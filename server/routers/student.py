"""
server/routers/student.py — Student router for adaptive learning paths, Cognitive-RAG quizzes, and mastery tracking.
"""
from __future__ import annotations

import asyncio
import os
import re
import logging
import networkx as nx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from server.core.dependencies import require_student
from server.models.course import CourseDocument, CourseEnrollmentDocument
from server.models.knowledge import (
    ContentChunkDocument,
    EnrichedConceptDocument,
    KnowledgeGraphDocument,
)
from server.models.schemas import (
    AiTutorAskRequest,
    AiTutorCitation,
    AiTutorResponse,
    ConceptHistorySummary,
    ConceptMasteryItem,
    CourseResponse,
    LearningPathItem,
    LearningPathResponse,
    QuizHistoryCourseOption,
    QuizHistoryItem,
    QuizHistoryResponse,
    QuizQuestionResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    SourceChunkItem,
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
    # Only show courses that have a completed KnowledgeGraphDocument
    kg_docs = await KnowledgeGraphDocument.find().to_list()
    courses_with_graph = {kg.course_id for kg in kg_docs}

    if not courses_with_graph:
        return []

    # Check student enrollment status
    student_id_str = str(student.id)
    student_enrollments = await CourseEnrollmentDocument.find(
        CourseEnrollmentDocument.student_id == student_id_str
    ).to_list()
    total_enrollments_in_system = await CourseEnrollmentDocument.count()

    # If the teacher has used enrollment anywhere in the system, strictly filter by student's enrollments
    if total_enrollments_in_system > 0:
        enrolled_course_ids = {e.course_id for e in student_enrollments}
        valid_ids = [
            ObjectId(cid) for cid in enrolled_course_ids
            if cid in courses_with_graph and ObjectId.is_valid(cid)
        ]
        if not valid_ids:
            return []
        courses = await CourseDocument.find(
            CourseDocument.status == "ready",
            {"_id": {"$in": valid_ids}},
        ).sort("-created_at").to_list()
    else:
        # Fallback when no enrollments exist in the database yet: show all ready courses with graphs
        courses = await CourseDocument.find(
            CourseDocument.status == "ready",
            {"_id": {"$in": [ObjectId(cid) for cid in courses_with_graph if ObjectId.is_valid(cid)]}},
        ).sort("-created_at").to_list()

    return [
        CourseResponse(
            id=str(c.id),
            title=c.title or "Untitled Course",
            description=c.description,
            teacher_id=c.teacher_id or "system_seed",
            uploaded_pdf_name=c.uploaded_pdf_name or "curriculum.pdf",
            status=c.status or "ready",
            active_task_id=c.active_task_id,
            created_at=c.created_at or datetime.now(timezone.utc),
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

    # If specific concept not requested, choose next optimal concept automatically via DAG navigation
    target_concept = concept
    if target_concept:
        await cognitive_rag.set_current_concept(
            course_id=course_id,
            student_id=str(student.id),
            concept_name=target_concept,
        )
    else:
        target_concept, _ = await cognitive_rag.get_next_target_concept(
            course_id=course_id,
            student_id=str(student.id),
        )

    # Generate MCQ
    mcq = await cognitive_rag.generate_mcq_for_concept(
        course_id=course_id,
        concept_name=target_concept,
        student_id=str(student.id),
    )

    return QuizQuestionResponse(
        question_id=mcq["question_id"],
        course_id=course_id,
        concept_name=mcq["concept_name"],
        question_text=mcq["question_text"],
        options=mcq["options"],
        evidence_chunk_ids=mcq["evidence_chunk_ids"],
        difficulty=mcq.get("difficulty", "medium"),
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

    # BE-8: Input length validation
    if not selected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="selected_option must not be empty.",
        )

    # Server-side verification using cached question if available
    cached_q = cognitive_rag.get_cached_question(submission.question_id)
    if cached_q:
        true_correct = cached_q["correct_option"].strip()
        explanation = cached_q.get("explanation", submission.explanation)
        difficulty = cached_q.get("difficulty")
        evidence_chunk_ids = list(cached_q.get("evidence_chunk_ids") or [])
        source_chunks = list(cached_q.get("source_chunks") or [])
    else:
        true_correct = submission.correct_option.strip() if submission.correct_option else selected
        explanation = submission.explanation or "Answer evaluated by Cognitive-RAG."
        difficulty = None
        source_chunks = await cognitive_rag.get_grounded_chunks_for_concept(
            course_id=submission.course_id,
            concept_name=submission.concept_name,
            max_chunks=3,
        )
        evidence_chunk_ids = [c["chunk_id"] for c in source_chunks]

    is_correct = (selected.lower() == true_correct.lower())

    # Update BKT mastery
    prior, updated = await bkt_engine.update_student_concept_mastery(
        student_id=str(student.id),
        course_id=submission.course_id,
        concept_name=submission.concept_name,
        is_correct=is_correct,
    )

    # Record quiz attempt including grounded source chunks for student review
    attempt = QuizAttemptDocument(
        student_id=str(student.id),
        course_id=submission.course_id,
        concept_name=submission.concept_name,
        question_id=submission.question_id,
        question_text=submission.question_text,
        options=submission.options,
        correct_option=true_correct,
        selected_option=submission.selected_option,
        is_correct=is_correct,
        explanation=explanation,
        difficulty=difficulty,
        evidence_chunk_ids=evidence_chunk_ids,
        source_chunks=source_chunks,
        prior_mastery=prior,
        posterior_mastery=updated,
    )
    await attempt.insert()

    # Determine next recommended concept via Graph-Aware Adaptive Traversal
    nav_result = await cognitive_rag.select_next_concept_with_navigation(
        course_id=submission.course_id,
        student_id=str(student.id),
        last_concept_answered=submission.concept_name,
        last_is_correct=is_correct,
    )

    return QuizSubmitResponse(
        is_correct=is_correct,
        correct_option=true_correct,
        explanation=explanation,
        prior_mastery=round(prior * 100, 1),
        updated_mastery=round(updated * 100, 1),
        next_recommended_concept=nav_result["concept_name"],
        navigation_reason=nav_result["navigation_reason"],
        transition_type=nav_result["transition_type"],
    )


@router.get(
    "/quiz/history",
    response_model=QuizHistoryResponse,
    summary="List student's past answered questions with results, BKT shifts, and grounded textbook context chunks",
)
async def get_student_quiz_history(
    course_id: str | None = None,
    concept: str | None = None,
    result: str | None = None,
    student: UserDocument = Depends(require_student),
):
    student_id_str = str(student.id)

    # Fetch all student attempts sorted newest first
    all_attempts = await QuizAttemptDocument.find(
        QuizAttemptDocument.student_id == student_id_str,
    ).sort("-created_at").to_list()

    # Resolve course titles for every course referenced in attempts
    course_ids = list({a.course_id for a in all_attempts if a.course_id})
    valid_oids = [ObjectId(cid) for cid in course_ids if ObjectId.is_valid(cid)]
    course_docs = (
        await CourseDocument.find({"_id": {"$in": valid_oids}}).to_list()
        if valid_oids
        else []
    )
    course_title_map = {str(c.id): (c.title or "Course") for c in course_docs}

    # Build course dropdown options across all student attempts
    course_counts: dict[str, int] = {}
    for a in all_attempts:
        course_counts[a.course_id] = course_counts.get(a.course_id, 0) + 1
    course_options = [
        QuizHistoryCourseOption(
            course_id=cid,
            course_title=course_title_map.get(cid, f"Course {cid[-6:].upper()}"),
            attempts=cnt,
        )
        for cid, cnt in sorted(course_counts.items(), key=lambda x: -x[1])
    ]

    # Apply optional filters
    filtered = all_attempts
    if course_id and course_id != "all":
        filtered = [a for a in filtered if a.course_id == course_id]
    if concept and concept != "all":
        filtered = [a for a in filtered if a.concept_name.lower() == concept.lower()]
    if result == "correct":
        filtered = [a for a in filtered if a.is_correct]
    elif result == "incorrect":
        filtered = [a for a in filtered if not a.is_correct]

    # Load latest mastery states for accurate concept summary
    mastery_docs = await StudentMasteryDocument.find(
        StudentMasteryDocument.student_id == student_id_str,
    ).to_list()
    mastery_lookup = {
        (m.course_id, m.concept_name): round(m.mastery_probability * 100, 1)
        for m in mastery_docs
    }

    # Build concept-wise summary from filtered attempts
    concept_buckets: dict[tuple[str, str], dict] = {}
    for a in filtered:
        key = (a.course_id, a.concept_name)
        if key not in concept_buckets:
            concept_buckets[key] = {
                "course_id": a.course_id,
                "course_title": course_title_map.get(a.course_id, f"Course {a.course_id[-6:].upper()}"),
                "concept_name": a.concept_name,
                "attempts": 0,
                "correct": 0,
                "incorrect": 0,
                "latest_mastery": mastery_lookup.get(key, round(a.posterior_mastery * 100, 1)),
            }
        b = concept_buckets[key]
        b["attempts"] += 1
        if a.is_correct:
            b["correct"] += 1
        else:
            b["incorrect"] += 1

    concept_summary = [
        ConceptHistorySummary(
            course_id=b["course_id"],
            course_title=b["course_title"],
            concept_name=b["concept_name"],
            attempts=b["attempts"],
            correct=b["correct"],
            incorrect=b["incorrect"],
            accuracy_percentage=round((b["correct"] / b["attempts"]) * 100, 1) if b["attempts"] else 0.0,
            latest_mastery_percentage=b["latest_mastery"],
        )
        for b in sorted(concept_buckets.values(), key=lambda x: (-x["attempts"], x["concept_name"]))
    ]

    # Resolve grounded textbook chunks (cached per (course_id, concept) for legacy attempts lacking saved source_chunks)
    fallback_chunk_cache: dict[tuple[str, str], list[dict]] = {}
    history_items: list[QuizHistoryItem] = []

    for a in filtered:
        raw_chunks = list(a.source_chunks or [])
        if not raw_chunks:
            cache_key = (a.course_id, a.concept_name)
            if cache_key not in fallback_chunk_cache:
                fallback_chunk_cache[cache_key] = await cognitive_rag.get_grounded_chunks_for_concept(
                    course_id=a.course_id,
                    concept_name=a.concept_name,
                    max_chunks=3,
                )
            raw_chunks = fallback_chunk_cache[cache_key]

        chunk_items = [
            SourceChunkItem(
                chunk_id=str(c.get("chunk_id", "chunk")),
                page_number=c.get("page_number"),
                text=str(c.get("text", "")),
            )
            for c in raw_chunks
            if c.get("text")
        ]
        chunk_ids = list(a.evidence_chunk_ids or [c.chunk_id for c in chunk_items])

        history_items.append(
            QuizHistoryItem(
                id=str(a.id),
                course_id=a.course_id,
                course_title=course_title_map.get(a.course_id, f"Course {a.course_id[-6:].upper()}"),
                concept_name=a.concept_name,
                question_id=a.question_id,
                question_text=a.question_text,
                options=a.options or [],
                correct_option=a.correct_option,
                selected_option=a.selected_option,
                is_correct=a.is_correct,
                explanation=a.explanation,
                difficulty=a.difficulty,
                prior_mastery=round(a.prior_mastery * 100, 1),
                posterior_mastery=round(a.posterior_mastery * 100, 1),
                evidence_chunk_ids=chunk_ids,
                source_chunks=chunk_items,
                created_at=a.created_at,
            )
        )

    total = len(history_items)
    correct_cnt = sum(1 for item in history_items if item.is_correct)
    incorrect_cnt = total - correct_cnt
    acc = round((correct_cnt / total) * 100, 1) if total > 0 else 0.0

    return QuizHistoryResponse(
        total_attempts=total,
        correct_count=correct_cnt,
        incorrect_count=incorrect_cnt,
        accuracy_percentage=acc,
        courses=course_options,
        concept_summary=concept_summary,
        attempts=history_items,
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


@router.post(
    "/ai-tutor/ask",
    response_model=AiTutorResponse,
    summary="Ask AI Tutor a question/doubt about course concepts with textbook grounding",
)
async def ask_ai_tutor(
    request: AiTutorAskRequest,
    student: UserDocument = Depends(require_student),
):
    course_id = request.course_id
    question = request.question.strip()
    concept = request.concept_name

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Find concept info if concept specified or deduce from question
    enriched = None
    if concept:
        enriched = await EnrichedConceptDocument.find_one(
            EnrichedConceptDocument.course_id == course_id,
            EnrichedConceptDocument.concept == concept,
        )

    # Search for evidence chunks related to concept or question
    citations: list[AiTutorCitation] = []
    chunk_texts: list[str] = []

    query_term = concept if concept else (question.split()[-1] if question.split() else "compiler")
    matching_chunks = await ContentChunkDocument.find(
        ContentChunkDocument.course_id == course_id,
        {"text": {"$regex": re.escape(query_term), "$options": "i"}},
    ).limit(3).to_list()

    for mc in matching_chunks:
        snippet = mc.text[:280].strip() + "..."
        citations.append(AiTutorCitation(chunk_id=mc.chunk_id, snippet=snippet, concept=concept))
        chunk_texts.append(f"[{mc.chunk_id}]: {mc.text[:600]}")

    # Fallback to local files if DB chunks are empty
    if not citations:
        from server.config import settings
        import json
        c_file = settings.COURSE_OUTPUTS_DIR / course_id / "content_chunks.json"
        if not c_file.exists():
            c_file = settings.MAIN_DIR / "outputs" / "data" / "content_chunks.json"
        map_file = settings.COURSE_OUTPUTS_DIR / course_id / "concept_chunk_map.json"
        if not map_file.exists():
            map_file = settings.MAIN_DIR / "outputs" / "data" / "concept_chunk_map.json"

        if c_file.exists():
            try:
                with open(c_file, "r", encoding="utf-8") as f:
                    all_c = json.load(f)
                chunk_by_id = {c.get("chunk_id"): c for c in all_c}

                matched = []
                if map_file.exists() and concept:
                    with open(map_file, "r", encoding="utf-8") as f:
                        cc_map = json.load(f)
                    mapped_ids = cc_map.get(concept, [])
                    matched = [chunk_by_id[cid] for cid in mapped_ids if cid in chunk_by_id][:3]

                if not matched:
                    words = [w.lower() for w in (concept or query_term).split() if len(w) > 3]
                    matched = [
                        c for c in all_c
                        if any(w in c.get("text", "").lower() for w in words)
                    ][:3]

                for m in matched:
                    cid = m.get("chunk_id", "chunk")
                    snip = m.get("text", "")[:260].strip() + "..."
                    citations.append(AiTutorCitation(chunk_id=cid, snippet=snip, concept=concept))
                    chunk_texts.append(f"[{cid}]: {m.get('text', '')[:600]}")
            except Exception:
                pass

    cat_name = enriched.coarse_grained_category[0] if (enriched and enriched.coarse_grained_category) else "Compiler Architecture"
    prereqs = enriched.prerequisites if enriched else []

    # Attempt LLM if API key or Ollama provider is available
    answer = None
    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    llm_available = (llm_provider == "ollama") or bool(
        os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEYS", "").strip()
    )
    if llm_available:
        try:
            tutor_llm = cognitive_rag.get_tutor_llm_client()
            context_str = "\n\n".join(chunk_texts) if chunk_texts else f"Curriculum topic: {concept or 'Compiler Design'}."
            tutor_prompt = (
                f"Student Question: {question}\n\n"
                f"Target Concept: {concept or 'General'}\n"
                f"Category: {cat_name}\n"
                f"Prerequisites: {', '.join(prereqs) if prereqs else 'None'}\n\n"
                f"Source Textbook Chunks:\n{context_str}\n\n"
                f"Provide a clear, educational, step-by-step explanation answering the student's doubt directly, citing evidence where appropriate."
            )
            answer = (await asyncio.to_thread(tutor_llm.get_response, tutor_prompt)).strip()
        except Exception as e:
            logging.getLogger("server.student").info("LLM AI Tutor fallback used (%s)", e)

    if not answer:
        # Synthesize clear, comprehensive academic answer
        c_mention = f"'{concept}'" if concept else "this concept"
        prereq_mention = f" Its immediate foundational prerequisites include: {', '.join(prereqs)}." if prereqs else " It operates as an entry-level building block in the syllabus."
        chunk_evidence_mention = f" Based on the textbook excerpt: \"{citations[0].snippet}\"" if citations else ""

        answer = (
            f"### Understanding {concept or 'the Concept'}\n\n"
            f"In the study of **{cat_name}**, {c_mention} is a critical topic in the curriculum.{prereq_mention}\n\n"
            f"**Key Conceptual Explanation:**\n"
            f"When resolving this question regarding {c_mention}, it is essential to understand how it functions within the compilation pipeline. "
            f"It ensures structural integrity and enables subsequent optimization and code generation passes to execute reliably.\n\n"
            f"**Textbook Evidence & Grounding:**\n"
            f"{chunk_evidence_mention}\n\n"
            f"**Next Recommended Step:**\n"
            f"Try attempting the adaptive practice quiz on this concept to reinforce your latent mastery ($P(L)$) in Bayesian Knowledge Tracing!"
        )

    return AiTutorResponse(
        question=question,
        answer=answer,
        concept_name=concept,
        citations=citations,
    )

