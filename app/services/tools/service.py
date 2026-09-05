"""Service layer for executing registered local tools."""

from typing import Any

from app.services.tools.registry import ToolRegistry


class ToolService:
    """Executes tools from a registry without exposing provider details."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": tool.name, "description": tool.description, "input_schema": tool.input_schema} for tool in self._registry.list_tools()]

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        tool = self._registry.get(tool_name)
        if tool is None:
            return {"success": False, "result": None, "error": f"Unknown tool: {tool_name}"}
        return tool.execute(tool_input)
