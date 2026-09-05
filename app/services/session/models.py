"""Models for Baby's conversation session state."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ConversationMessage(BaseModel):
    """One message stored in a conversation session."""

    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationSession(BaseModel):
    """A complete Baby conversation session."""

    session_id: str
    messages: list[ConversationMessage]
    created_at: datetime
    updated_at: datetime