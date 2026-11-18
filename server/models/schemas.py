"""
server/models/schemas.py — Pydantic Request and Response DTO Schemas.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


# ── Authentication Schemas ──────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str
    role: str = "student"  # 'teacher' | 'student'


class UserLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    full_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    created_at: datetime


# ── Teacher Schemas ─────────────────────────────────────────────────────
class CourseResponse(BaseModel):
    id: str
    title: str = "Untitled Course"
    description: str | None = None
    teacher_id: str = "system_seed"
    uploaded_pdf_name: str = "curriculum.pdf"
    status: str = "ready"
    active_task_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineStartResponse(BaseModel):
    task_id: str
    course_id: str
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    task_id: str
    course_id: str
    status: str
    current_stage: str
    progress_percentage: int
    stage_details: dict[str, Any]
    logs: list[str]
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class ConceptPatchRequest(BaseModel):
    concept_name: str
    coarse_grained_category: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


# ── Student Roster & Course Enrollment Schemas ──────────────────────────
class StudentRosterItem(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime
    is_enrolled: bool = False
    enrolled_at: datetime | None = None


class StudentEnrollRequest(BaseModel):
    student_id: str


class StudentEnrollBatchRequest(BaseModel):
    student_ids: list[str] = Field(default_factory=list)


class EnrollmentActionResponse(BaseModel):
    course_id: str
    student_id: str | None = None
    enrolled_count: int = 1
    is_enrolled: bool = True
    message: str



# ── Student & Adaptive Quiz Schemas ─────────────────────────────────────
class LearningPathItem(BaseModel):
    concept_name: str
    node_type: str = "fine_grained_concept"
    coarse_grained_category: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    mastery_percentage: float = 10.0
    status: str = "Locked"  # 'Mastered' | 'In Progress' | 'Ready to Learn' | 'Locked'


class LearningPathResponse(BaseModel):
    course_id: str
    course_title: str
    total_concepts: int
    path: list[LearningPathItem]


class QuizQuestionResponse(BaseModel):
    question_id: str
    course_id: str
    concept_name: str
    question_text: str
    options: list[str]
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    difficulty: str = "medium"
    # The server hides correct_option and explanation from the quiz prompt payload
    # to prevent client inspection cheating; they are kept server-side or encrypted/hashed.


class QuizSubmitRequest(BaseModel):
    course_id: str
    concept_name: str
    question_id: str
    selected_option: str
    correct_option: str
    question_text: str
    explanation: str
    options: list[str] = Field(default_factory=list)


class QuizSubmitResponse(BaseModel):
    is_correct: bool
    correct_option: str
    explanation: str
    prior_mastery: float
    updated_mastery: float
    next_recommended_concept: str | None = None
    navigation_reason: str | None = None
    transition_type: str | None = None


class ConceptMasteryItem(BaseModel):
    concept_name: str
    mastery_probability: float
    mastery_percentage: float
    attempts_count: int
    correct_count: int
    status: str  # 'Mastered' | 'In Progress' | 'Not Started'


class StudentMasteryResponse(BaseModel):
    course_id: str
    student_id: str
    overall_mastery_percentage: float
    concepts: list[ConceptMasteryItem]


class SourceChunkItem(BaseModel):
    chunk_id: str
    page_number: int | None = None
    text: str


class QuizHistoryItem(BaseModel):
    id: str
    course_id: str
    course_title: str
    concept_name: str
    question_id: str
    question_text: str
    options: list[str] = Field(default_factory=list)
    correct_option: str
    selected_option: str
    is_correct: bool
    explanation: str
    difficulty: str | None = None
    prior_mastery: float
    posterior_mastery: float
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    source_chunks: list[SourceChunkItem] = Field(default_factory=list)
    created_at: datetime


class ConceptHistorySummary(BaseModel):
    course_id: str
    course_title: str
    concept_name: str
    attempts: int
    correct: int
    incorrect: int
    accuracy_percentage: float
    latest_mastery_percentage: float


class QuizHistoryCourseOption(BaseModel):
    course_id: str
    course_title: str
    attempts: int


class QuizHistoryResponse(BaseModel):
    total_attempts: int
    correct_count: int
    incorrect_count: int
    accuracy_percentage: float
    courses: list[QuizHistoryCourseOption] = Field(default_factory=list)
    concept_summary: list[ConceptHistorySummary] = Field(default_factory=list)
    attempts: list[QuizHistoryItem] = Field(default_factory=list)


# ── Graph Schemas ───────────────────────────────────────────────────────
class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    mastery: float | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float
    evidence_chunk: str | None = None
    evidence_text: str | None = None


class GraphVisualizerResponse(BaseModel):
    course_id: str
    total_nodes: int
    total_edges: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ConceptNeighborhoodResponse(BaseModel):
    concept: str
    node_type: str
    parents: list[str]
    prerequisites: list[str]
    dependents: list[str]
    evidence_chunks: list[dict[str, Any]]


# ── AI Tutor & Doubts Schemas ───────────────────────────────────────────
class AiTutorAskRequest(BaseModel):
    course_id: str
    question: str
    concept_name: str | None = None


class AiTutorCitation(BaseModel):
    chunk_id: str
    snippet: str
    concept: str | None = None


class AiTutorResponse(BaseModel):
    question: str
    answer: str
    concept_name: str | None = None
    citations: list[AiTutorCitation] = Field(default_factory=list)

