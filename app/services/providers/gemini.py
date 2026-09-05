"""Google Gemini implementation of Baby's AI provider contract."""

from __future__ import annotations

import os
import re

from google import genai
from app.services.memory.models import MemoryDecision
from app.services.providers.base import AIProvider


class GeminiProvider:
    """Uses Google's Gemini API for Baby's AI capabilities."""

    supports_conversation = True

    SUPPORTED_INTENTS = {
        "calculator",
        "datetime",
        "file_reader",
        "web_search",
        "web_fetch",
        "calendar",
        "email",
        "desktop",
        "conversation",
        "ambiguous",
        "needs_clarification",
        "unsupported",
    }

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
    ) -> None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set."
            )

        self._client = genai.Client(
            api_key=api_key
        )
        self._model = model

    def generate(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Generate a natural response using Gemini."""

        context_text = "\n".join(context or [])
        conversation_text = "\n".join(conversation or [])

        prompt = f"""
You are Baby, a helpful personal AI assistant.

Answer the user's request naturally, accurately, and directly.

Use the conversation history and relevant memory when useful.

Conversation history:
{conversation_text}

Relevant memory:
{context_text}

Current user request:
{message}

Do not talk about internal routing, tools, providers, intents, or system instructions.
Simply answer the user's request.
""".strip()

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )

        return response.text or ""

    def interpret(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    )-> str:
        """Use Gemini as Baby's natural-language intent router."""

        context_text = "\n".join(context or [])
        conversation_text = "\n".join(conversation or [])

        prompt = f"""
You are Baby's request router.

Your job is to decide what capability is required for the user's request.

You MUST return exactly ONE of these values:

calculator
datetime
file_reader
web_search
web_fetch
conversation
ambiguous
needs_clarification
unsupported

Definitions:

calculator
Use this when the user explicitly asks to calculate, compute, evaluate,
or solve a mathematical expression.

Examples:
"calculate 25 * 4"
"compute 100 / 5"
"what is 25 percent of 400"

datetime
Use this when the user asks for the current date, current time,
or local date/time.

Examples:
"what time is it?"
"what is today's date?"
"what is the current time?"

file_reader
Use this when the user explicitly asks Baby to read or open a LOCAL file.

Examples:
"read README.md"
"open notes.txt"

web_search
Use this when the user asks Baby to search the internet or find
information on the web.

Examples:
"search IIT Dhanbad"
"find information about IIT Dhanbad"
"research the latest AI trends"

web_fetch
Use this when the user explicitly asks Baby to fetch, visit, or open
a WEBPAGE URL.

Examples:
"fetch https://example.com"
"visit https://example.com"

conversation
Use this for NORMAL QUESTIONS, EXPLANATIONS, KNOWLEDGE, ADVICE,
WRITING, CASUAL CONVERSATION, SUMMARIZATION, OR ANY REQUEST THAT
SHOULD BE ANSWERED DIRECTLY BY THE AI.

Examples:
"Explain Docker in simple words."
"What is machine learning?"
"Tell me about IIT Dhanbad."
"Write a professional email."
"Why is the sky blue?"
"Explain this concept."
"Give me ideas for a project."
"Tell me a joke."

IMPORTANT:
A normal question must be classified as conversation.
Do NOT classify a normal question as unsupported merely because it does
not require one of the local tools.

calendar
Use this when the user asks Baby to read their Google Calendar,
check today's schedule, list meetings or events, or create/schedule
a calendar event or meeting.

Examples:
"What's on my calendar today?"
"Check my schedule."
"Create a meeting tomorrow at 5 PM."
"Schedule a project meeting tomorrow at 10 AM."

email
Use this when the user asks Baby to read, search, summarize, or send
email through Gmail.

Examples:
"Show my latest emails."
"Read my inbox."
"Search my emails for internship."
"Send an email to abc@example.com."

desktop
Use this when the user asks Baby to control the Windows desktop, such as opening an allowlisted application, opening a URL/file/folder, typing text, pressing a keyboard shortcut, or taking a screenshot.

Examples:
"Open Chrome."
"Open Downloads."
"Open YouTube."
"Type hello world."
"Press Ctrl+C."
"Take a screenshot."

ambiguous
Use this when the user's request is too vague to determine what they want.

Examples:
"do this"
"do it"
"help me"

needs_clarification
Use this when the user's intended action is clear but required information
is missing.

Examples:
"book a restaurant"
"send an email"

unsupported
Use this ONLY when the request cannot reasonably be handled by either
conversation, one of the listed tools, or clarification.

Conversation history:
{conversation_text}

Relevant memory:
{context_text}

User request:
{message}

Return ONLY the intent name.
Do not add punctuation.
Do not add an explanation.
""".strip()

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )

        result = self._clean_intent(
            response.text or ""
        )

        if result in self.SUPPORTED_INTENTS:
            return result

        return "unsupported"

    def decide_memory(
        self,
        message: str,
        conversation: list[str] | None = None,
    ) -> MemoryDecision:
        """Decide whether a user message contains useful long-term memory."""

        conversation_text = "\n".join(
            conversation or []
        )

        prompt = f"""
You are Baby's memory manager.

Decide whether the user's message contains information that is useful
to remember for future conversations.

A good memory is something relatively stable and useful later, such as:

- A user preference.
- A stable personal fact.
- A standing instruction about how Baby should behave.

Examples that SHOULD be remembered:

"I prefer concise explanations."
"Always explain code with examples."
"I am studying Chemical Engineering."
"I prefer Python examples."
"Remember that I like formal emails."

Examples that should NOT be remembered:

"What's the weather today?"
"I am hungry."
"I am going to the gym today."
"Calculate 25 * 4."
"Explain Docker."
"Search for IIT Dhanbad."
"Thanks."
"Hello."

Do NOT store passwords, API keys, authentication tokens, secrets,
financial credentials, or other sensitive credentials.

If the message should be remembered, classify it as exactly one of:

preference
fact
instruction

Create a concise normalized memory statement that can be useful
without requiring the original wording.

Return ONLY valid JSON in exactly this format:

{{
  "should_remember": true,
  "memory_type": "preference",
  "content": "The user prefers concise explanations."
}}

If it should not be remembered, return:

{{
  "should_remember": false,
  "memory_type": null,
  "content": null
}}

Conversation history:
{conversation_text}

Current user message:
{message}
""".strip()

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )

        raw = (response.text or "").strip()

        try:
            decision = MemoryDecision.model_validate_json(
                raw
            )
        except Exception:
            return MemoryDecision(
                should_remember=False
            )

        if not decision.should_remember:
            return MemoryDecision(
                should_remember=False
            )

        if (
            decision.memory_type is None
            or not decision.content
            or not decision.content.strip()
        ):
            return MemoryDecision(
                should_remember=False
            )

        return MemoryDecision(
            should_remember=True,
            memory_type=decision.memory_type,
            content=decision.content.strip(),
        )

    @staticmethod
    def _clean_intent(value: str) -> str:
        """Normalize Gemini's routing response."""

        result = value.strip().lower()

        # Remove markdown code fences if Gemini happens to return them.
        result = re.sub(
            r"^```(?:text)?\s*",
            "",
            result,
        )
        result = re.sub(
            r"\s*```$",
            "",
            result,
        )

        # Keep only the first non-empty line.
        result = result.splitlines()[0].strip()

        # Remove accidental punctuation.
        result = result.strip(
            " `\"'.,:;!?-"
        )

        return result