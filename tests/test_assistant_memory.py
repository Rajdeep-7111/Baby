from fastapi.testclient import TestClient

from app.api.routes import get_assistant_service, get_memory_service
from app.main import app
from app.services.ai import AIService
from app.services.assistant.service import AssistantService
from app.services.memory.database import MemoryDatabase
from app.services.memory.repository import MemoryRepository
from app.services.memory.service import MemoryService
from app.services.providers.mock import MockAIProvider
from app.services.tasks.analyzer import TaskAnalyzer
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.planner import TaskPlanner
from app.services.tasks.service import TaskService
from app.services.tools.defaults import tool_registry, tool_service


def make_memory_service(database_path: object) -> MemoryService:
    return MemoryService(MemoryRepository(MemoryDatabase(database_path)))


def make_memory_aware_assistant(memory_service: MemoryService) -> tuple[AssistantService, MockAIProvider]:
    provider = MockAIProvider()
    tasks = TaskService(TaskAnalyzer(), TaskPlanner(tool_registry), TaskExecutor(tool_registry, tool_service))
    return AssistantService(AIService(provider), tasks, lambda: memory_service), provider


def test_assistant_retrieves_relevant_preference_and_excludes_irrelevant_memory(tmp_path: object) -> None:
    memory_service = make_memory_service(tmp_path / "memory.db")
    preference = memory_service.remember("preference", "Keep Docker explanations clear and practical.")
    memory_service.remember("fact", "My garden has three tomato plants.")
    assistant, provider = make_memory_aware_assistant(memory_service)

    response = assistant.handle_message("Explain Docker")

    assert [item.model_dump() for item in response.context.persistent_memories] == [
        {"id": preference.id, "memory_type": "preference"}
    ]
    assert provider.last_context == ("Keep Docker explanations clear and practical.",)
    assert response.status == "needs_clarification"


def test_memory_retrieval_orders_multiple_relevant_memories_deterministically(tmp_path: object) -> None:
    memory_service = make_memory_service(tmp_path / "memory.db")
    first = memory_service.remember("fact", "Docker guide for local development.")
    second = memory_service.remember("instruction", "Docker guide for troubleshooting containers.")
    assistant, _ = make_memory_aware_assistant(memory_service)

    response = assistant.handle_message("Explain Docker guide")

    assert [item.id for item in response.context.persistent_memories] == [first.id, second.id]


def test_assistant_without_memories_returns_empty_context_and_executes_task(tmp_path: object) -> None:
    memory_service = make_memory_service(tmp_path / "memory.db")
    assistant, _ = make_memory_aware_assistant(memory_service)

    response = assistant.handle_message("calculate 25 * 4")

    assert response.context.persistent_memories == []
    assert response.status == "completed"
    assert response.response == "100"


def test_assistant_executes_calculator_with_relevant_memory_context(tmp_path: object) -> None:
    memory_service = make_memory_service(tmp_path / "memory.db")
    memory = memory_service.remember("preference", "Show calculation results clearly.")
    assistant, _ = make_memory_aware_assistant(memory_service)

    response = assistant.handle_message("calculate 25 * 4")

    assert response.status == "completed"
    assert response.response == "100"
    assert [item.id for item in response.context.persistent_memories] == [memory.id]


def test_memory_api_creation_flows_into_assistant_chat_context(tmp_path: object) -> None:
    memory_service = make_memory_service(tmp_path / "memory.db")
    assistant, _ = make_memory_aware_assistant(memory_service)
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_assistant_service] = lambda: assistant
    client = TestClient(app)

    try:
        created = client.post(
            "/memory",
            json={"memory_type": "preference", "content": "Keep Docker explanations concise."},
        )
        assert created.status_code == 201

        response = client.post("/assistant/chat", json={"message": "Explain Docker"})
        assert response.status_code == 200
        body = response.json()
        assert body["context"]["persistent_memories"] == [
            {"id": created.json()["id"], "memory_type": "preference"}
        ]
        assert body["status"] == "needs_clarification"
    finally:
        app.dependency_overrides.clear()
