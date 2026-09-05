"""Task planning models."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """A natural-language task submitted by a user."""

    message: str = Field(min_length=1, max_length=4_000)


class TaskStep(BaseModel):
    step_id: int
    description: str
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Any | None = None
    error: str | None = None


class TaskPlan(BaseModel):
    task_id: str
    original_message: str
    status: Literal["planned", "running", "needs_clarification", "completed", "failed"]
    clarification_question: str | None = None
    steps: list[TaskStep] = Field(default_factory=list)
    error: str | None = None
