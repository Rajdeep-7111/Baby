"""Provider-independent AI gateway for Baby."""

from app.core.config import settings
from app.services.memory.models import MemoryDecision
from app.services.providers.base import AIProvider
from app.services.providers.gemini import GeminiProvider
from app.services.providers.mock import MockAIProvider


class AIService:
    """Delegates AI operations to the configured provider."""

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    @property
    def supports_conversation(self) -> bool:
        """Whether the configured provider supports normal conversation."""
        return getattr(
            self._provider,
            "supports_conversation",
            False,
        )

    @property
    def provider_name(self) -> str:
        """Return the active provider name."""
        return type(self._provider).__name__

    def generate(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Generate a response using the configured provider."""

        if self.supports_conversation:
            return self._provider.generate(
                message,
                context=context,
                conversation=conversation,
            )

        return self._provider.generate(message)

    def interpret(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Interpret a user request using the configured provider."""

        return self._provider.interpret(
            message,
            context,
            conversation,
        )

    def decide_memory(
        self,
        message: str,
        conversation: list[str] | None = None,
    ) -> MemoryDecision:
        """Ask the configured provider whether the message should be remembered."""

        method = getattr(
            self._provider,
            "decide_memory",
            None,
        )

        if method is None:
            return MemoryDecision(
                should_remember=False,
            )

        return method(
            message,
            conversation,
        )


def create_ai_provider() -> AIProvider:
    """Create the AI provider configured for the current environment."""

    provider_name = settings.ai_provider.lower().strip()

    if provider_name == "gemini":
        return GeminiProvider(
            model=settings.gemini_model,
        )

    if provider_name == "mock":
        return MockAIProvider()

    raise RuntimeError(
        f"Unsupported AI provider '{settings.ai_provider}'. "
        "Use 'gemini' or 'mock'."
    )


ai_service = AIService(
    provider=create_ai_provider()
)