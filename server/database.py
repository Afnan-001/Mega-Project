"""
server/database.py — Asynchronous MongoDB connection and Beanie ODM initialization.
"""
from __future__ import annotations

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from server.config import settings

logger = logging.getLogger("server.database")

# Compatibility patch for Beanie with newer Motor / PyMongo driver versions
if not hasattr(AsyncIOMotorClient, "append_metadata"):
    AsyncIOMotorClient.append_metadata = lambda self, *args, **kwargs: None

# Global motor client reference
client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    """Connect to MongoDB and initialize Beanie with all Document models."""
    global client
    logger.info("Connecting to MongoDB at: %s", settings.MONGODB_URL)
    client = AsyncIOMotorClient(settings.MONGODB_URL)

    # Import Document models lazily to avoid circular imports
    from server.models.user import UserDocument
    from server.models.course import CourseDocument, PipelineTaskDocument
    from server.models.knowledge import (
        ContentChunkDocument,
        ConceptDocument,
        ConceptChunkMappingDocument,
        EnrichedConceptDocument,
        KnowledgeGraphDocument,
    )
    from server.models.student import (
        StudentMasteryDocument,
        QuizAttemptDocument,
    )

    document_models = [
        UserDocument,
        CourseDocument,
        PipelineTaskDocument,
        ContentChunkDocument,
        ConceptDocument,
        ConceptChunkMappingDocument,
        EnrichedConceptDocument,
        KnowledgeGraphDocument,
        StudentMasteryDocument,
        QuizAttemptDocument,
    ]

    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=document_models,
    )
    logger.info("Beanie ODM initialized with database: %s", settings.MONGODB_DB_NAME)


async def close_db() -> None:
    """Close MongoDB connection gracefully."""
    global client
    if client is not None:
        client.close()
        logger.info("MongoDB connection closed.")
