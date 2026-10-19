"""
server/models/schemas.py — Pydantic Request and Response DTO Schemas.
"""
from __future__ import annotations

from datetime import datetime
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
    title: str
    description: str | None = None
    teacher_id: str
    uploaded_pdf_name: str
    status: str
    active_task_id: str | None = None
    created_at: datetime


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
