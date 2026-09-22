# Codele

Codele is a daily coding-practice platform: one challenge, immediate feedback, and a habit loop built around XP, streaks, and learning.

## Milestone status

Both Phase 0 milestones are scaffolded:

- M0.1: [architecture decisions](docs/architecture.md), core journeys, taxonomy, scoring rules, RBAC, wireframes, ERD, and API conventions.
- M0.2: a pnpm monorepo containing Next.js (`apps/web`), Vite + React (`apps/admin`), and FastAPI (`apps/api`); PostgreSQL and Redis Compose services; shared health integration; formatting and pre-commit configuration.
- M1: PostgreSQL schema/migrations, JWT authentication, and database-resolved RBAC.
- M2: question version authoring, immutable daily scheduling, learner-safe daily challenge delivery, idempotent queued submissions, and server-derived progress reads.

## Local development

Prerequisites: Node 22+, pnpm 9+, Python 3.12+, Docker Desktop, and `pre-commit`.

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis
pnpm install
pnpm dev
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Open the user app at `http://localhost:3000`, the admin app at `http://localhost:5173`, and API docs at `http://localhost:8000/docs`. Both frontends display the API health state.

Run checks with `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, and `cd apps/api; pytest`.

Install local hooks after dependencies are available:

```powershell
pre-commit install
pnpm exec husky
```

1. Backend API
   cd /d D:\adarsh\codele\apps\api
   .venv\Scripts\activate
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   API: http://localhost:8000
   Docs: http://localhost:8000/docs

2. Web user app
   cd /d D:\adarsh\codele
   pnpm --filter @codele/web dev
   Web: http://localhost:3000

3. Admin panel
   cd /d D:\adarsh\codele
   pnpm --filter @codele/admin dev
   Admin: http://localhost:5173
   Also ensure Docker services and execution worker are running:
   cd /d D:\adarsh\codele
   docker compose up -d --build
   docker compose ps
