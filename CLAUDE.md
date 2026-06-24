# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fancy Agent is a full-stack AI agent platform. Users can configure LLMs, MCP (Model Context Protocol) servers, and compose them into agents for streaming chat sessions. It also includes an independent image generation studio.

- **Backend**: FastAPI (Python 3.12), async SQLAlchemy with dual-dialect MySQL + SQLite support, LangChain/LangGraph, MCP adapter
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4
- **Infra**: Docker Compose (MySQL + FastAPI + Nginx) for prod; SQLite for local dev with no DB server

Design notes and incident write-ups live in `docs/` — check there before re-investigating known issues.

## Commands

### Backend

```bash
cd backend
uv sync                              # install dependencies
uv run uvicorn app.main:app          # run dev server (port 8000)
uv run uvicorn app.main:app --reload # run with auto-reload
uv run pytest                        # run the full test suite (unit + integration)
uv run pytest tests/unit             # unit tests only
uv run pytest tests/unit/test_sqlite_compat.py::TestName  # single test
```

Tests live under `backend/tests/{unit,integration}/` and use an in-memory SQLite via `tests/conftest.py` — they do not need MySQL or a running server. `pyproject.toml` configures `asyncio_mode = "auto"` so `async def test_*` works without `@pytest.mark.asyncio`.

### Frontend

```bash
cd frontend
npm install
npm run dev      # dev server
npm run build    # production build (tsc + vite)
npm run lint     # ESLint check
```

### Quality Gates

Before considering a change complete:
- **Frontend** changes must pass `npm run lint` **and** `npm run build` (the latter runs `tsc -b`). Trivial UI tweaks don't need *new* test cases, but the lint + type gate is non-negotiable.
- **Backend** changes should run the relevant `uv run pytest` — at least the affected `tests/unit` — and add/extend tests for new logic. This is the same bar as frontend, not a lighter one.

### Docker (full stack)

Before the first build (or after backend dependency changes), regenerate `backend/requirements.txt`:

```bash
cd backend && uv export --no-hashes --format requirements-txt -o requirements.txt
```

Then: `docker compose up --build`

### Production Deploy

部署配置集中在仓库根的 **`deploy.config`**（从 `deploy.config.example` 复制，已 gitignore，含密钥，`git reset --hard` 不会清除）。换服务器/域名通常只改 `PUBLIC_HOST` 一行。

```bash
cp deploy.config.example deploy.config   # 首次：填写 PUBLIC_HOST / DB_PASSWORD / SECRET_KEY 等
bash deploy.sh                           # 拉取 origin/main → configure.sh 渲染配置 → 构建前端 → 重启容器
```

`configure.sh` 由 `deploy.sh` 在 `git reset --hard` 之后调用，从 `deploy.config` 渲染出两份文件（均为生成物，勿手改）：
- `backend/.env` — `DATABASE_URL`（密码自动 URL 编码）、`OSS_URL`、`CORS_ORIGINS`、`SECRET_KEY`、邮件/搜索等
- 仓库根 `.env` — `DB_PASSWORD`/`DB_NAME`，供 `docker-compose.yml` 变量插值（MySQL 密码不再硬编码）

前端生产构建使用空 `VITE_API_BASE`（相对路径），无需写入域名；换域名/IP 不需要重新构建前端。

旧的 `backend/.env.prd` 流程已废弃。

## Commit Conventions

Use short prefixed messages matching the existing history: `feature:`, `fix:`, `docs:`, `refactor:`. Keep each commit focused on one logical change; avoid mixed backend/frontend commits unless tightly coupled.

**The `master` branch is protected — do not push to it directly.** Submit changes via a feature branch + PR:

```bash
git switch -c your-branch-name
git add .
git commit -m "type: short description"
git push -u origin your-branch-name
```

Then open a PR on GitHub to merge the branch back into `master`.

## Architecture

### Backend Layer Structure

```
routers (app/api/) → services (app/services/) → mappers (app/mappers/) → models (app/models/)
```

- **Routers** handle HTTP/SSE, DI, call services.
- **Services** receive `AsyncSession` via constructor injection — **except `ChatService`**, which uses `get_db_session()` context manager directly to avoid session lifetime issues.
- **Mappers** extend `BaseMapper[T]` — generic async CRUD (`get_by_id`, `list_by_filters`, `create_from_dict`, `update_by_id`, `delete_by_id`). Custom queries live in subclasses.
- **Models** use `Base` from `app.core.database` + `TimestampMixin`.

