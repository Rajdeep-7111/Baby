"""SQLite persistence operations for Baby memories."""

from datetime import datetime, timezone

from app.services.memory.database import MemoryDatabase
from app.services.memory.models import Memory


class MemoryRepository:
    """Provides parameterized SQL operations for memories."""

    def __init__(self, database: MemoryDatabase) -> None:
        self._database = database

    def create(self, memory_type: str, content: str) -> Memory:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO memories (memory_type, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (memory_type, content, timestamp, timestamp),
            )
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_memory(row)

    def get(self, memory_id: int) -> Memory | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._to_memory(row) if row else None

    def list_memories(self) -> list[Memory]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM memories ORDER BY id").fetchall()
        return [self._to_memory(row) for row in rows]

    def search(self, query: str) -> list[Memory]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM memories WHERE content LIKE ? COLLATE NOCASE ORDER BY id", (f"%{query}%",)
            ).fetchall()
        return [self._to_memory(row) for row in rows]

    def update(self, memory_id: int, memory_type: str, content: str) -> Memory | None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._database.connect() as connection:
            cursor = connection.execute(
                "UPDATE memories SET memory_type = ?, content = ?, updated_at = ? WHERE id = ?",
                (memory_type, content, timestamp, memory_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._to_memory(row)

    def delete(self, memory_id: int) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0

    @staticmethod
    def _to_memory(row: object) -> Memory:
        return Memory.model_validate(dict(row))
