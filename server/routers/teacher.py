"""
server/routers/teacher.py — Teacher router for PDF upload, pipeline control, and graph curation.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from server.config import settings
from server.core.dependencies import require_teacher
from server.models.course import CourseDocument, PipelineTaskDocument
from server.models.knowledge import (
    EnrichedConceptDocument,
    KnowledgeGraphDocument,
)
from server.models.schemas import (
    ConceptPatchRequest,
    CourseResponse,
    GraphEdge,
    GraphNode,
    GraphVisualizerResponse,
    PipelineStartResponse,
    PipelineStatusResponse,
)
from server.models.user import UserDocument
from server.services.pipeline_service import pipeline_service

router = APIRouter(prefix="/api/v1/teacher", tags=["Teacher"])


@router.post(
    "/upload",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload textbook PDF and initialize a new course",
)
async def upload_textbook(
    title: str = Form(..., description="Title of the course or textbook"),
    description: str | None = Form(None, description="Optional course description"),
    file: UploadFile = File(..., description="PDF textbook document"),
    teacher: UserDocument = Depends(require_teacher),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a PDF document (.pdf).",
        )

    # Ensure storage folder exists
    books_dir = settings.BOOKS_DIR
    books_dir.mkdir(parents=True, exist_ok=True)

    dest_path = books_dir / file.filename
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store PDF file on disk: {e}",
        )

    course = CourseDocument(
        title=title.strip(),
        description=description.strip() if description else None,
        teacher_id=str(teacher.id),
        uploaded_pdf_name=file.filename,
        pdf_storage_path=str(dest_path),
        status="ready",
    )
    await course.insert()

    return CourseResponse(
        id=str(course.id),
        title=course.title,
        description=course.description,
        teacher_id=course.teacher_id,
        uploaded_pdf_name=course.uploaded_pdf_name,
        status=course.status,
        active_task_id=course.active_task_id,
        created_at=course.created_at,
    )


@router.post(
    "/pipeline/start/{course_id}",
    response_model=PipelineStartResponse,
    summary="Trigger the 7-stage AutoHKG pipeline in the background",
)
async def start_pipeline(
    course_id: str,
    background_tasks: BackgroundTasks,
    teacher: UserDocument = Depends(require_teacher),
):
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID format.")

    course = await CourseDocument.get(ObjectId(course_id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    if course.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pipeline is already running for this course.",
        )

    # Initialize task record
    task = PipelineTaskDocument(
        course_id=course_id,
        status="queued",
        current_stage="QUEUED",
        progress_percentage=0,
        logs=[f"Task queued by teacher {teacher.full_name}"],
    )
    await task.insert()

    # Update course status
    course.status = "processing"
    course.active_task_id = str(task.id)
    await course.save()

    # Launch background worker
    background_tasks.add_task(
        pipeline_service.run_full_pipeline,
        course_id_str=course_id,
        task_id_str=str(task.id),
    )

    return PipelineStartResponse(
        task_id=str(task.id),
        course_id=course_id,
        status="queued",
        message="AutoHKG knowledge graph pipeline initiated in the background.",
    )


@router.get(
    "/pipeline/status/{task_id}",
    response_model=PipelineStatusResponse,
    summary="Get execution stage, progress percentage, and logs for a pipeline task",
)
async def get_pipeline_status(
    task_id: str,
    teacher: UserDocument = Depends(require_teacher),
):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format.")

    task = await PipelineTaskDocument.get(ObjectId(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Pipeline task not found.")

    return PipelineStatusResponse(
        task_id=str(task.id),
        course_id=task.course_id,
        status=task.status,
        current_stage=task.current_stage,
        progress_percentage=task.progress_percentage,
        stage_details=task.stage_details,
        logs=task.logs,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.get(
    "/courses",
    response_model=list[CourseResponse],
    summary="List all courses created by the authenticated teacher",
)
async def list_teacher_courses(teacher: UserDocument = Depends(require_teacher)):
    courses = await CourseDocument.find(
        CourseDocument.teacher_id == str(teacher.id)
    ).sort("-created_at").to_list()

    return [
        CourseResponse(
            id=str(c.id),
            title=c.title,
            description=c.description,
            teacher_id=c.teacher_id,
            uploaded_pdf_name=c.uploaded_pdf_name,
            status=c.status,
            active_task_id=c.active_task_id,
            created_at=c.created_at,
        )
        for c in courses
    ]


@router.get(
    "/knowledge-graph/{course_id}",
    response_model=GraphVisualizerResponse,
    summary="Get interactive Vis.js / Cytoscape nodes and edges for the course Knowledge Graph",
)
async def get_teacher_knowledge_graph(
    course_id: str,
    teacher: UserDocument = Depends(require_teacher),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc:
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph has not been generated for this course yet.",
        )

    nodes = [
        GraphNode(
            id=n["id"],
            label=n.get("label", n["id"]),
            type=n.get("type", "fine_grained_concept"),
        )
        for n in kg_doc.nodes
    ]
    edges = [
        GraphEdge(
            source=e["source"],
            target=e["target"],
            relation=e.get("relation", "PREREQUISITE_FOR"),
            confidence=e.get("confidence", 1.0),
            evidence_chunk=e.get("evidence_chunk"),
            evidence_text=e.get("evidence_text"),
        )
        for e in kg_doc.edges
    ]

    return GraphVisualizerResponse(
        course_id=course_id,
        total_nodes=len(nodes),
        total_edges=len(edges),
        nodes=nodes,
        edges=edges,
    )


@router.patch(
    "/knowledge-graph/{course_id}/concept",
    response_model=GraphVisualizerResponse,
    summary="Human-in-the-loop manual override of concept categories or prerequisites",
)
async def patch_concept_relationships(
    course_id: str,
    patch: ConceptPatchRequest,
    teacher: UserDocument = Depends(require_teacher),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc:
        raise HTTPException(status_code=404, detail="Knowledge graph not found.")

    c_name = patch.concept_name

    # 1. Update EnrichedConceptDocument
    enriched = await EnrichedConceptDocument.find_one(
        EnrichedConceptDocument.course_id == course_id,
        EnrichedConceptDocument.concept == c_name,
    )
    if enriched:
        if patch.coarse_grained_category:
            enriched.coarse_grained_category = patch.coarse_grained_category
        if patch.prerequisites:
            enriched.prerequisites = patch.prerequisites
            enriched.prerequisite_edges = [
                {"prerequisite": p, "confidence": 1.0, "evidence_chunk": "manual_override", "evidence_text": "Teacher specified"}
                for p in patch.prerequisites
            ]
        await enriched.save()

    # 2. Update KnowledgeGraph edges: remove old incoming edges to this concept, replace with new
    new_edges = [
        e for e in kg_doc.edges if not (e.get("target") == c_name and e.get("relation") == "PREREQUISITE_FOR")
    ]
    for p in patch.prerequisites:
        new_edges.append({
            "source": p,
            "target": c_name,
            "relation": "PREREQUISITE_FOR",
            "confidence": 1.0,
            "evidence_chunk": "manual_teacher_override",
            "evidence_text": "Manually verified relationship by course instructor.",
        })

    kg_doc.edges = new_edges
    kg_doc.total_edges = len(new_edges)
    kg_doc.updated_at = datetime.now(timezone.utc)
    await kg_doc.save()

    nodes = [
        GraphNode(id=n["id"], label=n.get("label", n["id"]), type=n.get("type", "fine_grained_concept"))
        for n in kg_doc.nodes
    ]
    edges = [
        GraphEdge(
            source=e["source"],
            target=e["target"],
            relation=e.get("relation", "PREREQUISITE_FOR"),
            confidence=e.get("confidence", 1.0),
            evidence_chunk=e.get("evidence_chunk"),
            evidence_text=e.get("evidence_text"),
        )
        for e in kg_doc.edges
    ]

    return GraphVisualizerResponse(
        course_id=course_id,
        total_nodes=len(nodes),
        total_edges=len(edges),
        nodes=nodes,
        edges=edges,
    )
