"""
server/routers/student.py — Student router for adaptive learning paths, Cognitive-RAG quizzes, and mastery tracking.
"""
from __future__ import annotations

import networkx as nx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from server.core.dependencies import require_student
from server.models.course import CourseDocument
from server.models.knowledge import KnowledgeGraphDocument
from server.models.schemas import (
    ConceptMasteryItem,
    CourseResponse,
    LearningPathItem,
    LearningPathResponse,
    QuizQuestionResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    StudentMasteryResponse,
)
from server.models.student import QuizAttemptDocument, StudentMasteryDocument
from server.models.user import UserDocument
from server.services.bkt_engine import bkt_engine
from server.services.cognitive_rag import cognitive_rag

router = APIRouter(prefix="/api/v1/student", tags=["Student"])


@router.get(
    "/courses",
    response_model=list[CourseResponse],
    summary="List all courses with available knowledge graphs for students to study",
)
async def list_available_courses(student: UserDocument = Depends(require_student)):
    courses = await CourseDocument.find(
        CourseDocument.status == "ready"
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
    "/learning-path/{course_id}",
    response_model=LearningPathResponse,
    summary="Get topological prerequisite learning path with student mastery and unlock statuses",
)
async def get_student_learning_path(
    course_id: str,
    student: UserDocument = Depends(require_student),
):
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID.")

    course = await CourseDocument.get(ObjectId(course_id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc or not kg_doc.nodes:
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph has not yet been processed for this course.",
        )

    # Fetch mastery records
    mastery_docs = await StudentMasteryDocument.find(
        StudentMasteryDocument.student_id == str(student.id),
        StudentMasteryDocument.course_id == course_id,
    ).to_list()
    mastery_map = {m.concept_name: m.mastery_probability for m in mastery_docs}

    # Build NetworkX DAG of fine-grained concepts
    G = nx.DiGraph()
    categories_map: dict[str, list[str]] = {}

    for node in kg_doc.nodes:
        if node.get("type") == "fine_grained_concept":
            G.add_node(node["id"])

    for edge in kg_doc.edges:
        rel = edge.get("relation")
        src = edge.get("source")
        tgt = edge.get("target")

        if rel == "PREREQUISITE_FOR" and src in G and tgt in G:
            G.add_edge(src, tgt)
        elif rel == "CONTAINS":
            if tgt not in categories_map:
                categories_map[tgt] = []
            if src not in categories_map[tgt]:
                categories_map[tgt].append(src)

    # Perform topological sort or in-degree sort
    try:
        ordered_nodes = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        # If any cycle somehow remained, fallback to degree sort
        ordered_nodes = sorted(list(G.nodes()), key=lambda n: G.in_degree(n))

    path_items: list[LearningPathItem] = []
    for node in ordered_nodes:
        p_mastery = mastery_map.get(node, 0.10)
        prereqs = list(G.predecessors(node))

        # Check prerequisite mastery threshold
        prereqs_met = all(mastery_map.get(p, 0.10) >= 0.70 for p in prereqs)

        if p_mastery >= 0.85:
            node_status = "Mastered"
        elif prereqs_met:
            node_status = "In Progress" if p_mastery > 0.10 else "Ready to Learn"
        else:
            node_status = "Locked"

        path_items.append(
            LearningPathItem(
                concept_name=node,
                node_type="fine_grained_concept",
                coarse_grained_category=categories_map.get(node, []),
                prerequisites=prereqs,
                mastery_percentage=round(p_mastery * 100, 1),
                status=node_status,
            )
        )

    return LearningPathResponse(
        course_id=course_id,
        course_title=course.title,
        total_concepts=len(path_items),
        path=path_items,
    )


@router.get(
    "/quiz/next-question/{course_id}",
    response_model=QuizQuestionResponse,
    summary="Dynamically generate next Cognitive-RAG question based on DAG prerequisites and BKT mastery",
)
async def get_next_question(
    course_id: str,
    concept: str | None = None,
    student: UserDocument = Depends(require_student),
):
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID.")

    # If specific concept not requested, choose next optimal concept automatically
    target_concept = concept
    if not target_concept:
        target_concept, _ = await cognitive_rag.get_next_target_concept(
            course_id=course_id,
            student_id=str(student.id),
        )

    # Generate MCQ
    mcq = await cognitive_rag.generate_mcq_for_concept(
        course_id=course_id,
        concept_name=target_concept,
    )

    return QuizQuestionResponse(
        question_id=mcq["question_id"],
        course_id=course_id,
        concept_name=mcq["concept_name"],
        question_text=mcq["question_text"],
        options=mcq["options"],
        evidence_chunk_ids=mcq["evidence_chunk_ids"],
    )


@router.post(
    "/quiz/submit-answer",
    response_model=QuizSubmitResponse,
    summary="Submit quiz answer, update student BKT mastery, and return next learning recommendation",
)
async def submit_quiz_answer(
    submission: QuizSubmitRequest,
    student: UserDocument = Depends(require_student),
):
    selected = submission.selected_option.strip()
    correct = submission.correct_option.strip()
    is_correct = (selected.lower() == correct.lower())

    # Update BKT mastery
    prior, updated = await bkt_engine.update_student_concept_mastery(
        student_id=str(student.id),
        course_id=submission.course_id,
        concept_name=submission.concept_name,
        is_correct=is_correct,
    )

    # Record quiz attempt
    attempt = QuizAttemptDocument(
        student_id=str(student.id),
        course_id=submission.course_id,
        concept_name=submission.concept_name,
        question_id=submission.question_id,
        question_text=submission.question_text,
        options=submission.options,
        correct_option=submission.correct_option,
        selected_option=submission.selected_option,
        is_correct=is_correct,
        explanation=submission.explanation,
        prior_mastery=prior,
        posterior_mastery=updated,
    )
    await attempt.insert()

    # Determine next recommended concept
    next_concept, _ = await cognitive_rag.get_next_target_concept(
        course_id=submission.course_id,
        student_id=str(student.id),
    )

    return QuizSubmitResponse(
        is_correct=is_correct,
        correct_option=submission.correct_option,
        explanation=submission.explanation,
        prior_mastery=round(prior * 100, 1),
        updated_mastery=round(updated * 100, 1),
        next_recommended_concept=next_concept,
    )


@router.get(
    "/mastery/{course_id}",
    response_model=StudentMasteryResponse,
    summary="Get per-concept mastery percentages and heatmap data for student",
)
async def get_student_mastery_overview(
    course_id: str,
    student: UserDocument = Depends(require_student),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc:
        raise HTTPException(status_code=404, detail="Knowledge graph not found.")

    mastery_docs = await StudentMasteryDocument.find(
        StudentMasteryDocument.student_id == str(student.id),
        StudentMasteryDocument.course_id == course_id,
    ).to_list()
    mastery_dict = {m.concept_name: m for m in mastery_docs}

    concept_nodes = [n["id"] for n in kg_doc.nodes if n.get("type") == "fine_grained_concept"]
    if not concept_nodes:
        concept_nodes = [n["id"] for n in kg_doc.nodes]

    items: list[ConceptMasteryItem] = []
    total_pct = 0.0

    for name in concept_nodes:
        m = mastery_dict.get(name)
        if m:
            prob = m.mastery_probability
            attempts = m.attempts_count
            corrects = m.correct_count
        else:
            prob = 0.10
            attempts = 0
            corrects = 0

        pct = round(prob * 100, 1)
        total_pct += pct

        if prob >= 0.85:
            c_status = "Mastered"
        elif attempts > 0:
            c_status = "In Progress"
        else:
            c_status = "Not Started"

        items.append(
            ConceptMasteryItem(
                concept_name=name,
                mastery_probability=round(prob, 4),
                mastery_percentage=pct,
                attempts_count=attempts,
                correct_count=corrects,
                status=c_status,
            )
        )

    overall_pct = round(total_pct / len(concept_nodes), 1) if concept_nodes else 0.0

    return StudentMasteryResponse(
        course_id=course_id,
        student_id=str(student.id),
        overall_mastery_percentage=overall_pct,
        concepts=items,
    )
