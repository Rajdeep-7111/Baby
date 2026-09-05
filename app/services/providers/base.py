"""Common contract for text-generation providers."""

from typing import Protocol


class AIProvider(Protocol):
    """Common interface for Baby AI providers."""

    supports_conversation: bool

    def generate(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Return a generated text response."""

    def interpret(
        self,
        message: str,
        context: list[str] | None = None,
        conversation: list[str] | None = None,
    ) -> str:
        """Return a provider-defined interpretation."""