### Adding a New Module (Checklist)

1. `app/models/foo_bar.py` — SQLAlchemy model using `Base` + `TimestampMixin`
2. `app/schemas/foo_bar_schema.py` — Pydantic Create/Update/Out schemas
3. `app/mappers/foo_bar_mapper.py` — `class FooBarMapper(BaseMapper[FooBar])`
4. `app/services/foo_bar_service.py` — business logic, calls mapper, commits session
5. `app/api/foo_bar_router.py` — `APIRouter`, uses `Depends(get_foo_bar_service)`
6. `app/deps/service.py` — add `get_foo_bar_service()` factory
7. `app/main.py` — `api_router.include_router(foo_bar_router)`
8. `app/core/database.py` → `init_db()` — add `from app.models.foo_bar import FooBar  # noqa: F401`

### Database Sessions

Two patterns:
- `get_db` (FastAPI `Depends`) — request-scoped session via `app/deps/db.py`
- `get_db_session()` (async context manager) — for services/background tasks that own their session lifecycle; auto-commits on exit, rolls back on exception

`expire_on_commit=False` — ORM objects remain usable after commit without re-querying.

**Dual-dialect (MySQL + SQLite)** — `app/core/database.py` branches on `DATABASE_URL` prefix. SQLite gets a `PRAGMA foreign_keys=ON` event listener on every new connection — **`ON DELETE CASCADE` is silently off by default in SQLite** without this. When writing models, avoid MySQL-only features; `JSON` and `func.json_extract` work on both. The conftest mirrors the PRAGMA listener so FK behaviour matches in tests.

Models auto-register via transitive imports from `main.py`. Only models not reachable through router imports need an explicit `import` inside `init_db()` before `create_all` — when in doubt, add it.

### Auth

JWT-based. Login returns a 30-day access token and sets a `refresh_token` httpOnly cookie (365-day). Frontend stores the access token in localStorage via `TokenManager.ts`. Backend validates in `app/core/security.py`; current user injected via `app/deps/user.py`. `/login` and `/register` routes share `AuthPage`.

### Builtin Tools

Pre-built LangChain tools bound to agents as `AgentBuiltinTool` join rows. `factory.build_builtin_tools(tool_types, user_id)` in `app/utils/langchain/builtin_tools/` instantiates by type name. Skips user-scoped tools if `user_id` is `None`; `knowledge_graph_manager` also accepts `llm_config`.

Current catalog: `web_search`, `web_fetch`, `python_exec`, `scheduled_task_manager`, `skill_manager`, `memory_manager`, `prompt_template_manager`, `knowledge_graph_manager`, `help_document_manager`, `workspace`.

**Session Workspace** (`workspace` builtin) — scratch dir at `{WORKSPACE_DIR}/{user_id}/{session_id}/`.

Key non-obvious behaviors:
- **`ws_write`/`ws_edit` auto-register a `ChatFile` row** (`storage_type="workspace"`) — the file appears in `WorkspaceFilesPanel` without the agent calling `ws_present`. `ws_delete` removes the row. `ws_present` is now auxiliary (explicit batch surfacing only).
- **Dangerous extensions** (`.html`, `.svg`, `.exe`, …) are silently skipped by `_register_workspace_file` (file stays on disk, no DB row) and blocked at download time.
- **Download requires JWT** — `WorkspacesService.downloadFile` fetches with `Authorization: Bearer`; cannot use a bare `<a href>`.
- **Docker**: `WORKSPACE_DIR` must be on a named volume. Without it, workspace files are wiped on every `docker compose down && up --build` even though DB rows survive.
- `GET /api/v1/workspace/{session_id}/download-all` zips all session files; runs via `asyncio.to_thread`; capped by `WORKSPACE_ZIP_MAX_MB` (→ HTTP 413 if exceeded).

**Python Exec Tool** (`python_exec`) — isolated subprocess with three security layers:
1. Clean environment — blocks credential leakage via env vars
2. Whitelist `__import__` — only `_ALLOWED_MODULES` importable at top level
3. Sandboxed `open`/`io.open` — restricted to subprocess temp dir

Concurrency capped at 2 via `asyncio.Semaphore(2)` (server is 2c/2G). Timeout 30 s.

### API Tools

