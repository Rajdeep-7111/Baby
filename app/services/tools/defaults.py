"""Default local tool configuration for the Baby API."""

from app.services.calendar.service import CalendarService
from app.services.tools.calendar import CalendarTool
from app.services.tools.calculator import CalculatorTool
from app.services.tools.datetime_tool import DateTimeTool
from app.services.tools.file_reader import FileReaderTool
from app.services.tools.registry import ToolRegistry
from app.services.tools.service import ToolService
from app.services.tools.web_fetch import WebFetchTool
from app.services.tools.web_search import WebSearchTool
from app.services.tools.email import EmailTool
from app.services.tools.desktop import DesktopTool

def create_tool_registry() -> ToolRegistry:
    """Create Baby's default local tool registry."""

    registry = ToolRegistry()

    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileReaderTool())
    registry.register(WebSearchTool())
    registry.register(WebFetchTool())
    registry.register(CalendarTool(CalendarService()))
    registry.register(EmailTool())
    registry.register(DesktopTool())
    
    return registry


tool_registry = create_tool_registry()
tool_service = ToolService(tool_registry)