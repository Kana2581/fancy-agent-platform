# Repository Guidelines

## Project Structure & Module Organization
- `backend/` contains the FastAPI service (`app/`) with a layered flow: `api/` -> `services/` -> `mappers/` -> `models/`; schemas are in `schemas/`, config in `core/`, and DI helpers in `deps/`.
- `frontend/` is a React 19 + TypeScript app. Main UI code is in `src/pages`, reusable UI in `src/components`, shared state in `src/context`, and generated API client code in `src/api`.
- `docs/` stores architecture notes and incident write-ups; check it before reworking behavior.
- Infra files are at repo root: `docker-compose.yml`, `deploy.sh`, and `nginx/nginx.conf`.

## Build, Test, and Development Commands
- Backend setup/run:
  - `cd backend && uv sync` — install Python dependencies.
  - `cd backend && uv run uvicorn app.main:app --reload` — run backend locally with reload.
- Frontend setup/run:
  - `cd frontend && npm install`
  - `cd frontend && npm run dev` — start Vite dev server.
  - `cd frontend && npm run build` — TypeScript compile + bundle.
  - `cd frontend && npm run lint` — run ESLint.
- Full stack (Docker):  
  `cd backend && uv export --no-hashes --format requirements-txt -o requirements.txt` then `docker compose up --build`.
- Regenerate frontend API client after schema updates:  
  `cd frontend && npx openapi-typescript-codegen --input ./openapi.json --output src/api --client axios`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, `snake_case` modules/functions, explicit service/mapper naming (e.g., `agent_service.py`, `agent_mapper.py`).
- TypeScript/React: follow existing style (2-space indentation, single quotes, semicolons). Use `PascalCase` for components/pages and `camelCase` for hooks/utils.
- Keep generated files under `frontend/src/api/` generated, not hand-edited unless regeneration is impossible.

## Testing Guidelines
- There is no end-to-end test suite yet; backend validation is script-based (`backend/test.py`, `backend/test_stream.py`, etc.).
- For new tests, prefer `pytest` files named `test_<feature>.py` under `backend/`, and keep tests deterministic (no hard-coded external keys/endpoints).
- Before opening a PR, run `npm run lint`, `npm run build`, and smoke-test key backend endpoints.

## Commit & Pull Request Guidelines
- Match existing commit prefixes from history: `feature:`, `fix:`, `docs:`, `refactor:` (short, scoped message after prefix).
- Keep each commit focused on one logical change; avoid mixed backend/frontend refactors unless tightly coupled.
- PRs should include: purpose, impacted directories (e.g., `backend/app/services`, `frontend/src/pages`), manual verification steps, and UI screenshots.

## Security & Configuration Tips
- Never commit secrets or `.env` files. Use `backend/.env` (local/dev) and environment-specific files such as `.env.prd` on servers.
- Run backend commands from `backend/` so environment loading behaves correctly.