`ApiTool` model + `AgentApiTool` join table. `build_tool_from_config()` in `app/utils/langchain/http_tool_factory.py` converts config to a LangChain `BaseTool`. Supports fixed/variable params, query/body placement, response extraction, and `response_max_chars` truncation.

### Image Tools

Dual-purpose: standalone studio + agent-bound chat tools. Adapter layer in `app/utils/image/` — `adapter_factory.get_image_adapter(provider, config)` dispatches to provider implementations.

Key behaviors:
- When `support_img2img=True` and the agent supplies a source image reference, `build_image_tool_from_config()` calls `adapter.img2img()` instead of `generate()`.
- `app/utils/langchain/image_reference_context.py` — per-request `ContextVar` holds `ImageReference` objects (ref_id → object_key) set from the conversation's uploaded/generated images. `resolve_image_ref_id()` normalises numeric IDs ("image 2", "#2", "2") for img2img routing.
- Internal image reads go through `load_image_bytes()` from `local_image_loader.py` — resolves `object_key` directly from disk, falls back to HTTP only for true external URLs.

### Agent Execution Flow

1. `POST /api/v1/chat/{session_id}/stream` receives a `ChatRequest`
2. Loads session → agent config → builds LangGraph agent via `get_langchian_agent()`
3. Fetches ancestor message chain (tree via `parent_id`)
4. Injects file contents into messages
5. Streams via `astream()` with `stream_mode=["messages","updates"]`
6. After streaming, `_inject_image_markdown()` scans tool messages for image URLs and appends markdown to the following AI message if the LLM omitted it
7. Persists all new messages

`agent_util.py` public API: `get_langchian_agent(agent_data)` and `get_langchain_agent_and_tools(agent_data)` (used by approve-tool endpoint). Both delegate to `_build_model_and_tools()` → `create_langchain_agent_with_middleware` which wraps: `ToolCallLimitMiddleware`, `ModelCallLimitMiddleware`, `ToolRetryMiddleware`, `MessageLimitMiddleware`. When `human_in_the_loop=True`, `ToolCallInterruptMiddleware` is prepended.

`ValidChatModel` uses aliases: `provider` → `model_provider`, `model_name` → `model` (maps to `init_chat_model` kwargs). `ValidAgent` filters out `mcps` with `has_mcp=False` via field validator.

**Human-in-the-loop** — `ToolCallInterruptMiddleware` calls LangGraph `interrupt()` before each tool call. Router detects `"__interrupt__"` signal → creates `MessageApproval` row (`status="pending"`) → yields `tool_approval_required` SSE event. On `POST .../approve-tool`: approved → execute tool calls directly + resume stream; rejected → inject synthetic rejection ToolMessages + resume. **Remember to import `MessageApproval` in `init_db()`.**

### Chat Message Tree

Messages stored as a tree via `parent_id`. The chat router assigns `parent_id` dynamically as new messages are produced, enabling branching. Compression (`CompressUtil.compress`) creates a new `ai` message with `name="__compressed__"` and **`parent_id=None`**, starting a new root.

### File Upload Pipeline

`POST /api/v1/upload` → `LocalFileUploader`. Parser selected by extension: plain text/csv/json/yaml → `TextParser`; `.pdf` → `PDFParser`; `.docx` → `DocxParser`.

Key behaviors:
- **Images are inlined as base64 `ImageContentBlock`s** read from `UPLOAD_DIR/{object_key}` — the LLM never fetches from a public URL. Falls back to `{OSS_URL}/{object_key}` only if local file is missing.
- Text files are inlined as `text` items truncated at 5 000 chars.

### Scheduled Tasks

`ScheduledTask` stores next run time as naive UTC datetime. `execute_due_tasks()` immediately advances `next_run_at` before execution to prevent double-firing. Results are emailed if the user has `UserEmailAgent` configured and enabled. Executions recorded as `ScheduledTaskExecution` rows.

### Email Agent / Scheduler

`AsyncIOScheduler` in `app/core/scheduler.py`. Two jobs: email polling (only when `EMAIL_ENABLED=true`) and scheduled task checker (always running).

### Feature Modules

Standard CRUD resources following the new-module checklist. Non-obvious behaviors only:

