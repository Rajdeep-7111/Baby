from fastapi.testclient import TestClient

from app.api.routes import get_task_service
from app.main import app
from app.services.tasks.analyzer import TaskAnalyzer
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.planner import TaskPlanner
from app.services.tasks.service import TaskNotExecutableError, TaskService
from app.services.tools.defaults import tool_registry, tool_service


def make_task_service() -> TaskService:
    return TaskService(TaskAnalyzer(), TaskPlanner(tool_registry), TaskExecutor(tool_registry, tool_service))


def test_calculator_task_planning() -> None:
    plan = make_task_service().plan_task("calculate 25 * 10")

    assert plan.status == "planned"
    assert plan.steps[0].tool_name == "calculator"
    assert plan.steps[0].arguments == {"expression": "25 * 10"}


def test_datetime_task_planning() -> None:
    plan = make_task_service().plan_task("what time is it?")

    assert plan.status == "planned"
    assert [step.model_dump() for step in plan.steps] == [
        {
            "step_id": 1,
            "description": "Get the current local date and time",
            "tool_name": "datetime",
            "arguments": {},
            "status": "pending",
            "result": None,
            "error": None,
        }
    ]


def test_file_reader_task_planning() -> None:
    plan = make_task_service().plan_task("read notes.txt")

    assert plan.status == "planned"
    assert plan.steps[0].tool_name == "file_reader"
    assert plan.steps[0].arguments == {"path": "notes.txt"}


def test_unsupported_request_needs_clarification() -> None:
    plan = make_task_service().plan_task("translate this to French")

    assert plan.status == "needs_clarification"
    assert plan.steps == []
    assert plan.clarification_question is not None


def test_ambiguous_request_needs_clarification() -> None:
    plan = make_task_service().plan_task("do this")

    assert plan.status == "needs_clarification"
    assert "What would you like" in plan.clarification_question


def test_restaurant_request_gets_specific_clarification() -> None:
    plan = make_task_service().plan_task("book a restaurant")

    assert plan.status == "needs_clarification"
    assert "location" in plan.clarification_question


def test_multiple_supported_task_steps_are_planned() -> None:
    plan = make_task_service().plan_task("calculate 2 + 2 and what time is it?")

    assert plan.status == "planned"
    assert [step.tool_name for step in plan.steps] == ["calculator", "datetime"]


def test_calculator_task_execution_stores_result_and_completes_task() -> None:
    service = make_task_service()
    planned = service.plan_task("calculate 25 * 4")

    executed = service.execute_task(planned.task_id)

    assert executed is not None
    assert executed.status == "completed"
    assert executed.steps[0].status == "completed"
    assert executed.steps[0].result == {"value": 100}
    assert executed.steps[0].error is None


def test_datetime_and_file_reader_task_execution() -> None:
    service = make_task_service()

    datetime_task = service.execute_task(service.plan_task("what time is it?").task_id)
    file_task = service.execute_task(service.plan_task("read README.md").task_id)

    assert datetime_task is not None
    assert datetime_task.steps[0].status == "completed"
    assert "datetime" in datetime_task.steps[0].result
    assert file_task is not None
    assert file_task.steps[0].status == "completed"
    assert "# Baby" in file_task.steps[0].result["content"]


def test_multi_step_execution_completes_in_order() -> None:
    service = make_task_service()
    planned = service.plan_task("calculate 2 + 2 and what time is it?")

    executed = service.execute_task(planned.task_id)

    assert executed is not None
    assert executed.status == "completed"
    assert [step.status for step in executed.steps] == ["completed", "completed"]
    assert executed.steps[0].result == {"value": 4}
    assert "datetime" in executed.steps[1].result


def test_failed_step_stops_later_steps() -> None:
    service = make_task_service()
    planned = service.plan_task("calculate 1 / 0 and what time is it?")

    executed = service.execute_task(planned.task_id)

    assert executed is not None
    assert executed.status == "failed"
    assert executed.steps[0].status == "failed"
    assert "Invalid expression" in executed.steps[0].error
    assert executed.steps[1].status == "pending"
    assert executed.steps[1].result is None


def test_clarification_and_unknown_tasks_cannot_execute() -> None:
    service = make_task_service()
    clarification = service.plan_task("do this")
    unsupported = service.plan_task("translate this to French")

    try:
        service.execute_task(clarification.task_id)
    except TaskNotExecutableError as error:
        assert "need clarification" in str(error)
    else:
        raise AssertionError("A clarification task must not execute.")
    try:
        service.execute_task(unsupported.task_id)
    except TaskNotExecutableError as error:
        assert "need clarification" in str(error)
    else:
        raise AssertionError("An unsupported task must not execute.")
    assert service.execute_task("unknown-task") is None


def test_task_api_plans_executes_and_retrieves_task() -> None:
    service = make_task_service()
    app.dependency_overrides[get_task_service] = lambda: service
    client = TestClient(app)

    try:
        planned = client.post("/tasks/plan", json={"message": "calculate 25 * 4"})
        assert planned.status_code == 200
        plan = planned.json()
        assert plan["status"] == "planned"
        assert plan["steps"][0]["arguments"] == {"expression": "25 * 4"}

        executed = client.post(f"/tasks/{plan['task_id']}/execute")
        assert executed.status_code == 200
        assert executed.json()["status"] == "completed"
        assert executed.json()["steps"][0]["result"] == {"value": 100}

        retrieved = client.get(f"/tasks/{plan['task_id']}")
        assert retrieved.status_code == 200
        assert retrieved.json() == executed.json()
        assert client.get("/tasks/unknown-task").status_code == 404
        clarification = client.post("/tasks/plan", json={"message": "do this"}).json()
        assert client.post(f"/tasks/{clarification['task_id']}/execute").status_code == 409
    finally:
        app.dependency_overrides.clear()
