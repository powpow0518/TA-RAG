# TA_RAG

`TA_RAG` is a teaching-assistant style RAG project that I adapted from a real internal codebase into a version I can show publicly.

There are two main parts:

- course-based question answering
- quiz generation and grading

I did not try to turn this into a fake "perfect" production project. The goal here is to show the core workflow, the architecture I cleaned up around it, and how the system behaves end to end.

## What this project does

The backend is built with FastAPI and SQLAlchemy. Retrieval uses Qdrant with dense embeddings and sparse search. On top of that, the app supports a teaching-assistant flow where users can ask course questions, generate quiz drafts, and grade student answers.

The frontend is intentionally small. It exists so the main flows can be demonstrated without extra setup.

## What I kept intact

The central logic in `app/services/rag_service.py` and `app/services/quiz_service.py` comes from the source project. In this public version, I treated the prompt and retrieval flow as protected logic and avoided rewriting it into a different design just for the sake of presentation.

What I did change was everything around it:

- API concerns stay in `app/api`
- database access is pulled into `app/repositories`
- external client setup is pulled into `app/providers`
- orchestration remains in `app/services`

That split makes the repo easier to explain and much easier to maintain than the original copied snapshot.

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL + pgvector
- Qdrant
- Gemini
- Voyage
- React + Vite
- Docker Compose

## Project layout

```text
app/
  api/          routes and auth dependencies
  core/         settings
  models/       SQLAlchemy models
  providers/    Gemini / Qdrant / embedding client setup
  repositories/ DB access layer
  schemas/      request / response models
  services/     RAG and quiz orchestration
frontend/       demo UI
tests/          smoke tests
docs/           demo and release notes
```

## Run locally

1. Copy `.env.example` to `.env`
2. Fill in `GEMINI_API_KEY` and `VOYAGE_API_KEY`
3. Start the stack

```bash
docker compose up --build
```

After startup:

- API docs: `http://localhost:8000/api/v1/docs`
- frontend: `http://localhost:5173`
- health check: `http://localhost:8000/health`

## Run tests

```bash
docker compose run --rm api pytest -q
```

## Demo notes

If you want a quick walkthrough for showing the project, start with [docs/demo-guide.md](./docs/demo-guide.md).

If you want ready-to-use GitHub push commands and a release draft, use [docs/github-release.md](./docs/github-release.md).

## Things I would improve next

- migrate the Gemini integration away from the deprecated SDK
- add better integration coverage around the protected RAG flow
- separate more of the prompt-heavy service logic if the source constraints are relaxed

## Why this repo exists

This repo is meant to show how I handle a real system when I need to make it presentable:

- keep the important behavior intact
- remove secrets and internal-only details
- make the structure understandable
- leave the project honest enough that it still feels real

## Before pushing anywhere public

- make sure `.env` is not committed
- revoke any old API keys that ever existed in previous local copies
- check `downloads/`, `archive/`, and `staging/` before packaging demo data
