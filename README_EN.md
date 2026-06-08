# Fancy Agent

[中文](./README.md) | English

A full-stack AI Agent platform. Configure LLMs and MCP servers, compose them into agents for streaming chat sessions, and build with a built-in image generation studio.

## Background

This is a personal side project — something I built while tinkering with various AI tools.

### Why build this

Today's AI products fall into two broad camps: traditional chatbots like ChatGPT / Grok / Claude, and local dev harnesses like Claude Code / Codex that embed deeply into your development environment. This project sits in between — the ease of use of a chatbot, but with far more transparency and control.

Specifically, a few pain points come up when trying to use existing chatbots as agents:

- **Black box**: You can't see the system prompt, don't know what tools are built in, and can't inspect the tool logic — hard to debug when things go wrong
- **No custom tools**: Want to connect your own internal API or business endpoint? Basically not possible
- **Subscription walls**: Free-tier users face limits on file uploads and message counts; using your own API key is often an afterthought

### What this project offers

- **Fully transparent agent configuration**: System prompt, bound tools, and call limits are all visible and editable
- **HTTP API Tool**: One of the core highlights. Most MCP tools are just wrappers around an HTTP endpoint anyway — this project lets you configure any REST API directly as an agent tool, no MCP server needed, just provide a URL and parameters
- **Bring your own API key**: Connect OpenAI, Anthropic, SiliconFlow, or any OpenAI-compatible provider — no platform subscription required
- **Local or public deployment**: Run locally with zero-dependency SQLite, or deploy to a server with Docker Compose
- **Extension features**: Webhook triggers (requires public IP), email notifications, and scheduled tasks for lightweight automation

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) · Async SQLAlchemy + MySQL · LangChain / LangGraph · MCP Adapter |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS v4 |
| Infrastructure | Docker Compose (MySQL + FastAPI + Nginx) |

## Features

- **Agent orchestration** — Freely combine LLMs + MCP tools + custom HTTP API tools
- **Streaming chat** — Real-time SSE output with branching message tree support
- **Human-in-the-loop** — Pause before each tool call and wait for user approval
- **Session workspace** — Each session has an isolated file sandbox directory. Agents can read and write files (code, data, reports, etc.) and generated files appear in the sidebar in real time with single-file or bulk download support; the code execution sandbox is integrated with the workspace so script outputs land on disk immediately
- **Image generation studio** — Supports DALL-E, Stability AI, SiliconFlow, and more
- **File upload & parsing** — Inline PDF, DOCX, TXT, CSV, JSON files directly into messages
- **Scheduled tasks** — Configure daily/weekly/monthly tasks; results can be sent via email
- **Email Agent** — Poll a mailbox and route incoming emails to a specified agent
- **Prompt templates** — Manage reusable prompt snippets with category filtering and one-click copy
- **Token usage stats** — View totals, per-agent breakdown, and a 30-day daily trend
- **JWT auth** — Access token (365 days) + httpOnly refresh token (3650 days)

## Builtin Tools

Besides custom MCP / HTTP API tools, the platform ships a set of ready-to-use tools — just check them when creating an agent:

| Tool | Description |
|---|---|
| `web_search` | Web search (DuckDuckGo / Tavily) |
| `web_fetch` | Fetch a given web page and extract its main content |
| `python_exec` | Run Python in an isolated subprocess sandbox (whitelisted imports, restricted file access) |
| `workspace` | Read/write the current session's file workspace; outputs appear in the sidebar automatically |
| `scheduled_task_manager` | Let the agent create/manage scheduled tasks itself |
| `skill_manager` | Pull skills on demand (SKILL.md + bundled scripts) and run them in the workspace |
| `memory_manager` | Read/write long-term user memory (core memories are auto-injected into the system prompt) |
| `prompt_template_manager` | Query reusable prompt templates |
| `knowledge_graph_manager` | Extract/query knowledge graph nodes and edges |
| `help_document_manager` | Query built-in help documents |

## Deployment

### Option 1: Local development (SQLite, zero dependencies)

The simplest way to get started — no database installation required.

**Backend**

```bash
cd backend
cp .env.sqlite.example .env
uv sync
uv run uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`, API points to `http://localhost:8000`.

---

### Option 2: Local MySQL (separate frontend/backend debugging)

For when you need a real database environment or want to test MySQL-specific behavior. Requires MySQL 8.0+ running locally with the database created.

```sql
CREATE DATABASE fancy_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Backend**

```bash
cd backend
cp .env.mysql.example .env
# Edit .env with your MySQL connection details
uv sync
uv run uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

---

### Option 3: Production (Docker Compose)

All services containerized (MySQL + FastAPI + code sandbox + Nginx). Recommended for server deployment.

**First deployment**

```bash
# 1. Configure backend environment variables
cp backend/.env.docker.example backend/.env
```

Open `backend/.env` and **change these two values**:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Replace with any random string (used for JWT signing) — leaving the placeholder is a security risk |
| `OSS_URL` | Set to your server's actual address, e.g. `http://your-server-ip/files` — used as the base URL for uploaded file links |

