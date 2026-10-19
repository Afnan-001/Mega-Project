"""
server/models/knowledge.py — Knowledge base ODM documents (Chunks, Concepts, Mappings, Graphs).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from beanie import Document, Indexed
from pydantic import Field


class ContentChunkDocument(Document):
    """Text chunk extracted from course textbook with optional embedding."""

    course_id: Indexed(str)
    chunk_id: Indexed(str)
    page_number: int
    book_name: str
    text: str
    embedding_vector: list[float] | None = None

    class Settings:
        name = "content_chunks"


class ConceptDocument(Document):
    """Extracted concept candidate or cleaned canonical concept term."""

    course_id: Indexed(str)
    concept_name: Indexed(str)
    canonical_name: str | None = None
    node_type: str = "fine_grained_concept"  # 'fine_grained_concept' | 'coarse_grained_category'
    is_grounded: bool = False
    max_chunk_similarity: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "concepts"


class ConceptChunkMappingDocument(Document):
    """Adaptive knee/elbow mapping between a concept and its qualifying source chunks."""

    course_id: Indexed(str)
    concept_name: Indexed(str)
    qualifying_chunks: list[dict[str, Any]] = Field(default_factory=list)  # [{"chunk_id": "...", "similarity": 0.85}]
    elbow_threshold: float = 0.0

    class Settings:
        name = "concept_chunk_mappings"


class EnrichedConceptDocument(Document):
    """Enriched concept with verified category and prerequisite edges grounded in citations."""

    course_id: Indexed(str)
    concept: Indexed(str)
    node_type: str = "fine_grained_concept"
    coarse_grained_category: list[str] = Field(default_factory=list)
    parent_concept: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    category_edge: dict[str, Any] | None = None
    prerequisite_edges: list[dict[str, Any]] = Field(default_factory=list)

    class Settings:
        name = "enriched_concepts"


class KnowledgeGraphDocument(Document):
    """Validated Directed Acyclic Graph (DAG) for a course in JSON and GML formats."""

    course_id: Indexed(str, unique=True)
    nodes: list[dict[str, Any]] = Field(default_factory=list)  # [{"id": str, "label": str, "type": str}]
    edges: list[dict[str, Any]] = Field(default_factory=list)  # [{"source": str, "target": str, "relation": str, "confidence": float, "evidence_chunk": str, "evidence_text": str}]
    gml_content: str = ""
    total_nodes: int = 0
    total_edges: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "knowledge_graphs"
