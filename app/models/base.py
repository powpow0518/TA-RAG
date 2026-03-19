from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


engine_kwargs = {}
if settings.DATABASE_URL.startswith("postgresql"):
    engine_kwargs["connect_args"] = {"options": "-c timezone=Asia/Taipei"}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    try:
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                print("pgvector extension is ready.")

        Base.metadata.create_all(bind=engine)
        print("Database tables are ready.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise
