"""Validation and business logic for explicit Baby memories."""

import re

from app.services.memory.models import Memory
from app.services.memory.repository import MemoryRepository


class MemoryService:
    """Manages user-created memories independently of AI providers and tools."""

    _memory_types = {"preference", "fact", "instruction"}
    _secret_patterns = (
        r"\b(?:password|api[_ -]?key|auth(?:entication)?[_ -]?token|secret)\s*[:=]",
        r"\bsk-[a-z0-9]{8,}\b",
        r"\bbearer\s+[a-z0-9._-]{8,}\b",
    )

    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    def remember(self, memory_type: str, content: str) -> Memory:
        self._validate(memory_type, content)
        return self._repository.create(memory_type, content)

    def get_memory(self, memory_id: int) -> Memory | None:
        return self._repository.get(memory_id)

    def list_memories(self) -> list[Memory]:
        return self._repository.list_memories()

    def search_memories(self, query: str) -> list[Memory]:
        if not query.strip():
            raise ValueError("Search query must not be empty.")
        return self._repository.search(query)

    def update_memory(self, memory_id: int, memory_type: str | None, content: str | None) -> Memory | None:
        existing = self._repository.get(memory_id)
        if existing is None:
            return None
        updated_type = memory_type if memory_type is not None else existing.memory_type
        updated_content = content if content is not None else existing.content
        self._validate(updated_type, updated_content)
        return self._repository.update(memory_id, updated_type, updated_content)

    def forget_memory(self, memory_id: int) -> bool:
        return self._repository.delete(memory_id)

    def _validate(self, memory_type: str, content: str) -> None:
        if memory_type not in self._memory_types:
            raise ValueError("Invalid memory type. Use preference, fact, or instruction.")
        if not content.strip():
            raise ValueError("Memory content must not be empty.")
        if any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in self._secret_patterns):
            raise ValueError("Memory content appears to contain a secret and cannot be stored.")
