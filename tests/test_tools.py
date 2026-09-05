from app.services.tools.calculator import CalculatorTool
from app.services.tools.datetime_tool import DateTimeTool
from app.services.tools.file_reader import FileReaderTool
from app.services.tools.registry import ToolRegistry
from app.services.tools.service import ToolService


def test_tool_registration_and_lookup() -> None:
    registry = ToolRegistry()
    calculator = CalculatorTool()
    registry.register(calculator)
    assert registry.get("calculator") is calculator
    assert [tool.name for tool in registry.list_tools()] == ["calculator"]


def test_duplicate_tool_registration_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    try:
        registry.register(CalculatorTool())
    except ValueError as error:
        assert "already registered" in str(error)
    else:
        raise AssertionError("Expected duplicate tool registration to fail.")


def test_calculator_evaluates_allowed_arithmetic() -> None:
    result = CalculatorTool().execute({"expression": "124 * 38"})
    assert result == {"success": True, "result": {"value": 4712}, "error": None}


def test_calculator_rejects_unsafe_expression() -> None:
    result = CalculatorTool().execute({"expression": "__import__('os').system('whoami')"})
    assert result["success"] is False
    assert result["result"] is None
    assert "Invalid expression" in result["error"]


def test_datetime_returns_structured_local_time() -> None:
    result = DateTimeTool().execute({})
    assert result["success"] is True
    assert "datetime" in result["result"]
    assert "timezone" in result["result"]


def test_file_reader_reads_workspace_text_file() -> None:
    result = FileReaderTool().execute({"path": "README.md"})
    assert result["success"] is True
    assert result["result"]["path"] == "README.md"
    assert "# Baby" in result["result"]["content"]


def test_unknown_tool_returns_structured_error() -> None:
    result = ToolService(ToolRegistry()).execute("missing", {})
    assert result == {"success": False, "result": None, "error": "Unknown tool: missing"}
