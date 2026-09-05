"""Memory domain and API models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MemoryType = Literal[
    "preference",
    "fact",
    "instruction",
]


class Memory(BaseModel):
    """A persisted Baby memory."""

    id: int
    memory_type: MemoryType
    content: str
    created_at: datetime
    updated_at: datetime


class CreateMemoryRequest(BaseModel):
    memory_type: MemoryType
    content: str = Field(
        min_length=1,
        max_length=10_000,
    )


class UpdateMemoryRequest(BaseModel):
    memory_type: MemoryType | None = None
    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=10_000,
    )


class MemoryDecision(BaseModel):
    """Gemini's decision about whether a message should become a memory."""

    should_remember: bool
    memory_type: MemoryType | None = None
    content: str | None = None