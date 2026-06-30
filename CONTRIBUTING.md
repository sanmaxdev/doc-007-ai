# Contributing to DOC-007-AI

Thanks for taking a look. This guide covers local setup, the project layout, and the checks that run in CI so you can match them before opening a pull request.

## Prerequisites

- Docker and Docker Compose (the simplest way to run everything)
- For working on a single service directly: Python 3.12+ and Node.js 20+

## Running the stack

```bash
cp .env.example .env
# add OPENROUTER_API_KEY and OPENAI_API_KEY for real answers (the app
# also runs with built-in mock providers if you leave them blank)

docker compose up --build
docker compose exec api alembic upgrade head   # first run only
```

- App: http://localhost:3000
- API and interactive docs: http://localhost:8000/docs

## Project layout

```
apps/
  api/                FastAPI backend
    src/doc007/
      api/v1/routers/  thin HTTP routers (no business logic)
      services/        business logic, called by routers
      rag/             extraction, chunking, embeddings, vector store, retrieval, prompt, answer
      providers/       swappable LLM and embedding providers (+ deterministic mocks)
      db/              SQLAlchemy models and session
      core/            config, security, exceptions, deps, logging, rate limiting
      workers/         Celery app and tasks
    tests/             pytest suite (runs on SQLite with fakes)
    alembic/           database migrations
  web/                 Next.js App Router frontend
    src/app/           routes (landing, auth, and the (app) group)
    src/components/     UI and feature components
    src/hooks/          TanStack Query hooks
    src/lib/            typed API client and types
```

The backend keeps a strict boundary: routers call services, services call `rag/` and `providers/`. No business logic or model calls belong in routers.

## Architecture in brief

A user (Next.js, JWT) or an external client (API key) hits FastAPI. Uploads are stored and queued to a Celery worker, which extracts, chunks, embeds (OpenAI), and writes vectors to Qdrant and rows to PostgreSQL. A question is embedded, retrieved with a hybrid of dense vectors and lexical keywords fused by Reciprocal Rank Fusion (always filtered by `workspace_id`), wrapped in a grounded prompt with the chunks marked as untrusted data, and streamed back from the LLM with `[n]` citations mapped to their sources. Redis backs the job queue and the public-API rate limiter.

## Checks (match CI before a PR)

Backend:

```bash
cd apps/api
ruff check .
mypy src
pytest
```

Frontend:

```bash
cd apps/web
npm run lint
npm run typecheck
npm run build
```

CI runs exactly these on every push and pull request.

## Database migrations

After changing a model, generate and apply a migration:

```bash
cd apps/api
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Models use portable column types so the test suite can run on SQLite while production runs on PostgreSQL. Keep it that way.

## Commit and PR conventions

- Short, imperative subject lines ("Add usage quotas", not "Added quotas").
- Explain the why in the body when it is not obvious. Plain prose over long bullet lists.
- Keep a PR focused on one change. Make sure the checks above pass.

## Reporting security issues

Please do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
