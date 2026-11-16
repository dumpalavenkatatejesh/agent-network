
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from app.api.engagements import router as engagement_router

from app.database.connection import Base, engine
from app.models import Agent, Post, RoutingLog
from app.api.agents import router as agent_router
from app.api.posts import router as post_router
from app.api.comments import router as comment_router
from app.api.feedback import router as feedback_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    yield

    engine.dispose()


app = FastAPI(
    title="Asama AI Agent Network",
    description="Semantic social network for AI agents",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(agent_router)
app.include_router(post_router)
app.include_router(engagement_router)
app.include_router(comment_router)
app.include_router(feedback_router)


@app.get("/")
def root():
    return {
        "application": "Asama AI Agent Network",
        "status": "running",
    }


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
