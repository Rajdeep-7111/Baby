"""Task planning service; execution is intentionally out of scope."""

from uuid import uuid4

from app.services.tasks.analyzer import TaskAnalyzer
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.models import TaskPlan
from app.services.tasks.planner import TaskPlanner


class TaskNotExecutableError(ValueError):
    """Raised when a stored task cannot safely be executed."""


class TaskService:
    """Plans, executes, and retains tasks in a single in-memory store."""

    def __init__(self, analyzer: TaskAnalyzer, planner: TaskPlanner, executor: TaskExecutor | None = None) -> None:
        self._analyzer = analyzer
        self._planner = planner
        self._executor = executor
        self._plans: dict[str, TaskPlan] = {}

    def plan_task(self, message: str) -> TaskPlan:
        task_id = str(uuid4())
        analysis = self._analyzer.analyze(message)
        if analysis.status == "needs_clarification":
            plan = TaskPlan(
                task_id=task_id,
                original_message=message,
                status="needs_clarification",
                clarification_question=analysis.clarification_question,
            )
        else:
            try:
                steps = self._planner.create_steps(analysis.actions)
            except ValueError as error:
                plan = TaskPlan(
                    task_id=task_id,
                    original_message=message,
                    status="needs_clarification",
                    clarification_question=str(error),
                )
            else:
                plan = TaskPlan(task_id=task_id, original_message=message, status="planned", steps=steps)
        self._plans[task_id] = plan
        return plan

    def get_task(self, task_id: str) -> TaskPlan | None:
        return self._plans.get(task_id)

    def execute_task(self, task_id: str) -> TaskPlan | None:
        """Execute a stored planned task without re-analyzing or re-planning it."""
        plan = self._plans.get(task_id)
        if plan is None:
            return None
        if plan.status == "needs_clarification":
            raise TaskNotExecutableError("Tasks that need clarification cannot be executed.")
        if plan.status != "planned":
            raise TaskNotExecutableError(f"Task cannot be executed while its status is '{plan.status}'.")
        if self._executor is None:
            raise TaskNotExecutableError("Task execution is not configured.")
        return self._executor.execute(plan)
