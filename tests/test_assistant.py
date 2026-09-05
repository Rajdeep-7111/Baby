from fastapi.testclient import TestClient

from app.api.routes import get_assistant_service
from app.main import app
from app.services.ai import AIService
from app.services.assistant.service import AssistantService
from app.services.providers.mock import MockAIProvider
from app.services.tasks.analyzer import TaskAnalyzer
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.planner import TaskPlanner
from app.services.tasks.service import TaskService
from app.services.tools.defaults import tool_registry, tool_service


def make_assistant_service() -> tuple[AssistantService, TaskService]:
    tasks = TaskService(TaskAnalyzer(), TaskPlanner(tool_registry), TaskExecutor(tool_registry, tool_service))
    return AssistantService(AIService(MockAIProvider()), tasks), tasks


def test_assistant_calculator_end_to_end_propagates_task_result() -> None:
    assistant, tasks = make_assistant_service()

    response = assistant.handle_message("calculate 25 * 4")

    assert response.interpretation == "calculator"
    assert response.status == "completed"
    assert response.response == "100"
    assert response.steps[0].result == {"value": 100}
    assert tasks.get_task(response.task_id).status == "completed"


def test_assistant_datetime_and_file_reader_end_to_end() -> None:
    assistant, _ = make_assistant_service()

    datetime_response = assistant.handle_message("what time is it?")
    file_response = assistant.handle_message("read README.md")

    assert datetime_response.status == "completed"
    assert datetime_response.interpretation == "datetime"
    assert "Current local date and time:" in datetime_response.response
    assert file_response.status == "completed"
    assert file_response.interpretation == "file_reader"
    assert file_response.response == "Read README.md successfully."


def test_assistant_unsupported_and_clarification_requests_do_not_execute() -> None:
    assistant, _ = make_assistant_service()

    unsupported = assistant.handle_message("translate this to French")
    clarification = assistant.handle_message("book a restaurant")

    assert unsupported.interpretation == "unsupported"
    assert unsupported.status == "needs_clarification"
    assert unsupported.steps == []
    assert clarification.interpretation == "needs_clarification"
    assert clarification.status == "needs_clarification"
    assert "location" in clarification.response


def test_assistant_propagates_execution_failure() -> None:
    assistant, _ = make_assistant_service()

    response = assistant.handle_message("calculate 1 / 0")

    assert response.status == "failed"
    assert "Invalid expression" in response.response
    assert response.steps[0].status == "failed"
    assert "Invalid expression" in response.steps[0].error


def test_assistant_chat_api_returns_completed_lifecycle() -> None:
    assistant, tasks = make_assistant_service()
    app.dependency_overrides[get_assistant_service] = lambda: assistant
    client = TestClient(app)

    try:
        response = client.post("/assistant/chat", json={"message": "calculate 25 * 4"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["response"] == "100"
        assert body["steps"][0]["result"] == {"value": 100}
        assert tasks.get_task(body["task_id"]).status == "completed"
    finally:
        app.dependency_overrides.clear()
