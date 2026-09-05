import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_memory_service
from app.main import app
from app.services.memory.database import MemoryDatabase
from app.services.memory.repository import MemoryRepository
from app.services.memory.service import MemoryService


def make_service(database_path: object) -> MemoryService:
    return MemoryService(MemoryRepository(MemoryDatabase(database_path)))


def test_database_initialization_creates_memories_table(tmp_path: object) -> None:
    database_path = tmp_path / "memory.db"
    MemoryDatabase(database_path)

    with sqlite3.connect(database_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", ("memories",)
        ).fetchone()

    assert database_path.exists()
    assert table == ("memories",)


def test_memory_service_create_retrieve_and_list(tmp_path: object) -> None:
    service = make_service(tmp_path / "memory.db")
    created = service.remember("preference", "Keep my emails concise and professional.")

    assert service.get_memory(created.id) == created
    assert service.list_memories() == [created]


def test_memory_service_search_and_update(tmp_path: object) -> None:
    service = make_service(tmp_path / "memory.db")
    created = service.remember("fact", "I prefer emails before noon.")

    assert [memory.id for memory in service.search_memories("EMAILS")] == [created.id]
    updated = service.update_memory(created.id, "instruction", "Write concise emails.")

    assert updated is not None
    assert updated.memory_type == "instruction"
    assert updated.content == "Write concise emails."


def test_memory_service_delete_and_unknown_id(tmp_path: object) -> None:
    service = make_service(tmp_path / "memory.db")
    created = service.remember("fact", "The project is Baby.")

    assert service.forget_memory(created.id) is True
    assert service.get_memory(created.id) is None
    assert service.forget_memory(99_999) is False
    assert service.update_memory(99_999, None, "Missing") is None


def test_memory_service_rejects_invalid_type_and_secrets(tmp_path: object) -> None:
    service = make_service(tmp_path / "memory.db")

    with pytest.raises(ValueError, match="Invalid memory type"):
        service.remember("note", "A valid-looking note.")
    with pytest.raises(ValueError, match="contain a secret"):
        service.remember("fact", "password=not-safe-to-store")


def test_memory_persists_across_service_instances(tmp_path: object) -> None:
    database_path = tmp_path / "memory.db"
    first_service = make_service(database_path)
    created = first_service.remember("instruction", "Use local storage only.")

    second_service = make_service(database_path)

    assert second_service.get_memory(created.id) == created


def test_memory_api_endpoints_use_temporary_database(tmp_path: object) -> None:
    service = make_service(tmp_path / "api-memory.db")
    app.dependency_overrides[get_memory_service] = lambda: service
    client = TestClient(app)

    try:
        create_response = client.post(
            "/memory", json={"memory_type": "preference", "content": "Keep my emails concise."}
        )
        assert create_response.status_code == 201
        memory = create_response.json()

        assert client.get("/memory").json()[0]["id"] == memory["id"]
        assert client.get(f"/memory/{memory['id']}").json()["content"] == "Keep my emails concise."
        assert client.get("/memory/search?q=emails").json()[0]["id"] == memory["id"]

        update_response = client.put(
            f"/memory/{memory['id']}", json={"memory_type": "instruction", "content": "Use concise emails."}
        )
        assert update_response.status_code == 200
        assert update_response.json()["memory_type"] == "instruction"

        assert client.delete(f"/memory/{memory['id']}").status_code == 204
        assert client.get(f"/memory/{memory['id']}").status_code == 404
        assert client.get("/memory/99999").status_code == 404
        assert client.post("/memory", json={"memory_type": "invalid", "content": "Nope"}).status_code == 422
    finally:
        app.dependency_overrides.clear()
