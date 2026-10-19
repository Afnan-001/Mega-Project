"""
server/models/student.py — Student mastery tracking and quiz attempt ODM documents.
"""
from __future__ import annotations

from datetime import datetime, timezone
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
    prior_mastery: float
    posterior_mastery: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "quiz_attempts"
