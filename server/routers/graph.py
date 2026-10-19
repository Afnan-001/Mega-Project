"""
server/routers/graph.py — Graph export and concept ego-network neighborhood query endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from server.core.dependencies import get_current_user
from server.models.knowledge import (
    ConceptChunkMappingDocument,
    ContentChunkDocument,
    KnowledgeGraphDocument,
)
from server.models.schemas import ConceptNeighborhoodResponse
from server.models.user import UserDocument

router = APIRouter(prefix="/api/v1/graph", tags=["Knowledge Graph"])


@router.get(
    "/{course_id}/gml",
    summary="Download or view raw GML (Graph Modeling Language) graph representation",
)
async def get_raw_gml(
    course_id: str,
    user: UserDocument = Depends(get_current_user),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc or not kg_doc.gml_content:
        raise HTTPException(
            status_code=404,
            detail="GML graph content not found for this course.",
        )

    return Response(
        content=kg_doc.gml_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="knowledge_graph_{course_id}.gml"'},
    )


@router.get(
    "/{course_id}/concept-neighborhood/{concept_name}",
    response_model=ConceptNeighborhoodResponse,
    summary="Get ego-network neighborhood (parents, prerequisites, dependents, evidence chunks) for a concept",
)
async def get_concept_neighborhood(
    course_id: str,
    concept_name: str,
    user: UserDocument = Depends(get_current_user),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc:
        raise HTTPException(status_code=404, detail="Knowledge graph not found.")

    node_type = "fine_grained_concept"
    for n in kg_doc.nodes:
        if n.get("id") == concept_name:
            node_type = n.get("type", "fine_grained_concept")
            break

    parents = []
    prerequisites = []
    dependents = []

    for edge in kg_doc.edges:
        src = edge.get("source")
        tgt = edge.get("target")
        rel = edge.get("relation")

        if rel == "CONTAINS" and tgt == concept_name:
            parents.append(src)
        elif rel == "PREREQUISITE_FOR":
            if tgt == concept_name:
                prerequisites.append(src)
            elif src == concept_name:
                dependents.append(tgt)

    # Fetch evidence chunks
    evidence_chunks = []
    mapping_doc = await ConceptChunkMappingDocument.find_one(
        ConceptChunkMappingDocument.course_id == course_id,
        ConceptChunkMappingDocument.concept_name == concept_name,
    )

    if mapping_doc and mapping_doc.qualifying_chunks:
        chunk_ids = [q["chunk_id"] for q in mapping_doc.qualifying_chunks[:5]]
        chunks = await ContentChunkDocument.find(
            ContentChunkDocument.course_id == course_id,
            {"chunk_id": {"$in": chunk_ids}},
        ).to_list()
        chunk_map = {c.chunk_id: c.text for c in chunks}

        for q in mapping_doc.qualifying_chunks[:5]:
            cid = q["chunk_id"]
            evidence_chunks.append({
                "chunk_id": cid,
                "similarity": q.get("similarity", 0.6),
                "text": chunk_map.get(cid, "")[:500],
            })

    return ConceptNeighborhoodResponse(
        concept=concept_name,
        node_type=node_type,
        parents=parents,
        prerequisites=prerequisites,
        dependents=dependents,
        evidence_chunks=evidence_chunks,
    )
