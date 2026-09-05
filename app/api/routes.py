from typing import Any

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.config import settings
from app.services.ai import ai_service
from app.services.assistant.service import AssistantResponse, AssistantService
from app.services.assistant.session import SessionService
from app.services.memory.database import MemoryDatabase, default_memory_database_path
from app.services.memory.models import (
    CreateMemoryRequest,
    Memory,
    UpdateMemoryRequest,
)
from app.services.memory.repository import MemoryRepository
from app.services.memory.service import MemoryService
from app.services.tasks.analyzer import TaskAnalyzer
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.models import TaskPlan, TaskRequest
from app.services.tasks.planner import TaskPlanner
from app.services.tasks.service import (
    TaskNotExecutableError,
    TaskService,
)
from app.services.tools.defaults import tool_registry, tool_service

router = APIRouter()


def get_memory_service() -> MemoryService:
    """Create the default local memory service on demand."""

    database = MemoryDatabase(default_memory_database_path())

    return MemoryService(
        MemoryRepository(database)
    )


task_service = TaskService(
    TaskAnalyzer(),
    TaskPlanner(tool_registry),
    TaskExecutor(
        tool_registry,
        tool_service,
    ),
)

# One temporary session store for the running Baby process.
session_service = SessionService()

assistant_service = AssistantService(
    ai_service,
    task_service,
    get_memory_service,
    session_service,
)


def get_task_service() -> TaskService:
    """Return the in-memory task planning service."""

    return task_service


def get_assistant_service() -> AssistantService:
    """Return Baby's local end-to-end assistant orchestrator."""

    return assistant_service

@router.get("/sessions")
def list_sessions() -> list:
    """List Baby's stored conversation sessions."""

    return session_service.list_sessions()


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> object:
    """Retrieve one conversation session."""

    session = session_service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    return session


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_session(session_id: str) -> Response:
    """Delete one conversation session."""

    if not session_service.delete_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )

class ChatRequest(BaseModel):
    """A user's message to Baby."""

    message: str = Field(
        min_length=1,
        max_length=4_000,
    )

    session_id: str | None = None


class ChatResponse(BaseModel):
    """Baby's response to a user message."""

    response: str


class ToolInfo(BaseModel):
    """Public metadata for a registered tool."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolListResponse(BaseModel):
    tools: list[ToolInfo]


class ToolExecutionRequest(BaseModel):
    """Structured input passed to a tool."""

    input: dict[str, Any]


class ToolExecutionResponse(BaseModel):
    """Structured outcome returned by a tool."""

    success: bool
    result: Any | None = None
    error: str | None = None


@router.get("/")
async def root() -> dict[str, str]:
    """Identify the application."""

    return {
        "app": settings.app_name,
        "message": "Baby personal AI OS",
    }


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API is available."""

    return {
        "status": "ok",
        "service": settings.app_name,
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Generate a response using Baby's configured AI provider."""

    return ChatResponse(
        response=ai_service.generate(request.message)
    )


@router.post(
    "/assistant/chat",
    response_model=AssistantResponse,
)
def assistant_chat(
    request: ChatRequest,
    service: AssistantService = Depends(
        get_assistant_service
    ),
) -> AssistantResponse:
    """Interpret, plan, execute, and maintain a conversation session."""

    try:
        return service.handle_message(
            request.message,
            session_id=request.session_id,
        )

    except ValueError as error:
        # Invalid/unknown session IDs should be a clean 404.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


# ============================================================
# Dashboard integrations
# ============================================================

@router.get("/calendar/today")
def calendar_today() -> dict[str, Any]:
    """Return today's Google Calendar events for the dashboard."""

    calendar_tool = tool_registry.get("calendar")

    if calendar_tool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Calendar tool is not configured.",
        )

    result = tool_service.execute(
        "calendar",
        {
            "operation": "today",
        },
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result["error"] or "Unable to retrieve calendar events.",
        )

    return result["result"]

@router.post("/calendar/events")
def create_calendar_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a calendar event through Baby's Calendar tool."""

    calendar_tool = tool_registry.get("calendar")

    if calendar_tool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Calendar tool is not configured.",
        )

    required_fields = ["title", "start", "end"]

    for field in required_fields:
        if not payload.get(field):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{field}' is required.",
            )

    tool_input = {
        "operation": "create",
        "title": payload["title"],
        "start": payload["start"],
        "end": payload["end"],
    }

    if payload.get("description"):
        tool_input["description"] = payload["description"]

    result = tool_service.execute(
        "calendar",
        tool_input,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result["error"] or "Unable to create calendar event.",
        )

    return result["result"]



