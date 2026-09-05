# Baby — Personal AI Operating System

> A full-stack personal AI assistant that combines LLM reasoning, tool orchestration, persistent memory, voice interaction, Gmail, Google Calendar, web access, and controlled Windows desktop automation.

Baby is a personal AI OS prototype built to explore how an AI assistant can move beyond chat and become an action-oriented system. Instead of giving an LLM unrestricted control, Baby uses a structured orchestration layer that routes requests through explicit tools and services.

## ✨ What Baby Can Do

- 🧠 **AI orchestration** — routes conversations and actionable requests through an AI gateway and task system.
- 🔧 **Tool-based execution** — calculator, date/time, file reading, web search, web fetching, Calendar, Gmail, and desktop tools.
- 🧩 **Provider-independent AI layer** — separates the assistant architecture from the underlying AI provider.
- 💾 **Persistent memory** — stores explicitly created preferences, facts, and instructions using SQLite.
- 💬 **Session persistence** — maintains assistant conversation/session state.
- 📅 **Google Calendar** — read and create calendar events through Google APIs.
- 📧 **Gmail** — access and search email through the Gmail API.
- 🌐 **Web access** — search the web and fetch web content when required.
- 🖥️ **Controlled desktop automation** — open approved applications, URLs and paths, type text, send keyboard shortcuts, and capture screenshots.
- 🎙️ **Voice interface** — browser speech recognition with wake phrase activation and spoken responses.
- 🖥️ **React dashboard** — a dark mission-control style interface for interacting with Baby.

## 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │      React UI        │
                         │  Chat • Voice • UI   │
                         └──────────┬───────────┘
                                    │
                              HTTP / REST
                                    │
                         ┌──────────▼───────────┐
                         │      FastAPI API     │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │ Assistant Orchestrator│
                         └──────┬───────┬────────┘
                                │       │
                    ┌───────────┘       └────────────┐
                    ▼                                ▼
             ┌─────────────┐                  ┌─────────────┐
             │  AI Gateway  │                  │ Task System │
             │ Gemini/Mock │                  │ Analyze     │
             └─────────────┘                  │ Plan        │
                                              │ Execute     │
                                              └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │ Tool Registry│
                                              └──────┬──────┘
                                                     │
          ┌─────────┬────────┬────────┬────────┬────┼───────┬─────────┐
          ▼         ▼        ▼        ▼        ▼    ▼       ▼         ▼
      Calculator  Date/Time  Files    Web    Calendar Gmail  Desktop  ...
```

## 🔄 Request Flow

For an actionable request, Baby follows a structured path rather than allowing the model to directly execute arbitrary operations:

```text
User request
     │
     ▼
Assistant Orchestrator
     │
     ├── Normal conversation ──► AI Provider ──► Response
     │
     └── Actionable request
              │
              ▼
        Task Analyzer
              │
              ▼
        Task Planner
              │
              ▼
        Tool Registry
              │
              ▼
        Task Executor
              │
              ▼
        Tool / External Service
              │
              ▼
           Result
```

This separation keeps **reasoning, planning, and execution** as distinct responsibilities.

## 🧰 Tool System

| Tool | Purpose |
|---|---|
| `calculator` | Arithmetic calculations |
| `datetime` | Date and time operations |
| `file_reader` | Read approved local text files |
| `web_search` | Search the web |
| `web_fetch` | Retrieve web content |
| `calendar` | Google Calendar operations |
| `email` | Gmail operations |
| `desktop` | Controlled Windows desktop actions |

The `ToolRegistry` manages available tools, while the task system determines and executes the required tool steps.

## 🧠 AI Gateway

Baby separates the assistant architecture from the AI provider through a provider abstraction.

The project includes:

- `AIProvider` — generic provider contract
- `GeminiProvider` — Gemini-backed AI provider
- `MockAIProvider` — deterministic local provider for development and testing

This allows the application architecture to remain independent of a single model provider.

## 💾 Persistent Memory

Baby includes a local memory layer backed by SQLite:

```text
MemoryService
      │
      ▼
MemoryRepository
      │
      ▼
