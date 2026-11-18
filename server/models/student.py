"""
server/models/student.py — Student mastery tracking and quiz attempt ODM documents.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from beanie import Document, Indexed
from pydantic import Field


class StudentMasteryDocument(Document):
    """Tracks latent Bayesian Knowledge Tracing (BKT) mastery per student, course, and concept."""

    student_id: Indexed(str)
    course_id: Indexed(str)
    concept_name: Indexed(str)
    mastery_probability: float = 0.10  # P(L_0) default
    attempts_count: int = 0
    correct_count: int = 0
    recent_answers: list[int] = Field(default_factory=list)  # Last 10 binary answers (1=correct, 0=incorrect)
    last_practiced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "student_mastery_states"


class QuizAttemptDocument(Document):
    """Individual quiz question response record with BKT prior and posterior mastery."""

    student_id: Indexed(str)
    course_id: Indexed(str)
    concept_name: str
    question_id: str
    question_text: str
    options: list[str]
    correct_option: str
    selected_option: str
    is_correct: bool
    explanation: str
    difficulty: str | None = None
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    source_chunks: list[dict[str, Any]] = Field(default_factory=list)
    prior_mastery: float
    posterior_mastery: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "quiz_attempts"


class StudentNavigationStateDocument(Document):
    """Per-student, per-course DAG traversal state mirroring CogRAG adaptive_engine."""

    student_id: Indexed(str)
    course_id: Indexed(str)
    current_concept: str | None = None
    return_target: str | None = None
    recent_concepts: list[str] = Field(default_factory=list)
    last_transition_type: str | None = None
    last_transition_reason: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "student_navigation_states"
