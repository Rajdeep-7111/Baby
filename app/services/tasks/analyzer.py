"""Deterministic recognition of Baby's currently supported task intents."""

from dataclasses import dataclass
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class AnalyzedAction:
    tool_name: str
    description: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class TaskAnalysis:
    status: Literal["understood", "needs_clarification"]
    actions: list[AnalyzedAction]
    clarification_question: str | None = None


class TaskAnalyzer:
    """Maps natural-language requests to known local tools."""

    def analyze(self, message: str) -> TaskAnalysis:
        normalized = message.strip()
        lowered = normalized.lower()

        if lowered in {"do this", "do it", "help me", "help"}:
            return self._clarify(
                "What would you like me to do? Please describe the task."
            )

        if "book" in lowered and "restaurant" in lowered:
            return self._clarify(
                "What location, date, time, and party size should I use "
                "for the restaurant request?"
            )

       # ---------------------------------------------------------
       # Email sending
       # ---------------------------------------------------------
        if "send" in lowered and "email" in lowered:
            return self._analyze_email_send(message)

        # ---------------------------------------------------------
        # Split multi-action requests
        # ---------------------------------------------------------
        segments = re.split(
            r"\s+(?:and|then)\s+"
            r"(?=(?:calculate|compute|what|current|read|open|search|"
            r"find|look|browse|research|fetch|visit|show|check|open|launch|start|type|write|enter|press|hit|take|"
            r"schedule|create|add|send)\b)",
            normalized,
            flags=re.IGNORECASE,
        )

        actions: list[AnalyzedAction] = []

        for segment in segments:
            action = self._analyze_segment(segment.strip())

            if action is None:
                return self._clarify(
                    "I can currently plan calculations, local date/time "
                    "lookups, calendar operations, email operations, "
                    "reading a text file, web searches, and fetching "
                    "webpages. Could you rephrase your request?"
                )

            actions.append(action)

        return TaskAnalysis(
            status="understood",
            actions=actions,
        )

    def _analyze_segment(
        self,
        message: str,
    ) -> AnalyzedAction | None:

        lowered = message.lower().strip()

        # ---------------------------------------------------------
        # Calculator
        # ---------------------------------------------------------
        match = re.fullmatch(
            r"(?:calculate|compute)\s+(.+?)\s*[?.!]?\"?",
            message,
            flags=re.IGNORECASE,
        )

        if match:
            expression = match.group(1).strip()

            return AnalyzedAction(
                tool_name="calculator",
                description=f"Calculate {expression}",
                arguments={
                    "expression": expression,
                },
            )

        # ---------------------------------------------------------
        # Calendar - CREATE EVENT
        # ---------------------------------------------------------
        create_keywords = (
            "schedule",
            "create",
            "add",
            "book",
        )

        calendar_keywords = (
            "calendar",
            "meeting",
            "event",
        )

        has_create_intent = any(
            re.search(rf"\b{re.escape(keyword)}\b", lowered)
            for keyword in create_keywords
        )

        if (
            has_create_intent
            and any(keyword in lowered for keyword in calendar_keywords)
        ):
            return self._analyze_calendar_create(message)

        # ---------------------------------------------------------
        # Calendar - READ EVENTS
        # ---------------------------------------------------------
        calendar_phrases = (
            "calendar",
            "schedule",
            "events",
            "event",
            "meetings",
            "meeting",
        )

        calendar_actions = (
            "what's on",
            "what is on",
            "show",
            "check",
            "view",
            "list",
            "do i have",
        )

        # Specific-date calendar queries, including time filters.
        if any(token in lowered for token in ("tomorrow", "day after tomorrow")) and (
            any(phrase in lowered for phrase in calendar_phrases)
            or "do i have" in lowered
        ):
            timezone = ZoneInfo("Asia/Kolkata")
            now = datetime.now(timezone)
            if "day after tomorrow" in lowered:
                target_date = now.date() + timedelta(days=2)
            else:
                target_date = now.date() + timedelta(days=1)

            after_match = re.search(
                r"(?:after|from)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
                lowered,
                flags=re.IGNORECASE,
            )
            after_time = None
            if after_match:
                hour = int(after_match.group(1))
                minute = int(after_match.group(2) or 0)
                meridiem = after_match.group(3)
                if meridiem:
                    if meridiem.lower() == "pm" and hour < 12:
                        hour += 12
                    elif meridiem.lower() == "am" and hour == 12:
                        hour = 0
                if hour <= 23 and minute <= 59:
                    after_time = f"{hour:02d}:{minute:02d}"

            return AnalyzedAction(
                tool_name="calendar",
                description=f"Get calendar events for {target_date.isoformat()}",
                arguments={
                    "operation": "date",
                    "date": target_date.isoformat(),
                    **({"after_time": after_time} if after_time else {}),
                },
            )

        if (
            any(
                phrase in lowered
                for phrase in calendar_phrases
            )
            and any(
                action in lowered
                for action in calendar_actions
            )
        ):
            return AnalyzedAction(
                tool_name="calendar",
                description="Get today's calendar events",
                arguments={
                    "operation": "today",
                },
            )

        if (
            "today" in lowered
            and any(
                phrase in lowered
                for phrase in (
                    "schedule",
                    "calendar",
                    "events",
                    "meetings",
                    "meeting",
                )
            )
        ):
            return AnalyzedAction(
                tool_name="calendar",
                description="Get today's calendar events",
                arguments={
                    "operation": "today",
                },
            )

        # ---------------------------------------------------------
        # Email - SEARCH
        # ---------------------------------------------------------
        search_patterns = [
            r"(?:search|find|look\s+up)\s+(?:my\s+)?emails?\s+(?:for|about)\s+(.+)",
            r"(?:find|search)\s+(?:emails?|mail)\s+(?:about|regarding)\s+(.+)",
        ]

        for pattern in search_patterns:
            match = re.fullmatch(
                pattern,
                message,
                flags=re.IGNORECASE,
            )

            if match:
                query = match.group(1).strip().rstrip("?.!")

                if query:
                    return AnalyzedAction(
                        tool_name="email",
                        description=f"Search emails for {query}",
                        arguments={
                            "operation": "search",
                            "query": query,
                            "max_results": 5,
                        },
                    )

        # ---------------------------------------------------------
        # Email - READ RECENT
        # ---------------------------------------------------------
        email_recent_phrases = (
            "recent emails",
            "latest emails",
            "recent mail",
            "latest mail",
            "my emails",
            "my email",
            "my inbox",
            "inbox",
        )

        if (
            any(phrase in lowered for phrase in email_recent_phrases)
            or (
                "email" in lowered
                and any(
                    word in lowered
                    for word in (
                        "show",
                        "read",
                        "check",
                        "list",
                        "recent",
                        "latest",
                    )
                )
            )
        ):
            return AnalyzedAction(
                tool_name="email",
                description="Get recent emails",
                arguments={
                    "operation": "recent",
                    "max_results": 5,
                },
            )

        # ---------------------------------------------------------
        # Date/time
        # ---------------------------------------------------------
        lowered = lowered.rstrip("?!. ")

        if lowered in {
            "what time is it",
            "what is the time",
            "what's the time",
            "current time",
            "current local time",
            "what is today's date",
            "what's today's date",
            "what is the date today",
            "today's date",
            "current date",
        }:
            return AnalyzedAction(
                tool_name="datetime",
                description="Get the current local date and time",
                arguments={},
            )

        # ---------------------------------------------------------
        # Controlled Windows desktop
        # ---------------------------------------------------------
        desktop_app_aliases = {
            "chrome": "chrome",
            "google chrome": "google chrome",
            "edge": "edge",
            "microsoft edge": "microsoft edge",
            "notepad": "notepad",
            "calculator": "calculator",
            "calc": "calc",
            "file explorer": "file explorer",
            "explorer": "explorer",
            "command prompt": "command prompt",
            "cmd": "cmd",
            "powershell": "powershell",
            "terminal": "terminal",
            "windows terminal": "windows terminal",
            "vscode": "vscode",
            "visual studio code": "visual studio code",
        }

        website_aliases = {
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "google": "https://www.google.com",
            "github": "https://github.com",
            "calendar": "https://calendar.google.com",
        }

        if re.fullmatch(r"(?:open|launch|start)\s+.+", message, flags=re.IGNORECASE):
            target = re.sub(r"^(?:open|launch|start)\s+", "", message, flags=re.IGNORECASE).strip().strip("\"'").rstrip("?.!")
            target_key = target.lower()

            if target_key in desktop_app_aliases:
                return AnalyzedAction(
                    tool_name="desktop",
                    description=f"Open application: {target}",
                    arguments={"operation": "open_app", "target": desktop_app_aliases[target_key]},
                )

            if target_key in website_aliases:
                return AnalyzedAction(
                    tool_name="desktop",
                    description=f"Open website: {target}",
                    arguments={"operation": "open_url", "target": website_aliases[target_key]},
                )

            if target.startswith(("http://", "https://")):
                return AnalyzedAction(
                    tool_name="desktop",
                    description=f"Open URL: {target}",
                    arguments={"operation": "open_url", "target": target},
                )

            folder_aliases = {
                "downloads": Path.home() / "Downloads",
                "documents": Path.home() / "Documents",
                "desktop": Path.home() / "Desktop",
                "pictures": Path.home() / "Pictures",
                "music": Path.home() / "Music",
                "videos": Path.home() / "Videos",
            }
            if target_key in folder_aliases:
                return AnalyzedAction(
                    tool_name="desktop",
                    description=f"Open folder: {target}",
                    arguments={"operation": "open_path", "target": str(folder_aliases[target_key])},
                )

            if (Path(target).is_absolute() or "\\" in target or "/" in target or re.search(r"\.[A-Za-z0-9]{1,8}$", target)):
                return AnalyzedAction(
                    tool_name="desktop",
                    description=f"Open path: {target}",
                    arguments={"operation": "open_path", "target": target},
                )

        match = re.fullmatch(r"(?:type|write|enter)\s+(.+)", message, flags=re.IGNORECASE)
        if match:
            return AnalyzedAction(
                tool_name="desktop",
                description="Type text",
                arguments={"operation": "type_text", "text": match.group(1).strip()},
            )

        match = re.fullmatch(r"(?:press|hit)\s+(.+)", message, flags=re.IGNORECASE)
        if match:
            raw_keys = match.group(1).strip()
            keys = [k.strip() for k in re.split(r"\s*\+\s*", raw_keys) if k.strip()]
            return AnalyzedAction(
                tool_name="desktop",
                description=f"Press {' + '.join(keys)}",
                arguments={"operation": "hotkey", "keys": keys},
            )

        if re.fullmatch(r"(?:take\s+)?a?\s*screenshot", message, flags=re.IGNORECASE):
            return AnalyzedAction(
                tool_name="desktop",
                description="Take a screenshot",
                arguments={"operation": "screenshot"},
            )

        # ---------------------------------------------------------
        # File reader / Web fetch
        # ---------------------------------------------------------
        match = re.fullmatch(
            r"(?:read|open)\s+(.+?)\s*[?.!]?\"?",
            message,
            flags=re.IGNORECASE,
        )

        if match:
            target = match.group(1).strip().strip("\"'")

            if target.startswith(("http://", "https://")):
                return AnalyzedAction(
                    tool_name="web_fetch",
                    description=f"Fetch webpage {target}",
                    arguments={
                        "url": target,
                        "max_chars": 12000,
                    },
                )

            if target:
                return AnalyzedAction(
                    tool_name="file_reader",
                    description=f"Read {target}",
                    arguments={
                        "path": target,
                    },
                )

        # ---------------------------------------------------------
        # Direct web fetch
        # ---------------------------------------------------------
        match = re.fullmatch(
            r"(?:fetch|visit|browse)\s+(https?://\S+?)\s*[?.!]?\"?",
            message,
            flags=re.IGNORECASE,
        )

        if match:
            url = match.group(1).rstrip("?.!\"'")

            return AnalyzedAction(
                tool_name="web_fetch",
                description=f"Fetch webpage {url}",
                arguments={
                    "url": url,
                    "max_chars": 12000,
                },
            )

        # ---------------------------------------------------------
        # Web search
        # ---------------------------------------------------------
        web_search_patterns = [
            r"(?:search(?:\s+the)?\s+(?:web|internet)\s+for)\s+(.+?)\s*[?.!]?\"?",
            r"(?:search\s+for)\s+(.+?)\s*[?.!]?\"?",
            r"(?:find\s+(?:information\s+about|info\s+about|details\s+about))\s+(.+?)\s*[?.!]?\"?",
            r"(?:look\s+up)\s+(.+?)\s*[?.!]?\"?",
            r"(?:research)\s+(.+?)\s*[?.!]?\"?",
            r"(?:browse\s+(?:the\s+)?web\s+for)\s+(.+?)\s*[?.!]?\"?",
            r"(?:find)\s+(.+?)\s*[?.!]?\"?",
        ]

        for pattern in web_search_patterns:
            match = re.fullmatch(
                pattern,
                message,
                flags=re.IGNORECASE,
            )

            if match:
                query = match.group(1).strip()

                if query:
                    return AnalyzedAction(
                        tool_name="web_search",
                        description=f"Search the web for {query}",
                        arguments={
                            "query": query,
                            "max_results": 5,
                        },
                    )

        return None

    def _analyze_email_send(
        self,
        message: str,
    ) -> TaskAnalysis:
        """Parse a basic natural-language send-email request."""

        # Example:
        # Send an email to abc@gmail.com saying Hello
        match = re.search(
            r"send\s+(?:an?\s+)?email\s+to\s+"
            r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
            r"\s+(?:saying|with\s+message|that\s+says)\s+(.+)",
            message,
            flags=re.IGNORECASE,
        )

        if match:
            recipient = match.group(1).strip()
            body = match.group(2).strip().rstrip("?.!")

            return TaskAnalysis(
                status="needs_clarification",
                actions=[],
                clarification_question=(
                    f"I have the recipient ({recipient}) and message. "
                    "What subject should I use?"
                ),
            )

        return self._clarify(
            "Who should receive the email, what should the subject be, "
            "and what should the email say?"
        )

    def _analyze_calendar_create(
        self,
        message: str,
    ) -> AnalyzedAction | None:
        """Parse a basic natural-language calendar creation request."""

        lowered = message.lower()
        timezone = ZoneInfo("Asia/Kolkata")
        now = datetime.now(timezone)

        if "day after tomorrow" in lowered:
            event_date = now.date() + timedelta(days=2)
        elif "tomorrow" in lowered:
            event_date = now.date() + timedelta(days=1)
        else:
            event_date = now.date()

        time_match = re.search(
            r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
            lowered,
            flags=re.IGNORECASE,
        )

        if time_match is None:
            return None

        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)

        if meridiem:
            if meridiem.lower() == "pm" and hour < 12:
                hour += 12
            elif meridiem.lower() == "am" and hour == 12:
                hour = 0

        if hour > 23 or minute > 59:
            return None

        start = datetime(
            event_date.year,
            event_date.month,
            event_date.day,
            hour,
            minute,
            tzinfo=timezone,
        )

        duration_match = re.search(
            r"for\s+(\d+(?:\.\d+)?)\s*"
            r"(hour|hours|hr|hrs|minute|minutes|min|mins)",
            lowered,
        )

        if duration_match:
            amount = float(duration_match.group(1))
            unit = duration_match.group(2)

            if unit.startswith("hour") or unit.startswith("hr"):
                duration = timedelta(hours=amount)
            else:
                duration = timedelta(minutes=amount)
        else:
            duration = timedelta(hours=1)

        end = start + duration

        title = self._extract_calendar_title(
            message,
            time_match.group(0),
        )

        if not title:
            return None

        return AnalyzedAction(
            tool_name="calendar",
            description=f"Create calendar event: {title}",
            arguments={
                "operation": "create",
                "title": title,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )

    @staticmethod
    def _extract_calendar_title(
        message: str,
        time_text: str,
    ) -> str:
        """Extract a reasonable event title."""

        title = message.strip()

        title = re.sub(
            r"^(?:please\s+)?(?:schedule|create|add|book)\s+",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\b(?:on\s+)?(?:today|tomorrow|day after tomorrow)\b",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            re.escape(time_text),
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\bfor\s+\d+(?:\.\d+)?\s*"
            r"(?:hour|hours|hr|hrs|minute|minutes|min|mins)\b",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip(" .?!,")

        # Remove a dangling preposition left after removing the time.
        title = re.sub(
            r"\bat\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip(" .?!,")

        return title

    @staticmethod
    def _clarify(
        question: str,
    ) -> TaskAnalysis:
        return TaskAnalysis(
            status="needs_clarification",
            actions=[],
            clarification_question=question,
        )