@router.get("/email/recent")
def email_recent(
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """Return recent Gmail messages for the dashboard."""

    email_tool = tool_registry.get("email")

    if email_tool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email tool is not configured.",
        )

    result = tool_service.execute(
        "email",
        {
            "operation": "recent",
            "max_results": limit,
        },
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result["error"] or "Unable to retrieve emails.",
        )

    return result["result"]

@router.get("/email/{message_id}")
def email_read(
    message_id: str,
) -> dict[str, Any]:
    """Return the full contents of one Gmail message."""

    email_tool = tool_registry.get("email")

    if email_tool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email tool is not configured.",
        )

    result = tool_service.execute(
        "email",
        {
            "operation": "read",
            "message_id": message_id,
        },
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                result["error"]
                or "Unable to retrieve email."
            ),
        )

    return result["result"]


@router.get(
    "/tools",
    response_model=ToolListResponse,
)
async def list_tools() -> ToolListResponse:
    """List the local tools available to Baby."""

    return ToolListResponse(
        tools=tool_service.list_tools()
    )


@router.post(
    "/tools/{tool_name}/execute",
    response_model=ToolExecutionResponse,
)
async def execute_tool(
    tool_name: str,
    request: ToolExecutionRequest,
) -> ToolExecutionResponse:
    """Execute one registered local tool without involving an AI provider."""

    return ToolExecutionResponse(
        **tool_service.execute(
            tool_name,
            request.input,
        )
    )


@router.post(
    "/tasks/plan",
    response_model=TaskPlan,
)
def plan_task(
    request: TaskRequest,
    service: TaskService = Depends(
        get_task_service
    ),
) -> TaskPlan:
    """Analyze a task and return a plan without executing its steps."""

    return service.plan_task(request.message)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskPlan,
)
def get_task(
    task_id: str,
    service: TaskService = Depends(
        get_task_service
    ),
) -> TaskPlan:
    """Retrieve a task plan from the V0.5 in-memory store."""

    task = service.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return task


@router.post(
    "/tasks/{task_id}/execute",
    response_model=TaskPlan,
)
def execute_task(
    task_id: str,
    service: TaskService = Depends(
        get_task_service
    ),
) -> TaskPlan:
    """Execute the pending steps of an existing task plan."""

    try:
        task = service.execute_task(task_id)

    except TaskNotExecutableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return task


@router.post(
    "/memory",
    response_model=Memory,
    status_code=status.HTTP_201_CREATED,
)
def create_memory(
    request: CreateMemoryRequest,
    service: MemoryService = Depends(
        get_memory_service
    ),
) -> Memory:
    """Explicitly create a local Baby memory."""

    try:
        return service.remember(
            request.memory_type,
            request.content,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


@router.get(
    "/memory",
    response_model=list[Memory],
)
def list_memories(
    service: MemoryService = Depends(
        get_memory_service
    ),
) -> list[Memory]:
    """List explicitly stored local memories."""

    return service.list_memories()


@router.get(
    "/memory/search",
    response_model=list[Memory],
)
def search_memories(
    q: str = Query(min_length=1),
    service: MemoryService = Depends(
        get_memory_service
    ),
) -> list[Memory]:
    """Search local memory content by text."""

    try:
        return service.search_memories(q)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


@router.get(
    "/memory/{memory_id}",
    response_model=Memory,
)
def get_memory(
    memory_id: int,
    service: MemoryService = Depends(
        get_memory_service
    ),
) -> Memory:
    """Retrieve a memory by ID."""

    memory = service.get_memory(memory_id)

    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found.",
        )

    return memory


@router.put(
    "/memory/{memory_id}",
    response_model=Memory,
)
def update_memory(
    memory_id: int,
    request: UpdateMemoryRequest,
    service: MemoryService = Depends(
        get_memory_service
    ),
) -> Memory:
    """Update an existing memory."""

    try:
        memory = service.update_memory(
            memory_id,
            request.memory_type,
            request.content,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found.",
        )

    return memory


@router.delete(
    "/memory/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_memory(
    memory_id: int,
    service: MemoryService = Depends(
        get_memory_service
    ),
) -> Response:
    """Permanently delete a local memory."""

    if not service.forget_memory(memory_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found.",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )