# Baby

Minimal FastAPI backend for the Baby personal AI OS.

## Mock AI architecture

Baby V0.2 exposes `POST /chat` with a JSON body such as `{"message": "Hello Baby"}`.
The API delegates to `AIService`, which depends only on the generic `AIProvider`
contract. The current `MockAIProvider` returns deterministic local text and makes
no network or external API calls. A future provider can implement the same
`generate(message)` method without changing the API layer.

## Local tools

Baby V0.3 adds an offline Tool System separate from AI-provider selection.
`ToolRegistry` manages uniquely named tools, and `ToolService` executes them.
The default local tools are `calculator`, `datetime`, and `file_reader`.

Use `GET /tools` to inspect their descriptions and input schemas. Execute one
with `POST /tools/{tool_name}/execute`, for example:

```json
{"input": {"expression": "124 * 38"}}
```

`file_reader` only accepts approved text-file types at safe relative paths
inside this workspace; it never writes files. The AI provider does not select
or invoke tools yet.

## Local memory

Baby V0.4 adds a persistent memory layer independent of AI providers and tools:

```text
API → MemoryService → MemoryRepository → SQLite
```

Memories are explicitly created through the API—chat messages are never stored
automatically. Supported memory types are `preference`, `fact`, and
`instruction`. Basic validation rejects obvious passwords, API keys, tokens,
and secrets.

The local SQLite database is created on first memory API use at `data/baby.db`.
It is not stored in `.venv` and uses only Python's built-in `sqlite3` module.

Examples:

```http
POST /memory
Content-Type: application/json

{"memory_type": "preference", "content": "Keep my emails concise and professional."}
```

```http
GET /memory/search?q=emails
```

## Task planning

Baby V0.5 adds a deterministic planning foundation. It recognizes the existing
local capabilities—calculator, date/time, and text-file reading—without calling
an LLM or executing a tool:

```text
API -> TaskService -> TaskAnalyzer -> TaskPlanner -> ToolRegistry -> TaskPlan
```

`POST /tasks/plan` accepts a natural-language task and returns either pending
steps or `needs_clarification`. For example:

```json
{"message": "calculate 20 + 30"}
```

returns a plan with a `calculator` step and `{"expression": "20 + 30"}`.
Requests such as `book a restaurant` or `do this` return a useful clarification
question rather than pretending Baby can perform an unsupported action.

## Task execution

Baby V0.6 executes only an existing planned task, using registered local tools:

```text
API -> TaskService -> TaskExecutor -> ToolService -> ToolRegistry -> Local Tool
```

Planning and execution remain separate. `POST /tasks/plan` only creates pending
steps; `POST /tasks/{task_id}/execute` runs those pending steps in order. Each
step progresses from `pending` to `running` to either `completed` (with a
stored result) or `failed` (with an error). A failed step stops all later steps,
which remain pending.

Tasks needing clarification cannot be executed and return HTTP `409 Conflict`.
The executor never invents tools: it runs only tools present in the existing
ToolRegistry. No files, shell commands, or external services are executed.

Example:

```http
POST /tasks/{task_id}/execute
```

For a planned `calculate 25 * 4` task, the completed step stores:

```json
{"value": 100}
```

The deterministic analyzer and planner can later be replaced or augmented by
an LLM without changing the task API.

## Local AI-to-task orchestration

Baby V0.7 connects the local deterministic AI gateway to the existing planner
and executor:

```text
User request -> AI Gateway -> local mock interpretation -> TaskService
-> TaskExecutor -> ToolService -> ToolRegistry -> Local Tool
```

`POST /assistant/chat` accepts a message, obtains a deterministic interpretation
from the local `MockAIProvider`, creates a task plan, and executes supported
tasks through the existing task and tool services. The provider remains fully
local—there is no external AI API.

```http
POST /assistant/chat
Content-Type: application/json

{"message": "calculate 25 * 4"}
```

The response includes the task lifecycle and final tool result:

```json
{
  "message": "calculate 25 * 4",
  "interpretation": "calculator",
  "task_id": "...",
  "status": "completed",
  "response": "100"
}
```

Unsupported or ambiguous messages return structured `needs_clarification`
responses and are never executed.

## Context-aware memory

Baby V0.8 adds a fully local memory-retrieval step before mock AI
interpretation:

```text
User message -> relevant persistent memories -> AssistantService
-> MockAIProvider -> TaskService -> TaskExecutor
```

Persistent memory is long-lived information created explicitly through the
memory API. Session context is not implemented in V0.8; each assistant request
is independent. Task state remains in the in-memory task store and is never
written as user memory.

The assistant extracts message tokens, uses the existing local memory search to
find candidates, scores them deterministically, and uses at most three matches.
Only memory IDs and types are returned in the assistant response; selected
content is supplied internally to the local MockAIProvider and is not exposed.

```http
POST /memory
Content-Type: application/json

{"memory_type": "preference", "content": "Keep Docker explanations clear and practical."}
```

```http
POST /assistant/chat
Content-Type: application/json

{"message": "Explain Docker"}
```

The response includes safe context metadata:

```json
{
  "status": "needs_clarification",
  "context": {
    "user_message": "Explain Docker",
    "persistent_memories": [{"id": 1, "memory_type": "preference"}],
    "session_id": null
  }
}
```

V0.8 remains provider-independent and uses only the deterministic local mock;
no external AI service, embedding model, or vector database is involved.

## Requirements

- Python 3.12

## Install

Activate the existing Python 3.12 virtual environment, then install the project and development dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
uvicorn app.main:app --reload
```

The API provides `GET /`, `GET /health`, `POST /chat`, `GET /tools`,
`POST /tools/{tool_name}/execute`, and these memory endpoints:

- `POST /memory`
- `GET /memory`
- `GET /memory/search?q=...`
- `GET /memory/{memory_id}`
- `PUT /memory/{memory_id}`
- `DELETE /memory/{memory_id}`

Task planning endpoints:

- `POST /tasks/plan`
- `GET /tasks/{task_id}`
- `POST /tasks/{task_id}/execute`
- `POST /assistant/chat`

## Test

```powershell
pytest
```
