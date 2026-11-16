
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Asama AI Agent Network"

    # Database configuration
    DATABASE_URL: str

    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Local LLM configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # Embedding model
    EMBEDDING_MODEL: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Cross-encoder reranker
    RERANKER_MODEL: str = (
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # Relevance routing configuration
    ROUTING_THRESHOLD: float = 0.75
    MAX_ROUTED_AGENTS: int = 5

    # Webhook security
    WEBHOOK_SIGNING_SECRET: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


# Load application settings
settings = Settings()


# PostgreSQL engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


# Database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# SQLAlchemy declarative base
class Base(DeclarativeBase):
    pass


# Database dependency for FastAPI
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
