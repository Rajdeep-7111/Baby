"""Sequential execution of already-planned Baby tasks."""

from typing import Any

from app.services.tasks.models import TaskPlan, TaskStep
from app.services.tools.registry import ToolRegistry
from app.services.tools.service import ToolService


class TaskExecutor:
    """Executes pending task steps through registered local tools only."""

    def __init__(self, tool_registry: ToolRegistry, tool_service: ToolService) -> None:
        self._tool_registry = tool_registry
        self._tool_service = tool_service

    def execute(self, plan: TaskPlan) -> TaskPlan:
        """Run pending steps in order and stop at the first failure."""
        plan.status = "running"
        plan.error = None
        pending_steps = [step for step in plan.steps if step.status == "pending"]
        if not pending_steps:
            plan.status = "failed"
            plan.error = "Task has no executable pending steps."
            return plan

        for step in pending_steps:
            step.status = "running"
            if step.tool_name is None or self._tool_registry.get(step.tool_name) is None:
                step.status = "failed"
                step.error = f"Tool is not available: {step.tool_name or 'unspecified'}"
                plan.status = "failed"
                plan.error = step.error
                return plan

            try:
                execution = self._tool_service.execute(step.tool_name, step.arguments)
            except Exception as error:  # Defensive boundary around local tool execution.
                step.status = "failed"
                step.error = f"Tool execution failed: {error}"
                plan.status = "failed"
                plan.error = step.error
                return plan

            self._store_execution_result(step, execution)
            if not execution["success"]:
                plan.status = "failed"
                plan.error = step.error
                return plan

        plan.status = "completed"
        return plan

    @staticmethod
    def _store_execution_result(step: TaskStep, execution: dict[str, Any]) -> None:
        step.result = execution["result"]
        step.error = execution["error"]
        step.status = "completed" if execution["success"] else "failed"
