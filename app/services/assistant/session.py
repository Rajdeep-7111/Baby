"""Persistent session storage for Baby V1.0."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.session.models import (
    ConversationMessage,
    ConversationSession,
)


class SessionService:
    """Stores Baby conversation sessions in a local JSON file."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            storage_path = Path("data") / "sessions.json"

        self._storage_path = storage_path
        self._sessions: dict[str, ConversationSession] = {}

        self._load()

    def create_session(self) -> ConversationSession:
        """Create and persist a new conversation session."""

        now = datetime.now(timezone.utc)

        session = ConversationSession(
            session_id=str(uuid4()),
            messages=[],
            created_at=now,
            updated_at=now,
        )

        self._sessions[session.session_id] = session
        self._save()

        return session

    def get_session(
        self,
        session_id: str,
    ) -> ConversationSession | None:
        """Retrieve an existing session."""

        return self._sessions.get(session_id)

    def list_sessions(self) -> list[ConversationSession]:
        """Return all stored sessions ordered by most recently updated."""

        return sorted(
            self._sessions.values(),
            key=lambda session: session.updated_at,
            reverse=True,
        )

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> ConversationSession | None:
        """Append a message and persist the updated session."""

        session = self._sessions.get(session_id)

        if session is None:
            return None

        message = ConversationMessage(
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
        )

        session.messages.append(message)
        session.updated_at = message.created_at

        self._save()

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session permanently."""

        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]
        self._save()

        return True

    def _load(self) -> None:
        """Load sessions from disk if the storage file exists."""

        if not self._storage_path.exists():
            return

        try:
            raw_data = json.loads(
                self._storage_path.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(raw_data, dict):
                return

            sessions = raw_data.get("sessions", [])

            if not isinstance(sessions, list):
                return

            for raw_session in sessions:
                try:
                    session = ConversationSession.model_validate(
                        raw_session
                    )
                    self._sessions[session.session_id] = session

                except Exception:
                    # Ignore one malformed session rather than
                    # preventing Baby from starting.
                    continue

        except (OSError, json.JSONDecodeError):
            # If the storage file cannot be read, start with
            # an empty session store.
            self._sessions = {}

    def _save(self) -> None:
        """Persist all sessions atomically."""

        self._storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "sessions": [
                session.model_dump(mode="json")
                for session in self._sessions.values()
            ]
        }

        temporary_path = self._storage_path.with_suffix(
            ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(
            self._storage_path
        )