# GitHub Push Notes

## Suggested repository name

- `ta-rag-demo`
- `teaching-assistant-rag`
- `ta-rag-portfolio`

## First push

Replace the remote URL with your own repository:

```bash
git remote add origin https://github.com/<your-account>/<your-repo>.git
git push -u origin main
```

If the remote already exists:

```bash
git remote set-url origin https://github.com/<your-account>/<your-repo>.git
git push -u origin main
```

## Suggested GitHub description

Teaching-assistant style RAG demo with FastAPI, Qdrant, Gemini, and quiz generation/grading workflows.

## Suggested topics

- `fastapi`
- `rag`
- `qdrant`
- `llm`
- `education`
- `postgres`
- `docker`
- `react`

## Release draft

Title:

`TA_RAG portfolio release`

Body:

```text
This is a sanitized portfolio version of a teaching-assistant style RAG project.

Included in this release:
- course-based RAG chat flow
- quiz draft generation
- quiz grading flow
- FastAPI backend
- React/Vite demo frontend
- Docker Compose setup for local demo

Notes:
- API keys are not included
- the central prompt and retrieval behavior was preserved from the source workflow
- this repository is intended for demonstration and code review, not as a production deployment template
```

## Good screenshot candidates

1. Swagger docs home
2. RAG chat page
3. quiz generation screen
4. student quiz submission screen
