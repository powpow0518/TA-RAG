# TA_RAG

`TA_RAG` is a teaching-assistant style RAG project for course-based question answering, quiz generation, and answer grading.

There are two main parts:

- course-based question answering
- quiz generation and grading

This project focuses on the core workflow, the supporting architecture, and the end-to-end behavior of the system.

## What this project does

The backend is built with FastAPI and SQLAlchemy. Retrieval uses Qdrant with dense embeddings and sparse search. On top of that, the app supports a teaching-assistant flow where users can ask course questions, generate quiz drafts, and grade student answers.

The frontend is intentionally small. It exists so the main flows can be demonstrated without extra setup.

## Architecture notes

The central logic lives in `app/services/rag_service.py` and `app/services/quiz_service.py`. The prompt and retrieval flow remain concentrated there so the main application behavior stays easy to follow.

The surrounding structure is split as follows:

- API concerns stay in `app/api`
- database access is pulled into `app/repositories`
- external client setup is pulled into `app/providers`
- orchestration remains in `app/services`

That split keeps responsibilities clearer and makes the repo easier to maintain.

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
- add better integration coverage around the RAG flow
- separate more of the prompt-heavy service logic into smaller units

## Why this repo exists

This repo is meant to demonstrate a teaching-assistant RAG workflow in a form that is easy to run, inspect, and extend:

- keep the main behavior easy to trace
- make the structure understandable
- provide a small UI for demonstrating the core flows
- keep the system practical enough for local experimentation

## Before pushing anywhere public

- make sure `.env` is not committed
- revoke any old API keys that ever existed in previous local copies
- check `downloads/`, `archive/`, and `staging/` before packaging demo data
