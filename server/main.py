"""
server/main.py — Main FastAPI Application Entrypoint.
Initializes lifespan, database connection, CORS middleware, and API routers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.database import close_db, init_db
from server.routers import auth, graph, student, teacher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager handling database connection startup and shutdown."""
    logger.info("Initializing database connection...")
    try:
        await init_db()
        logger.info("Database connection and Beanie ODM successfully initialized.")
    except Exception as e:
        logger.warning(
            "MongoDB connection could not be established at startup: %s. "
            "Ensure MongoDB is running at %s if persistent operations fail.",
            e,
            settings.MONGODB_URL,
        )
    yield
    logger.info("Closing database connection...")
    await close_db()


app = FastAPI(
    title="AutoHKG & Cognitive-RAG Adaptive Learning Server",
    description=(
        "FastAPI REST backend providing role-based access for Teachers (PDF ingestion, "
        "automated 7-stage AutoHKG pipeline, DAG knowledge graph curation) and Students "
        "(prerequisite learning paths, Bayesian Knowledge Tracing, and Cognitive-RAG quizzes)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(graph.router)


@app.get("/", tags=["Health Check"])
async def root():
    return {
        "name": "AutoHKG & Cognitive-RAG Adaptive Learning Server",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/api/health", tags=["Health Check"])
async def health_check():
    return {
        "status": "healthy",
        "database": settings.MONGODB_DB_NAME,
        "llm_provider": settings.dict().get("LLM_PROVIDER", "gemini"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
