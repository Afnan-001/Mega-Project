"""
server/models/course.py — Course and Pipeline Task ODM documents.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from beanie import Document, Indexed
from pydantic import Field


class CourseDocument(Document):
    """Course document representing an uploaded textbook and its knowledge base."""

    title: str
    description: str | None = None
    teacher_id: Indexed(str)
    uploaded_pdf_name: str
    pdf_storage_path: str
    status: str = "ready"  # 'ready' | 'processing' | 'error'
    active_task_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "courses"


class PipelineTaskDocument(Document):
    """Background pipeline task tracking execution stages and progress."""

    course_id: Indexed(str)
    status: str = "queued"  # 'queued' | 'running' | 'completed' | 'failed'
    current_stage: str = "QUEUED"  # 'CHUNKING' | 'NLP_CONCEPTS' | 'LLM_CLEANING' | 'EMBEDDING' | 'MAPPING' | 'ENRICHMENT' | 'DAG_RESOLVE' | 'COMPLETED'
    progress_percentage: int = 0
    stage_details: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    error_message: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    class Settings:
        name = "pipeline_tasks"
