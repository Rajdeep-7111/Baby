"""Registration and lookup for local tools."""

from app.services.tools.base import Tool


class ToolRegistry:
    """Stores one tool for each unique tool name."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool, rejecting duplicate names."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Return a registered tool by name, if present."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Return registered tools in registration order."""
        return list(self._tools.values())
