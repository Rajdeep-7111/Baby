"""Offline mock implementation of Baby's AI provider contract."""

from app.services.memory.models import MemoryDecision


class MockAIProvider:
    """Returns deterministic local responses without external calls."""

    def __init__(self) -> None:
        self.last_context: tuple[str, ...] = ()
        self.last_conversation: tuple[str, ...] = ()

    def generate(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Generate a deterministic local response."""

        self.last_context = tuple(context or [])
        self.last_conversation = tuple(conversation or [])

        return f"Baby mock response: I received '{message}'"

    def interpret(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Classify known local capabilities without external calls."""

        self.last_context = tuple(context or [])
        self.last_conversation = tuple(conversation or [])

        normalized = message.lower().strip()

        if (
            "calculate" in normalized
            or "compute" in normalized
        ):
            return "calculator"

        if (
            "what time" in normalized
            or "current time" in normalized
            or "current local time" in normalized
            or "today's date" in normalized
            or "what is the date today" in normalized
            or "current date" in normalized
        ):
            return "datetime"

        if normalized.startswith(("read ", "open ")):
            if (
                "http://" in normalized
                or "https://" in normalized
            ):
                return "web_fetch"

            return "file_reader"

        if normalized.startswith(
            (
                "fetch ",
                "visit ",
            )
        ):
            return "web_fetch"

        if any(word in normalized for word in ("calendar", "schedule", "meeting", "meetings", "event", "events")):
            if any(word in normalized for word in ("create", "schedule", "add", "book", "show", "check", "view", "list", "what's on", "what is on", "do i have")):
                return "calendar"

        if (
            normalized.startswith(("open ", "launch ", "start ", "type ", "press ", "take a screenshot", "screenshot"))
            and not normalized.startswith(("open http://", "open https://", "open read "))
        ):
            return "desktop"

        if any(word in normalized for word in ("email", "emails", "mail", "inbox")):
            if any(word in normalized for word in ("send", "show", "read", "check", "list", "search", "find", "latest", "recent")):
                return "email"

        if normalized.startswith(
            (
                "search ",
                "search the web ",
                "search the internet ",
                "find ",
                "look up ",
                "research ",
                "browse ",
            )
        ):
            return "web_search"

        if normalized in {
            "do this",
            "do it",
            "help",
            "help me",
        }:
            return "ambiguous"

        if (
            ("book" in normalized and "restaurant" in normalized)
            or ("send" in normalized and "email" in normalized)
        ):
            return "needs_clarification"

        return "unsupported"

    def decide_memory(
        self,
        message: str,
        conversation: list[str] | None = None,
    ) -> MemoryDecision:
        """Never create automatic memories in offline/mock mode."""

        return MemoryDecision(
            should_remember=False,
        )