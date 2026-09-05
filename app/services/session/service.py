"""In-memory session storage for Baby V0.9."""

from datetime import datetime, timezone
from uuid import uuid4

from app.services.session.models import ConversationMessage, ConversationSession


class SessionService:
    """Stores ordered, temporary user/assistant conversation turns."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}

    def create_session(self) -> ConversationSession:
        now = datetime.now(timezone.utc)
        session = ConversationSession(session_id=str(uuid4()), messages=[], created_at=now, updated_at=now)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self._sessions.get(session_id)

    def append_message(self, session_id: str, role: str, content: str) -> ConversationSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        message = ConversationMessage(role=role, content=content, created_at=datetime.now(timezone.utc))
        session.messages.append(message)
        session.updated_at = message.created_at
        return session
