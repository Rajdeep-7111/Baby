"""Local date and time tool."""

from datetime import datetime
from typing import Any


class DateTimeTool:
    """Returns the machine's local date and time."""

    name = "datetime"
    description = "Returns the current local date and time."
    input_schema: dict[str, Any] = {"type": "object", "properties": {}}

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        current_time = datetime.now().astimezone()
        return {"success": True, "result": {"datetime": current_time.isoformat(), "timezone": str(current_time.tzinfo)}, "error": None}