```bash
# 2. Set the frontend API address (must be done before building)
# Edit frontend/.env.production and set VITE_API_BASE to your server address:
# VITE_API_BASE=http://your-server-ip
```

> **Why this matters**: The API address is compiled into the static files at build time. Nginx mounts `frontend/dist/` directly from the host — it does not rebuild inside the container. A wrong address means every API call will fail in the browser.

```bash
# 3. Build the frontend (must happen before docker compose)
cd frontend && npm install && npm run build && cd ..

# 4. (Only when dependencies change) Regenerate requirements.txt
# cd backend && uv export --no-hashes --format requirements-txt -o requirements.txt && cd ..

# 5. Start all containers
docker compose up --build -d
```

Once started, visit `http://your-server-ip`, register an account, and you're ready.

> **Note**: The first run pulls base images (MySQL 8.0, Python 3.12-slim, etc.). If you're on a server in mainland China, configure Docker mirror registries first (Docker Desktop → Settings → Docker Engine → add `registry-mirrors`).

**Subsequent updates**

```bash
bash deploy.sh
```

`deploy.sh` handles: pull latest code → overwrite `.env` (from `backend/.env.prd`) → build frontend → restart containers. Create `backend/.env.prd` on the server beforehand (same format as `.env.docker.example`).

> `uv export` automatically adds `; sys_platform == "win32"` markers for Windows-only packages (e.g. `pywin32`), so the Linux Docker build skips them cleanly.

## Quick Start

Once the service is running, here's how to configure your first agent:

1. **Register / Log in** — Open the homepage, register an account, and log in.
2. **Configure an LLM** — On the Models page, add an LLM with its `provider`, `model_name`, `api_key`, and a custom `base_url` (any OpenAI-compatible endpoint works — OpenAI, Anthropic, SiliconFlow, etc.).
3. **(Optional) Set up tools** — When you need external capabilities, configure tools first:
   - **MCP** — Paste a Claude Desktop-format MCP config to import
   - **HTTP API Tool** — Wrap any REST endpoint into a tool via the wizard (URL, method, params, response extraction)
   - **Image Tools** — Connect image generation providers
4. **Create an Agent** — On the Agents page, create an agent: pick an LLM, write a system prompt, check the tools to bind (MCP / API tools / builtin tools), and optionally enable human-in-the-loop approval.
5. **Start chatting** — Go to the chat page, select your agent, and start a streaming conversation with file upload, tool-call visibility, and branch/regenerate support.

## Bot / Webhook Integrations

The platform can connect agents to inbound webhooks, triggered by external events or chat bots. Inbound webhook endpoints are **public (no login required)** and verified per channel via signatures / tokens. **Human-in-the-loop approval is automatically skipped in webhook context** (no human can intervene, so tools execute directly). All channels require a **publicly accessible address**.

| Channel | Endpoint | Required credential | Verification |
|---|---|---|---|
| Generic HTTP | `/api/v1/webhooks/{slug}` | Auto-generated secret | HMAC-SHA256 (`X-Signature` header) |
| Telegram | `/api/v1/telegram/webhooks/{slug}` | Bot Token | `x-telegram-bot-api-secret-token` header |
| DingTalk | `/api/v1/dingtalk/webhooks/{slug}` | App Secret | HMAC-SHA256 + timestamp |
| Discord | `/api/v1/discord/interactions/{slug}` | Public Key | Ed25519 signature |

On the Inbound Webhooks page, pick a channel and enter its credential — the system generates the public URL (and an internal secret).

**Generic HTTP webhook** — The simplest option, ideal for triggering an agent from your own script or system. Request body:

```json
{ "content": "message for the agent", "metadata": {} }
```

The request must include an `X-Signature: sha256=<HMAC>` header, where the signature is `HMAC-SHA256(secret, raw_request_body)`. The response returns `session_id`, `message_id`, and the agent's reply `content`.

**Chat bot channels** — Detailed platform-side setup steps (docs are in Chinese):

- DingTalk: [docs/dingtalk-webhook-setup.md](docs/dingtalk-webhook-setup.md)
- Telegram: [docs/telegram-webhook-setup.md](docs/telegram-webhook-setup.md)
- Discord: [docs/discord-webhook-setup.md](docs/discord-webhook-setup.md)

## Environment Variables

The backend reads `backend/.env` — **all backend commands must be run from the `backend/` directory**, otherwise the relative `.env` path won't load.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | SQLite: `sqlite+aiosqlite:///./fancy_agent.db`; MySQL: `mysql+asyncmy://user:pass@host/db` |
| `SECRET_KEY` | ✅ | JWT signing key — **must be set to a random string; changing it invalidates all active sessions** |
| `OSS_URL` | ✅ | Base URL for uploaded files; use `http://localhost:8000` for local development |
| `UPLOAD_DIR` | ✅ | File upload storage directory, e.g. `./data/uploads` |
| `WORKSPACE_DIR` | ✅ | Agent workspace directory, e.g. `./data/workspaces` |
| `SEARCH_PROVIDER` | — | `duckduckgo` (default) or `tavily` |
| `TAVILY_API_KEY` | — | Required when `SEARCH_PROVIDER=tavily` |
| `EMAIL_ENABLED` | — | Enable email agent (`true` / `false`, default `false`) |
| `EMAIL_PROVIDER` | — | `gmail` / `163` / `qq` / `outlook` |
| `EMAIL_ADDRESS` | — | Mailbox address |
| `EMAIL_PASSWORD` | — | Mailbox password (Gmail requires an app-specific password) |

