"""Common contract for Baby's local tools."""

from typing import Any, Protocol


class Tool(Protocol):
    """A named operation that accepts structured input and returns structured output."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with validated caller-provided input."""
