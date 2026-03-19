from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    APP_NAME: str = "TA RAG"
    API_VERSION: str = "v1"

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ta_rag"
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    GEMINI_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""

    SECRET_KEY: str = "dev_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 600
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    RAG_INITIAL_K: int = 50
    RAG_FINAL_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.4
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200


settings = Settings()
