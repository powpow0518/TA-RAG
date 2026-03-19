# Demo Guide

## 1. Start services

```bash
docker compose up --build
```

## 2. Create accounts

Open Swagger at `http://localhost:8000/api/v1/docs`.

Recommended demo users:

- teacher: `teacher_demo`
- student: `student_demo`

Use `POST /api/v1/auth/register`.

Example teacher payload:

```json
{
  "user_id": "teacher_demo",
  "password": "password123",
  "username": "teacher_demo",
  "role": "teacher"
}
```

## 3. Login

Use `POST /api/v1/auth/login`, then paste the returned bearer token into Swagger's `Authorize` dialog.

## 4. Create a course

Use `POST /api/v1/courses/`.

Example query parameters:

```text
course_id=STAT101
course_name=Statistics Demo
```

## 5. Show the RAG flow

Use `POST /api/v1/rag/ask`.

Example body:

```json
{
  "query": "請解釋常態分配的核心概念",
  "course_id": "STAT101",
  "session_id": "demo-session-001"
}
```

Notes:

- good answers depend on having course content indexed into Qdrant
- if no course documents are loaded yet, the endpoint still shows the protected prompt flow, but the answer quality will be limited

## 6. Show the quiz flow

Teacher flow:

- `GET /api/v1/quiz/documents`
- `POST /api/v1/quiz/generate`
- `POST /api/v1/quiz/create`

Student flow:

- `GET /api/v1/quiz/code/{access_code}`
- `POST /api/v1/quiz/submit`

## 7. Show the frontend

Open `http://localhost:5173`.

A simple demo sequence:

1. register a teacher
2. log in
3. create a course
4. show quiz generation or chat
5. switch to the student flow

## 8. Optional admin bootstrap

If you want an admin account for a local demo:

```bash
docker compose run --rm api python add_admin.py
```