- **Prompt Templates** — CRUD snippets, filterable by category. Designed for copy-to-chat, not agent runtime use.
- **Skills** — Text content (SKILL.md-style) + optional bundled **text files** (`skill_files` table, cascade-deleted with the skill) for dynamic agent fetch at runtime via `skill_manager` tool. `use_skill` materializes a skill's files into the session workspace `.skills/<name>/` (text-only, caps in `skill_service.validate_skill_files`; not registered as `ChatFile`), then the agent runs them via `python_exec(script=".skills/<name>/x.py")`. Scripts run through the same sandbox as inline code (whitelist `__import__`, preinstalled libs only) — see `docs/sandbox-architecture.md`.
- **User Memory** — Two types: `"core"` (auto-injected into every agent system prompt, **only when `memory_manager` is in the agent's builtin tools**) and `"normal"` (explicit query only). `upsert` on `(user_id, key)`.
- **Knowledge Graph** — `/extract` endpoint returns a preview and **does not auto-save**; caller must explicitly save nodes/edges. Graph names auto-created on first use.
- **Help Documents** — Seed data in `backend/app/seed/help_docs.json` is **not auto-loaded at startup**; must be imported manually.
- **Webhooks** — `POST /webhooks/{slug}` (no auth) verifies HMAC-SHA256 from `x-signature`/`x-hub-signature-256`. Secret only returned on create or regenerate. **HITL interrupts are skipped** in webhook context (interrupt → break immediately).
- **Session Sharing** — `GET /share/{slug}` is **public, no auth**; unauthenticated visitors can read the conversation.
- **Token Usage Stats** — `StatsService` owns its own queries directly on `ChatMessage.usage_metadata` (JSON column via `func.json_extract`); no mapper.

### Frontend Structure

- `src/api/` — frontend API client code originally generated from the OpenAPI schema. Manual edits are acceptable in this repository when keeping the client in sync pragmatically; export any manual additions from `src/api/index.ts`
- `src/context/AppContext.tsx` — global state (agents, sessions, LLMs, MCPs), loaded once on auth
- `src/hooks/useMessageHandler.ts` — core chat hook: message tree, SSE parsing, branching, sibling nav, tool approval, regenerate, compress, stream abort
- `src/utils/TokenManager.ts` — JWT in localStorage, auth guard

### UI Preferences (Frontend-only)

Stored in `localStorage` (`src/utils/UIPreferences.ts`). Same-tab sync via `CustomEvent('ui-pref-change')`; cross-tab via `storage` event.

**Hide intermediate messages** (`hideIntermediate`): collapses consecutive `tool` rows + `ai` rows with non-empty `tool_calls` (excluding `__compressed__`) into `IntermediateGroup`. **The trailing group stays expanded while streaming** (`defaultCollapsed=!(isLoading && isTrailing)`). Chat header has Eye/EyeOff button for per-session override.

### Frontend Styling

Tailwind CSS v4 frosted-glass theme:
- Section cards: `bg-white/15 backdrop-blur-2xl rounded-3xl border border-white/30`
- Inner rows: `bg-white/15 backdrop-blur-sm rounded-2xl border border-white/20 hover:bg-white/25`
- Primary buttons: `bg-gradient-to-r from-cyan-400 to-blue-500`
- **Do not use hardcoded `text-white` for body text** — use `.theme-white-text` / `.theme-black-text` from `index.css` so theme switching works.

### Environment

**All backend commands must be run from the `backend/` directory** — `config.py` calls `load_dotenv(".env")` with a relative path.

Key env vars in `backend/.env`:
- `DATABASE_URL` — `sqlite+aiosqlite:///./fancy_agent.db` (local) or `mysql+asyncmy://...` (prod). Copy `.env.sqlite.example` → `.env` for zero-infra local dev.
- `OSS_URL` — base URL for uploads and generated images
- `SECRET_KEY` — JWT signing key
- `UPLOAD_DIR` / `WORKSPACE_DIR` — storage roots (distinct directories)
- `AGENT_TOOL_CALL_LIMIT` / `AGENT_MODEL_CALL_LIMIT` — per-agent call limits
- `SEARCH_PROVIDER` — `"duckduckgo"` (default) or `"tavily"` (requires `TAVILY_API_KEY`)
- `CORS_ORIGINS` — comma-separated allowed origins
- `EMAIL_ENABLED` + related `EMAIL_*` vars — email polling feature flag
- `WORKSPACE_MAX_FILE_SIZE_MB` / `WORKSPACE_MAX_SESSION_MB` / `WORKSPACE_MAX_USER_GB` / `WORKSPACE_ZIP_MAX_MB` — quota controls

Frontend reads `.env.development` / `.env.production` for `VITE_API_BASE_URL`.
