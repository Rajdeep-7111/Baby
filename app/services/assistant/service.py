"""Coordinates Baby's AI gateway, memory context, task planning, execution, and sessions."""

import re
from collections.abc import Callable
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from app.services.ai import AIService
from app.services.assistant.session import SessionService
from app.services.memory.models import Memory
from app.services.memory.service import MemoryService
from app.services.session.models import ConversationMessage
from app.services.tasks.models import TaskPlan, TaskStep
from app.services.tasks.service import TaskService


class MemoryContextItem(BaseModel):
    """Safe public metadata for one persistent memory used as context."""

    id: int
    memory_type: str


class AssistantContext(BaseModel):
    """Separates user input, persistent memory, session state, and task state."""

    user_message: str
    persistent_memories: list[MemoryContextItem]
    session_id: str | None = None
    session_message_count: int = 0
    task_id: str | None = None
    task_status: str | None = None


class AssistantResponse(BaseModel):
    """The visible lifecycle and final state of an assistant request."""

    message: str
    interpretation: str
    task_id: str
    status: Literal[
        "planned",
        "running",
        "needs_clarification",
        "completed",
        "failed",
    ]
    response: str
    clarification_question: str | None = None
    steps: list[TaskStep]
    error: str | None = None
    context: AssistantContext


class AssistantService:
    """Plans, executes, and maintains Baby conversation sessions."""

    def __init__(
        self,
        ai_service: AIService,
        task_service: TaskService,
        memory_service_factory: Callable[[], MemoryService] | None = None,
        session_service: SessionService | None = None,
        max_memories: int = 3,
    ) -> None:
        self._ai_service = ai_service
        self._task_service = task_service
        self._memory_service_factory = memory_service_factory
        self._session_service = session_service or SessionService()
        self._max_memories = max_memories

    def handle_message(
        self,
        message: str,
        session_id: str | None = None,
        conversation: list[ConversationMessage] | None = None,
    ) -> AssistantResponse:
        """Route a request through AI intent detection, local tools, memory, and sessions."""

        # ---------------------------------------------------------
        # 1. Create or resume session
        # ---------------------------------------------------------
        if session_id is None:
            session = self._session_service.create_session()
        else:
            session = self._session_service.get_session(session_id)

            if session is None:
                raise ValueError(f"Unknown session ID: {session_id}")

        if conversation is None:
            conversation = list(session.messages)

        previous_conversation = list(conversation)

        self._session_service.append_message(
            session.session_id,
            "user",
            message,
        )

        # ---------------------------------------------------------
        # 2. Retrieve relevant persistent memory
        # ---------------------------------------------------------
        memories = self._find_relevant_memories(message)

        context = AssistantContext(
            user_message=message,
            persistent_memories=[
                MemoryContextItem(
                    id=memory.id,
                    memory_type=memory.memory_type,
                )
                for memory in memories
            ],
            session_id=session.session_id,
            session_message_count=len(session.messages),
        )

        # ---------------------------------------------------------
        # 3. Resolve supported session follow-ups
        # ---------------------------------------------------------
        task_message = self._resolve_session_follow_up(
            message,
            previous_conversation,
        )

        # ---------------------------------------------------------
        # 4. Deterministic desktop fast path
        #
        # Desktop commands are intentionally handled locally so
        # simple actions such as "open Chrome" do not consume a
        # Gemini request. All other requests continue through the
        # normal AI router below.
        # ---------------------------------------------------------
        local_plan = self._task_service.plan_task(task_message)

        if (
            local_plan.status == "planned"
            and local_plan.steps
            and local_plan.steps[0].tool_name == "desktop"
        ):
            plan = self._task_service.execute_task(local_plan.task_id)
            if plan is None:
                plan = local_plan

            context.task_id = plan.task_id
            context.task_status = plan.status

            response = self._build_response(
                message,
                "desktop",
                plan,
                context,
            )

            self._session_service.append_message(
                session.session_id,
                "assistant",
                response.response,
            )

            updated_session = self._session_service.get_session(
                session.session_id
            )
            if updated_session is not None:
                response.context.session_message_count = len(
                    updated_session.messages
                )

            return response

        # ---------------------------------------------------------
        # 4. AI is the router; deterministic analyzers execute
        #    known local operations.
        #
        # This fixes the old flow where an unrecognized normal
        # conversation was turned into a "clarification" task
        # before Gemini ever got a chance to answer it.
        # ---------------------------------------------------------
        try:
            interpretation = self._ai_service.interpret(
                task_message,
                [memory.content for memory in memories],
                [
                    f"{entry.role}: {entry.content}"
                    for entry in previous_conversation
                ],
            )
        except Exception:
            # If the AI router is temporarily unavailable, preserve
            # the deterministic local-tool path rather than crashing
            # the whole assistant request.
            interpretation = "fallback"

        # ---------------------------------------------------------
        # 5. Normal conversation -> Gemini
        # ---------------------------------------------------------
        if (
            interpretation == "conversation"
            and self._ai_service.supports_conversation
        ):
            self._consider_automatic_memory(
                task_message,
                previous_conversation,
                interpretation,
            )

            response_text = self._ai_service.generate(
                task_message,
                context=[memory.content for memory in memories],
                conversation=[
                    f"{entry.role}: {entry.content}"
                    for entry in previous_conversation
                ],
            )

            task_id = str(uuid4())
            context.task_id = task_id
            context.task_status = "completed"

            response = AssistantResponse(
                message=message,
                interpretation="conversation",
                task_id=task_id,
                status="completed",
                response=response_text,
                clarification_question=None,
                steps=[],
                error=None,
                context=context,
            )

        # ---------------------------------------------------------
        # 6. Ambiguous / clarification -> deterministic task
        # ---------------------------------------------------------
        elif interpretation in {"ambiguous", "needs_clarification"}:
            plan = self._task_service.plan_task(task_message)

            context.task_id = plan.task_id
            context.task_status = plan.status

            self._consider_automatic_memory(
                task_message,
                previous_conversation,
                "conversation" if interpretation == "conversation" else interpretation,
            )

            response = self._build_response(
                message,
                interpretation,
                plan,
                context,
            )

        # ---------------------------------------------------------
        # 7. Known tool intent -> deterministic task planning
        # ---------------------------------------------------------
        elif interpretation in {
            "calculator",
            "datetime",
            "file_reader",
            "web_search",
            "web_fetch",
            "calendar",
            "email",
            "desktop",
        }:
            plan = self._task_service.plan_task(task_message)

            # The AI router and deterministic analyzer must agree.
            # If the analyzer cannot parse the request, return a
            # useful clarification instead of executing anything.
            if plan.status == "planned":
                executed_plan = self._task_service.execute_task(
                    plan.task_id
                )
                if executed_plan is not None:
                    plan = executed_plan

            context.task_id = plan.task_id
            context.task_status = plan.status

            response = self._build_response(
                message,
                interpretation,
                plan,
                context,
            )

        # ---------------------------------------------------------
        # 8. AI fallback: deterministic tools can still work when
        #    the provider router is unavailable.
        # ---------------------------------------------------------
        elif interpretation == "fallback":
            plan = self._task_service.plan_task(task_message)

            if plan.status == "planned":
                executed_plan = self._task_service.execute_task(
                    plan.task_id
                )
                if executed_plan is not None:
                    plan = executed_plan

            context.task_id = plan.task_id
            context.task_status = plan.status

            if plan.status == "needs_clarification":
                # Do not pretend a normal conversational request is
                # a successful task. Explain the temporary limitation.
                plan.clarification_question = (
                    "Baby's AI router is temporarily unavailable. "
                    "Please try again in a moment."
                )

            response = self._build_response(
                message,
                "fallback",
                plan,
                context,
            )

        # ---------------------------------------------------------
        # 9. Unsupported AI classification
        # ---------------------------------------------------------
        else:
            task_id = str(uuid4())
            context.task_id = task_id
            context.task_status = "completed"

            response = AssistantResponse(
                message=message,
                interpretation=interpretation or "unsupported",
                task_id=task_id,
                status="completed",
                response=(
                    "I can't safely perform that request yet. "
                    "Please rephrase it or ask me to use one of my "
                    "available capabilities."
                ),
                clarification_question=None,
                steps=[],
                error=None,
                context=context,
            )

        # ---------------------------------------------------------
        # 10. Store Baby's response in the session
        # ---------------------------------------------------------
        self._session_service.append_message(
            session.session_id,
            "assistant",
            response.response,
        )

        updated_session = self._session_service.get_session(
            session.session_id
        )

        if updated_session is not None:
            response.context.session_message_count = len(
                updated_session.messages
            )

        return response

    @staticmethod
    def _interpretation_for_local_task(
        plan: TaskPlan,
    ) -> str:
        """Return the tool name as the interpretation for local tasks."""

        if not plan.steps:
            return "task"

        return plan.steps[0].tool_name or "task"

    def _consider_automatic_memory(
        self,
        message: str,
        conversation: list[ConversationMessage],
        interpretation: str,
    ) -> None:
        """Ask the configured AI provider whether this message should be remembered."""

        if interpretation != "conversation":
            return

        if self._memory_service_factory is None:
            return

        decision = self._ai_service.decide_memory(
            message,
            [
                f"{entry.role}: {entry.content}"
                for entry in conversation
            ],
        )

        if not decision.should_remember:
            return

        if (
            decision.memory_type is None
            or decision.content is None
            or not decision.content.strip()
        ):
            return

        memory_service = self._memory_service_factory()

        try:
            memory_service.remember(
                decision.memory_type,
                decision.content,
            )
        except ValueError:
            return

    @staticmethod
    def _should_use_ai_conversation(
        message: str,
    ) -> bool:
        """Decide whether an unrecognized request should go to the AI provider."""

        normalized = message.strip().lower()

        if normalized in {
            "do this",
            "do it",
            "help",
            "help me",
        }:
            return False

        if (
            "book" in normalized
            and "restaurant" in normalized
        ):
            return False

        if (
            "send" in normalized
            and "email" in normalized
        ):
            return False

        return True

    @staticmethod
    def _resolve_session_follow_up(
        message: str,
        conversation: list[ConversationMessage],
    ) -> str:
        """Resolve the narrowly supported 'now add N' follow-up."""

        match = re.fullmatch(
            r"(?:now\s+)?add\s+(-?\d+(?:\.\d+)?)\s*[?.!]?",
            message.strip(),
            flags=re.IGNORECASE,
        )

        if match is None:
            return message

        for entry in reversed(conversation):
            if (
                entry.role == "assistant"
                and re.fullmatch(
                    r"-?\d+(?:\.\d+)?",
                    entry.content.strip(),
                )
            ):
                return (
                    f"calculate {entry.content.strip()} "
                    f"+ {match.group(1)}"
                )

        return message

    @staticmethod
    def _build_response(
        message: str,
        interpretation: str,
        plan: TaskPlan,
        context: AssistantContext,
    ) -> AssistantResponse:
        """Build the public assistant response."""

        if plan.status == "completed":
            response = AssistantService._completed_response(
                plan
            )

        elif plan.status == "needs_clarification":
            response = (
                plan.clarification_question
                or "Please provide more detail about the task."
            )

        else:
            response = (
                plan.error
                or "The task could not be completed."
            )

        return AssistantResponse(
            message=message,
            interpretation=interpretation,
            task_id=plan.task_id,
            status=plan.status,
            response=response,
            clarification_question=plan.clarification_question,
            steps=plan.steps,
            error=plan.error,
            context=context,
        )

    def _find_relevant_memories(
        self,
        message: str,
    ) -> list[Memory]:
        """Retrieve a small, deterministically ordered local memory subset."""

        if self._memory_service_factory is None:
            return []

        terms = self._search_terms(message)

        if not terms:
            return []

        memory_service = self._memory_service_factory()

        candidates: dict[int, Memory] = {}

        for term in terms:
            for memory in memory_service.search_memories(term):
                candidates[memory.id] = memory

        scored = [
            (
                self._relevance_score(memory, terms),
                memory,
            )
            for memory in candidates.values()
        ]

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].id,
            )
        )

        return [
            memory
            for score, memory in scored
            if score > 0
        ][: self._max_memories]

    @staticmethod
    def _search_terms(
        message: str,
    ) -> list[str]:
        """Extract simple deterministic search terms."""

        ignored_terms = {
            "about",
            "and",
            "are",
            "can",
            "could",
            "for",
            "how",
            "please",
            "the",
            "this",
            "what",
            "with",
        }

        terms = [
            term
            for term in dict.fromkeys(
                re.findall(
                    r"[a-z0-9]{3,}",
                    message.lower(),
                )
            )
            if term not in ignored_terms
        ]

        return list(
            dict.fromkeys(
                [
                    *terms,
                    *(
                        term[:-1]
                        for term in terms
                        if term.endswith("e")
                    ),
                ]
            )
        )

    @staticmethod
    def _relevance_score(
        memory: Memory,
        terms: list[str],
    ) -> int:
        """Calculate deterministic memory relevance."""

        memory_terms = re.findall(
            r"[a-z0-9]{3,}",
            memory.content.lower(),
        )

        return sum(
            1
            for term in terms
            if any(
                candidate.startswith(term)
                or term.startswith(candidate)
                for candidate in memory_terms
            )
        )

    @staticmethod
    def _completed_response(
        plan: TaskPlan,
    ) -> str:
        """Convert a completed tool result into a user-friendly response."""

        if not plan.steps:
            return "Task completed successfully."

        result = plan.steps[-1].result

        if isinstance(result, dict):
            if "value" in result:
                return str(result["value"])

            if "datetime" in result:
                return (
                    "Current local date and time: "
                    f"{result['datetime']}"
                )

            if "path" in result:
                return (
                    f"Read {result['path']} successfully."
                )

            # -----------------------------------------------------
            # Calendar result
            # -----------------------------------------------------
            if "events" in result:
                events = result.get("events", [])
                count = result.get(
                    "count",
                    len(events),
                )
                date_label = result.get("date")
                after_time = result.get("after_time")

                if date_label:
                    try:
                        parsed_date = __import__("datetime").date.fromisoformat(date_label)
                        date_label = parsed_date.strftime("%A, %d %B")
                    except (ValueError, TypeError):
                        pass

                scope = f" on {date_label}" if date_label else " today"
                if after_time:
                    scope += f" after {after_time}"

                if count == 0:
                    return f"You have no calendar events{scope}."

                if count == 1:
                    prefix = f"You have 1 event{scope}:"
                else:
                    prefix = f"You have {count} events{scope}:"

                lines = [prefix]

                for event in events:
                    title = event.get(
                        "title",
                        "(No title)",
                    )

                    start = event.get(
                        "start",
                        "",
                    )

                    if start:
                        event_time = start

                        try:
                            parsed = __import__(
                                "datetime"
                            ).datetime.fromisoformat(
                                start
                            )

                            event_time = parsed.strftime(
                                "%I:%M %p"
                            ).lstrip("0")

                        except (
                            ValueError,
                            TypeError,
                        ):
                            pass

                        lines.append(
                            f"• {event_time} — {title}"
                        )
                    else:
                        lines.append(
                            f"• {title}"
                        )

                return "\n".join(lines)

            # -----------------------------------------------------
            # Calendar creation result
            # -----------------------------------------------------
            if "id" in result and "title" in result and "start" in result:
                return (
                    f"Done. I created '{result['title']}' "
                    f"for {result['start']}."
                )

            # -----------------------------------------------------
            # Read one email
            # -----------------------------------------------------
            if "body" in result and "subject" in result:
                subject = result.get("subject") or "(No subject)"
                sender = result.get("from") or "Unknown sender"
                body = (result.get("body") or "").strip()
                if len(body) > 3000:
                    body = body[:3000].rstrip() + "…"
                return f"Email from {sender}\nSubject: {subject}\n\n{body}"

            # -----------------------------------------------------
            # Send email result
            # -----------------------------------------------------
            if "thread_id" in result and "id" in result and "emails" not in result:
                return "Done. The email was sent successfully."

            # -----------------------------------------------------
            # Email result
            # -----------------------------------------------------
            if "emails" in result:
                emails = result.get("emails", [])
                count = result.get("count", len(emails))

                if count == 0:
                    return "You have no matching emails."

                lines = [f"I found {count} email{'s' if count != 1 else ''}:"]
                for email in emails:
                    sender = email.get("from", "Unknown sender")
                    subject = email.get("subject", "(No subject)")
                    lines.append(f"• {sender} — {subject}")
                return "\n".join(lines)

            # -----------------------------------------------------
            # Web page result
            # -----------------------------------------------------
            if "text" in result and "url" in result:
                title = result.get("title") or result.get("url")
                text = (result.get("text") or "").strip()
                if len(text) > 2500:
                    text = text[:2500].rstrip() + "…"
                return f"{title}\n\n{text}"

            # -----------------------------------------------------
            # Web search result
            # -----------------------------------------------------
            if "results" in result:
                results = result.get("results", [])
                if not results:
                    return "I couldn't find any matching web results."

                lines = ["Here are the most relevant results:"]
                for item in results[:5]:
                    title = item.get("title") or item.get("name") or "Untitled"
                    url = item.get("url", "")
                    lines.append(f"• {title}" + (f" — {url}" if url else ""))
                return "\n".join(lines)

        return str(result)