Frontend reads `frontend/.env.development` / `frontend/.env.production`:

| Variable | Description |
|---|---|
| `VITE_API_BASE` | Backend API address, e.g. `http://localhost:8000` |

## Testing

The backend test suite uses pytest + pytest-asyncio. **No database server required** — integration tests use an in-memory SQLite instance.

```bash
cd backend
uv run pytest                    # run all tests
uv run pytest tests/unit         # unit tests only
uv run pytest tests/integration  # integration tests only
uv run pytest -v                 # verbose output
```

### Test structure

```
backend/tests/
├── conftest.py                    # shared fixtures (in-memory SQLite engine + session)
├── unit/
│   ├── test_compress_util.py      # _extract_text pure function
│   ├── test_message_processor.py  # MessageConverter / MessageProcessor
│   ├── test_schemas.py            # ValidChatModel / ValidAgent Pydantic validation
│   └── test_security.py           # JWT generation and parsing
└── integration/
    ├── test_base_mapper.py        # BaseMapper generic CRUD
    └── test_agent_service.py      # AgentService business logic
```

- **Unit tests** — Pure Python, no database dependency, run by importing the module directly
- **Integration tests** — Use the `async_session` fixture from `conftest.py`; each test gets its own in-memory SQLite instance that rolls back on completion

### Adding new tests

Integration tests receive the `async_session: AsyncSession` fixture directly — no manual session setup needed:

```python
class TestFooService:
    async def test_create(self, async_session: AsyncSession):
        service = FooService(async_session)
        result = await service.create({"name": "bar"})
        assert result.name == "bar"
```

If you add a new Model, import it at the top of `conftest.py` so `create_all` picks it up:

```python
from app.models.foo import Foo  # noqa: F401
```

## Development Guide

### Sync API types

After modifying backend schemas, regenerate frontend types:

```bash
# 1. Make sure the backend is running and export openapi.json
# 2. Run the codegen command
cd frontend
npx openapi-typescript-codegen --input ./openapi.json --output src/api --client axios
```

> If the backend can't start (e.g. no database available), manually add type files under `src/api/models/`, add service classes under `src/api/services/`, and export them from `src/api/index.ts`.

### Backend architecture

```
Routers (app/api/)
  └─ Services (app/services/)
       └─ Mappers (app/mappers/)
            └─ Models (app/models/)
```

- **Routers** — HTTP / SSE handling, dependency injection, calls services
- **Services** — Business logic, receive `AsyncSession` via constructor injection
- **Mappers** — Extend `BaseMapper[T]` for generic CRUD; custom queries go in subclasses
- **Models** — SQLAlchemy ORM, extend `Base` + `TimestampMixin`

When adding a new resource, follow this order: `model` → `schema` → `mapper` → `service` → `router` → register in `deps/service.py` and `main.py` → import the model inside `init_db()`.

## Project Structure

```
fancy_agent/
├── backend/
│   ├── app/
│   │   ├── api/          # router layer
│   │   ├── core/         # config, database, security, scheduler
│   │   ├── deps/         # FastAPI dependency injection factories
│   │   ├── mappers/      # data access layer
│   │   ├── models/       # ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # business logic layer
│   │   └── utils/        # LangChain tools, image adapters, etc.
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── api/          # auto-generated API client
    │   ├── components/   # shared components
    │   ├── context/      # global state
    │   ├── hooks/        # custom hooks
    │   └── pages/        # page components
    └── package.json
```

## More Documentation

Topic-specific docs under `docs/` (Chinese):

| Doc | Description |
|---|---|
| [dingtalk-webhook-setup.md](docs/dingtalk-webhook-setup.md) | Full DingTalk bot setup steps and troubleshooting |
| [telegram-webhook-setup.md](docs/telegram-webhook-setup.md) | Full Telegram bot setup steps and troubleshooting |
| [discord-webhook-setup.md](docs/discord-webhook-setup.md) | Full Discord slash command setup steps and troubleshooting |
| [sandbox-architecture.md](docs/sandbox-architecture.md) | Security architecture and design of the code execution sandbox |
| [local-limitations.md](docs/local-limitations.md) | Feature differences and trade-offs between SQLite and MySQL |
| [项目结构说明.md](docs/项目结构说明.md) | Detailed project directory structure |
| [stream-interrupt-persist-bug.md](docs/stream-interrupt-persist-bug.md) | Post-mortem of the stream interrupt persistence bug |
| [webhook-smoke-test.md](docs/webhook-smoke-test.md) | Webhook smoke test notes |
