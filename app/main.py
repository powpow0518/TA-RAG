import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.api import api_router
from app.core.config import settings
from app.models.base import init_db

# Ensure model metadata is registered before init_db() runs.
from app.models.course import Course  # noqa: F401
from app.models.login_log import LoginLog  # noqa: F401
from app.models.question import Question  # noqa: F401
from app.models.quiz import Quiz, QuizSubmission  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models import rag as rag_models  # noqa: F401
from app.services import rag_service


async def scheduled_weekly_update():
    script_candidates = [
        Path("update.py"),
        Path("update_knowledge_base.py"),
    ]
    script_path = next((path for path in script_candidates if path.exists()), None)
    if script_path is None:
        print("Knowledge-base update skipped: no update script found.")
        return

    print(f"Starting scheduled knowledge-base update with {script_path.name}...")
    try:
        process = await asyncio.create_subprocess_shell(
            f"python {script_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            print("Knowledge-base update completed.")
            print(stdout.decode())
        else:
            print(f"Knowledge-base update failed: {stderr.decode()}")
    except Exception as e:
        print(f"Knowledge-base update error: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    init_db()

    try:
        rag_service.initialize_rag_service()
        print("RAG service initialized successfully.")
    except Exception as e:
        print(f"RAG initialization failed: {e}")

    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(day_of_week="sun", hour=19, minute=0)
    scheduler.add_job(scheduled_weekly_update, trigger, id="weekly_kb_update", replace_existing=True)
    scheduler.start()
    print(f"Scheduler started with trigger: {trigger}")

    yield

    scheduler.shutdown(wait=False)
    print("Application shutdown...")


app = FastAPI(
    title=settings.APP_NAME,
    description="""
## Teaching Assistant RAG API

Backend for an AI teaching assistant demo that supports:

- authentication
- course management
- RAG chat
- quiz generation and grading
    """,
    version=settings.API_VERSION,
    lifespan=lifespan,
    openapi_url=f"/api/{settings.API_VERSION}/openapi.json",
    docs_url=f"/api/{settings.API_VERSION}/docs",
    redoc_url=f"/api/{settings.API_VERSION}/redoc",
    openapi_tags=[
        {"name": "authentication", "description": "Auth endpoints"},
        {"name": "users", "description": "User management"},
        {"name": "RAG", "description": "RAG chat endpoints"},
    ],
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Use the access token returned from /auth/login.",
        }
    }

    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if "login" not in path and method != "parameters":
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")


@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Teaching Assistant API",
        "version": settings.API_VERSION,
        "docs": f"/api/{settings.API_VERSION}/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
