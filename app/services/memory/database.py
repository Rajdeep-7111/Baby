"""SQLite database setup for Baby's local memory."""

from pathlib import Path
import sqlite3


class MemoryDatabase:
    """Creates and connects to the local SQLite memory database."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )


def default_memory_database_path() -> Path:
    """Return the on-disk location for Baby's production memory database."""
    return Path(__file__).resolve().parents[3] / "data" / "baby.db"