SQLite
```

Supported memory categories include:

- `preference`
- `fact`
- `instruction`

Memory is explicitly created through the application rather than automatically storing every conversation.

## 📅 Gmail & Google Calendar

Baby integrates with Google services through their APIs.

### Google Calendar

Baby can read calendar information and create events through the authenticated Calendar integration.

### Gmail

Baby can retrieve and search email through the authenticated Gmail integration.

OAuth credentials and tokens are intentionally excluded from version control.

## 🖥️ Controlled Desktop Automation

Baby includes a deliberately constrained Windows desktop tool layer.

Supported capabilities include:

- Opening approved applications
- Opening HTTP/HTTPS URLs
- Opening existing files and folders
- Typing text
- Sending keyboard shortcuts
- Capturing screenshots

The desktop layer uses an explicit allowlist for supported applications and does not provide unrestricted shell execution or arbitrary autonomous clicking.

This boundary is intentional: the goal is to demonstrate **controlled computer interaction**, not unrestricted computer-use autonomy.

## 🎙️ Voice Interface

Baby's frontend supports browser-based voice interaction using:

- Speech Recognition
- `en-IN` language recognition
- Wake phrase: **"Hey Baby"**
- Browser/OS speech synthesis for spoken responses

The browser requires the user to activate microphone access once. After activation, Baby can continuously listen for the wake phrase while voice mode is active.

## 🖥️ Frontend

The frontend is built with React and Vite.

The dashboard provides:

- Central assistant interface
- Voice control
- Chat interaction
- Calendar panel
- Email panel
- Quick actions
- Calendar event creation
- Email reading
- Dark mission-control inspired visual design

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python |
| API | FastAPI |
| AI | Google Gemini + local Mock provider |
| Frontend | React + Vite |
| Database | SQLite |
| Calendar | Google Calendar API |
| Email | Gmail API |
| Voice | Browser Speech Recognition + Speech Synthesis |
| Desktop | Python desktop automation |
| Testing | Pytest |
| Configuration | `.env` / environment variables |

## 📁 Project Structure

```text
Baby/
├── app/
│   ├── api/
│   ├── core/
│   └── services/
│       ├── assistant/
│       ├── calendar/
│       ├── email/
│       ├── memory/
│       ├── providers/
│       ├── session/
│       ├── tasks/
│       └── tools/
├── frontend/
│   └── src/
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## 🚀 Local Setup

### Prerequisites

- Python 3.12
- Node.js / npm
- Google API credentials for Gmail and Calendar features
- A Gemini API key for Gemini-backed AI features

### Backend

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Configure the required environment variables using `.env.example`.

Start the FastAPI backend:

```powershell
uvicorn app.main:app --reload --port 8001
```

The API will be available at:

```text
http://127.0.0.1:8001
```

FastAPI documentation:

```text
http://127.0.0.1:8001/docs
```

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Then open the Vite development URL shown in the terminal.

## 🧪 Testing

Run the automated test suite from the project root:

```powershell
pytest
```

Integration checks for external services are also included in the repository.

## 🔐 Security & Design Boundaries

Baby is designed around explicit control boundaries.

- Secrets and OAuth credentials are excluded from Git.
- Local runtime data is excluded from Git.
- File reading is restricted to approved text-file types and safe paths.
- Desktop applications are allowlisted.
- Desktop URLs are restricted to HTTP/HTTPS.
- Desktop actions are exposed through dedicated tools rather than arbitrary shell execution.
- Memory is explicitly created instead of automatically persisting every conversation.
- Tool execution happens through the registered tool system.

These constraints are part of the architecture, not afterthoughts.

## 📌 Current Status

**Baby V1.0 — Functional Personal AI OS Prototype**

Implemented:

- [x] FastAPI backend
- [x] Provider-independent AI gateway
- [x] Gemini integration
- [x] Deterministic mock AI provider
- [x] Tool registry and execution system
- [x] Calculator and date/time tools
- [x] File reading
- [x] Web search and fetch
- [x] Persistent memory
- [x] Session persistence
- [x] Task analysis, planning and execution
- [x] Gmail integration
- [x] Google Calendar integration
- [x] React/Vite dashboard
- [x] Voice interface
- [x] Controlled Windows desktop automation
- [x] Automated tests

## 🧭 Future Directions

Possible future development includes:

- More robust wake-word detection
- Neural/local text-to-speech
- More desktop actions with stronger confirmation controls
- Richer multi-step planning
- Better memory retrieval and ranking
- Additional external service integrations
- Improved observability and execution history
- Production deployment and authentication

## 🎯 Why Baby?

Baby is an exploration of the architecture required to turn a conversational AI model into an **action-oriented personal operating system**.

The core idea is simple:

> **The model reasons. The system decides. The tools act.**

By separating these responsibilities, Baby can evolve from a chat interface into a modular AI system capable of interacting with both digital services and the user's computer.

## 👤 Author

**Rajdeep Sonkar**

Built as a personal AI systems project focused on AI orchestration, automation, memory, tool use, and full-stack engineering.
