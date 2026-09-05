"""Converts understood task intents into non-executing task plans."""

from app.services.tasks.analyzer import AnalyzedAction
from app.services.tasks.models import TaskStep
from app.services.tools.registry import ToolRegistry


class TaskPlanner:
    """Creates pending steps only for registered tools."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry

    def create_steps(self, actions: list[AnalyzedAction]) -> list[TaskStep]:
        steps: list[TaskStep] = []
        for step_id, action in enumerate(actions, start=1):
            if self._tool_registry.get(action.tool_name) is None:
                raise ValueError(f"The required tool '{action.tool_name}' is not available.")
            steps.append(
                TaskStep(
                    step_id=step_id,
                    description=action.description,
                    tool_name=action.tool_name,
                    arguments=action.arguments,
                )
            )
        return steps
