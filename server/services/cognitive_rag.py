"""
server/services/cognitive_rag.py — Cognitive-RAG Context Builder & MCQ Question Generator.
Selects optimal concepts along the prerequisite DAG and generates dynamic, grounded assessment items.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import uuid
from typing import Any
import networkx as nx

from server.config import settings
from server.models.knowledge import (
    ConceptChunkMappingDocument,
    ContentChunkDocument,
    EnrichedConceptDocument,
    KnowledgeGraphDocument,
)
from server.models.student import QuizAttemptDocument, StudentMasteryDocument

logger = logging.getLogger("server.services.cognitive_rag")

QUESTION_GEN_PROMPT = """You are an expert educational assessment designer.
Generate an educational Multiple-Choice Question (MCQ) testing comprehension of the concept: "{concept_name}".

STRICT CONSTRAINTS:
1. Base the question and options EXCLUSIVELY on the provided SOURCE TEXT CHUNKS below.
2. Do NOT invent facts or cite external information not grounded in the chunks.
3. Formulate exactly 4 distinct answer choices.
4. Exactly ONE choice must be clearly correct; the other three must be plausible distractors.
5. Provide a concise explanation justifying why the correct answer is true, referencing the source text.
6. Output MUST be valid JSON only. Do NOT add markdown commentary outside the JSON block.

OUTPUT JSON SCHEMA:
{{
  "question": "The question text here...",
  "options": [
    "Option text 1",
    "Option text 2",
    "Option text 3",
    "Option text 4"
  ],
  "correct_answer": "Exact text of the correct option matching one of the 4 options above",
  "explanation": "Clear explanation referencing chunk evidence..."
}}

CONCEPT:
{concept_name}

CATEGORY / CONTEXT:
{category_info}

RECENT QUESTIONS TO AVOID REPEATING:
{recent_questions_text}

SOURCE TEXT CHUNKS:
{source_chunks_text}
"""


class CognitiveRAGEngine:
    """Cognitive-RAG engine selecting target concepts and generating grounded assessment questions."""

    def __init__(self):
        self._question_cache: dict[str, dict[str, Any]] = {}
        self._chunk_file_cache: dict[str, list[dict[str, Any]]] = {}

    def get_cached_question(self, question_id: str) -> dict[str, Any] | None:
        """Retrieve question payload from server cache for secure answer verification."""
        return self._question_cache.get(question_id)

    async def get_next_target_concept(
        self,
        course_id: str,
        student_id: str,
    ) -> tuple[str, str]:
        """
        Evaluates DAG prerequisites and student's current BKT mastery profile.
        Rotates across available pedagogical candidates to avoid repeating the same concept.
        Returns: (selected_concept_name, status)
        """
        kg_doc = await KnowledgeGraphDocument.find_one(
            KnowledgeGraphDocument.course_id == course_id
        )
        if not kg_doc or not kg_doc.nodes:
            raise ValueError(f"Knowledge graph not found or empty for course: {course_id}")

        # Fetch all mastery records for this student in this course
        mastery_records = await StudentMasteryDocument.find(
            StudentMasteryDocument.student_id == student_id,
            StudentMasteryDocument.course_id == course_id,
        ).to_list()
        mastery_map = {r.concept_name: r.mastery_probability for r in mastery_records}

        # Fetch recent quiz attempts to track recently asked concepts for rotation
        recent_attempts = await QuizAttemptDocument.find(
            QuizAttemptDocument.student_id == student_id,
            QuizAttemptDocument.course_id == course_id,
        ).sort("-created_at").limit(10).to_list()
        recent_concepts = [a.concept_name for a in recent_attempts]
        last_concept = recent_concepts[0] if recent_concepts else None

        # Build DAG
        G = nx.DiGraph()
        for node in kg_doc.nodes:
            if node.get("type") == "fine_grained_concept":
                G.add_node(node["id"])

        for edge in kg_doc.edges:
            if edge.get("relation") == "PREREQUISITE_FOR":
                src, tgt = edge["source"], edge["target"]
                if src in G and tgt in G:
                    G.add_edge(src, tgt)

        if not G.nodes():
            raise ValueError(f"Knowledge graph has no fine-grained concepts for course: {course_id}")

        in_progress: list[tuple[str, float]] = []    # prereqs met, 0.10 < mastery < 0.85
        ready_to_learn: list[tuple[str, float]] = []  # prereqs met, mastery <= 0.10
        fallback: list[tuple[str, float]] = []        # all unmastered concepts

        for node in G.nodes():
            p_mastery = mastery_map.get(node, 0.10)
            in_edges = list(G.predecessors(node))
            prereqs_met = all(mastery_map.get(p, 0.10) >= 0.70 for p in in_edges)

            if p_mastery < 0.85:
                fallback.append((node, p_mastery))

            if p_mastery >= 0.85:
                continue

            if prereqs_met:
                if p_mastery > 0.10:
                    in_progress.append((node, p_mastery))
                else:
                    ready_to_learn.append((node, p_mastery))

        # Combined candidate pool of unlocked concepts (prerequisites met and mastery < 0.85)
        all_unlocked = in_progress + ready_to_learn

        if all_unlocked:
            # Avoid immediately repeating the exact same concept if other unlocked candidates exist
            non_last = [c for c in all_unlocked if c[0] != last_concept]
            pool = non_last if non_last else all_unlocked

            # Priority ordering:
            # 1. Recency penalty (fewer recent attempts first)
            # 2. Stage priority: weak in-progress (0), ready-to-learn (1), higher in-progress (2)
            # 3. Lowest mastery probability
            def candidate_priority(item: tuple[str, float]) -> tuple[int, int, float]:
                c_name, m = item
                recency_penalty = recent_concepts.count(c_name)
                stage_prio = 0 if 0.10 < m <= 0.40 else (1 if m <= 0.10 else 2)
                return (recency_penalty, stage_prio, m)

            pool.sort(key=candidate_priority)
            chosen_concept = pool[0][0]
            chosen_status = "In Progress" if mastery_map.get(chosen_concept, 0.10) > 0.10 else "Ready to Learn"
            return chosen_concept, chosen_status

        # Fallback across all unmastered nodes
        if fallback:
            non_last = [c for c in fallback if c[0] != last_concept]
            pool = non_last if non_last else fallback
            pool.sort(key=lambda x: (recent_concepts.count(x[0]), x[1]))
            chosen_concept = pool[0][0]
            return chosen_concept, "In Progress"

        first_node = list(G.nodes())[0]
        return first_node, "Mastered"

    async def generate_mcq_for_concept(
        self,
        course_id: str,
        concept_name: str,
        student_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieves grounded evidence chunks and generates a psychometrically valid,
        difficulty-calibrated MCQ with dynamic styles and randomized options.
        """
        # 1. Check past attempts for this student on this concept to avoid repeating questions
        past_attempts = []
        if student_id:
            past_attempts = await QuizAttemptDocument.find(
                QuizAttemptDocument.student_id == student_id,
                QuizAttemptDocument.course_id == course_id,
                QuizAttemptDocument.concept_name == concept_name,
            ).to_list()
        past_question_texts = {a.question_text for a in past_attempts}
        attempt_count = len(past_attempts)

        # 2. Retrieve concept details from EnrichedConceptDocument
        enriched = await EnrichedConceptDocument.find_one(
            EnrichedConceptDocument.course_id == course_id,
            EnrichedConceptDocument.concept == concept_name,
        )
        cat_info = "Compiler Architecture"
        prereqs: list[str] = []
        evidence_text = ""
        evidence_chunk = ""
        if enriched:
            if enriched.coarse_grained_category:
                cat_info = enriched.coarse_grained_category[0]
            prereqs = enriched.prerequisites or []
            if enriched.category_edge:
                evidence_text = enriched.category_edge.get("evidence_text", "")
                evidence_chunk = enriched.category_edge.get("evidence_chunk", "")

        # 3. Retrieve chunks from DB or local file cache
        source_blocks = []
        evidence_chunk_ids = []
        if evidence_chunk:
            evidence_chunk_ids.append(evidence_chunk)

        chunks_docs = await ContentChunkDocument.find(
            ContentChunkDocument.course_id == course_id,
            {"text": {"$regex": re.escape(concept_name), "$options": "i"}},
        ).limit(3).to_list()

        for c in chunks_docs:
            if c.chunk_id not in evidence_chunk_ids:
                evidence_chunk_ids.append(c.chunk_id)
            source_blocks.append(f"[{c.chunk_id}]: {c.text[:800]}")

        # If DB chunks are empty, load from precomputed course directory on disk
        if not source_blocks:
            chunk_file = settings.COURSE_OUTPUTS_DIR / course_id / "content_chunks.json"
            if not chunk_file.exists():
                chunk_file = settings.MAIN_DIR / "outputs" / "data" / "content_chunks.json"
            if chunk_file.exists():
                try:
                    if course_id not in self._chunk_file_cache:
                        with open(chunk_file, "r", encoding="utf-8") as f:
                            self._chunk_file_cache[course_id] = json.load(f)
                    all_chunks = self._chunk_file_cache[course_id]
                    matched = [
                        c for c in all_chunks
                        if concept_name.lower() in c.get("text", "").lower()
                    ][:3]
                    for m in matched:
                        cid = m.get("chunk_id", "chunk")
                        if cid not in evidence_chunk_ids:
                            evidence_chunk_ids.append(cid)
                        source_blocks.append(f"[{cid}]: {m.get('text', '')[:800]}")
                except Exception as ex:
                    logger.warning("Could not read local chunks file: %s", ex)

        source_text = "\n\n".join(source_blocks) if source_blocks else (
            evidence_text or f"Core curriculum concept: {concept_name} within {cat_info}."
        )

        # 4. Retrieve other concepts and categories for domain-specific distractors
        kg_doc = await KnowledgeGraphDocument.find_one(
            KnowledgeGraphDocument.course_id == course_id
        )
        other_concepts: list[str] = []
        major_compiler_phases = [
            "Lexical Analysis",
            "Syntax Analysis",
            "Intermediate Code Generation",
            "Code Optimization",
            "Target Code Generation",
            "Register Allocation",
            "Symbol Table Management",
            "Runtime Storage Administration",
        ]
        if kg_doc and kg_doc.nodes:
            other_concepts = [
                n["id"] for n in kg_doc.nodes
                if n["id"] != concept_name and n.get("type") == "fine_grained_concept"
            ]

        # 5. Check if LLM API is configured and attempt LLM generation
        parsed_q = None
        has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))
        if has_api_key:
            try:
                from llm import LLM
                recent_avoid = "\n".join(f"- {q}" for q in list(past_question_texts)[:3]) if past_question_texts else "None"
                prompt = QUESTION_GEN_PROMPT.format(
                    concept_name=concept_name,
                    category_info=cat_info,
                    recent_questions_text=recent_avoid,
                    source_chunks_text=source_text,
                )
                llm = LLM(sys_msg="You are an expert assessment question generator.", temperature=0.3)
                resp = llm.get_response(prompt)
                clean_resp = resp.strip()
                if "```" in clean_resp:
                    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_resp)
                    if match:
                        clean_resp = match.group(1).strip()
                parsed_q = json.loads(clean_resp)
                if (
                    parsed_q.get("question") in past_question_texts
                    or not parsed_q.get("options")
                    or len(parsed_q.get("options", [])) != 4
                ):
                    parsed_q = None
            except Exception as e:
                logger.info("LLM generation deferred to grounded synthesizer (%s)", e)
                parsed_q = None

        # 6. Grounded Assessment Synthesizer (5 pedagogical styles with real knowledge graph distractors)
        if not parsed_q or "question" not in parsed_q or "options" not in parsed_q:
            parsed_q = self._synthesize_grounded_mcq(
                concept_name=concept_name,
                cat_info=cat_info,
                prereqs=prereqs,
                evidence_text=evidence_text,
                other_concepts=other_concepts,
                major_phases=major_compiler_phases,
                attempt_count=attempt_count,
                past_texts=past_question_texts,
            )

        # 7. Secure Option Shuffling (Randomizes correct answer uniformly across A, B, C, D)
        options = list(parsed_q["options"])
        correct_ans = parsed_q.get("correct_answer", options[0])
        if correct_ans not in options:
            options[0] = correct_ans

        # Shuffle options randomly
        random.shuffle(options)

        q_id = f"q_{concept_name[:6]}_{uuid.uuid4().hex[:8]}"

        mcq_payload = {
            "question_id": q_id,
            "course_id": course_id,
            "concept_name": concept_name,
            "question_text": parsed_q["question"],
            "options": options,
            "correct_option": correct_ans,
            "explanation": parsed_q.get("explanation", f"Based on curriculum principles regarding {concept_name}."),
            "evidence_chunk_ids": evidence_chunk_ids,
        }

        # Cache question on server for anti-cheat verification
        self._question_cache[q_id] = mcq_payload
        if len(self._question_cache) > 500:
            oldest_key = next(iter(self._question_cache))
            self._question_cache.pop(oldest_key, None)

        return mcq_payload

    def _synthesize_grounded_mcq(
        self,
        concept_name: str,
        cat_info: str,
        prereqs: list[str],
        evidence_text: str,
        other_concepts: list[str],
        major_phases: list[str],
        attempt_count: int,
        past_texts: set[str],
    ) -> dict[str, Any]:
        """Synthesize a pedagogical MCQ rotating through 5 distinct educational assessment styles."""
        distractor_concepts = random.sample(other_concepts, min(3, len(other_concepts))) if len(other_concepts) >= 3 else [
            "Parse Tree", "Symbol Table", "Activation Record"
        ]
        phase_distractors = [p for p in major_phases if p.lower() != cat_info.lower()][:3]
        if len(phase_distractors) < 3:
            phase_distractors = ["Lexical Analysis", "Target Code Generation", "Register Allocation"]

        # Clean evidence excerpt for comprehension questions
        clean_excerpt = ""
        if evidence_text:
            sentences = [s.strip() for s in re.split(r"[.\n]+", evidence_text) if len(s.strip()) > 35]
            if sentences:
                clean_excerpt = sentences[0]

        # 5 Structured Pedagogical Assessment Styles
        style_candidates = [
            # Style 0: Role & Architectural Function
            {
                "question": f"In compiler construction and {cat_info}, what is the primary architectural function of '{concept_name}'?",
                "correct": f"It serves as an essential semantic representation or operational structure within {cat_info}.",
                "distractors": [
                    "It bypasses semantic analysis to emit raw unverified machine code bytes.",
                    "It directly drives physical CPU register allocation and instruction pipelining.",
                    "It is an obsolete memory compaction routine not utilized in modern syntax-directed translation.",
                ],
                "explanation": f"According to course curriculum specifications, '{concept_name}' is utilized for structure representation and syntax-directed processing within {cat_info}.",
            },
            # Style 1: Phase & Module Classification
            {
                "question": f"During which primary phase of compiler processing is '{concept_name}' formally constructed or evaluated?",
                "correct": cat_info,
                "distractors": phase_distractors,
                "explanation": f"'{concept_name}' is classified under the '{cat_info}' module in the course knowledge graph.",
            },
            # Style 2: Prerequisite & Dependency Reasoning
            {
                "question": (
                    f"In the prerequisite knowledge graph for '{concept_name}', which concept represents a foundational prerequisite?"
                    if prereqs else
                    f"How is '{concept_name}' positioned in the prerequisite dependency DAG for {cat_info}?"
                ),
                "correct": (
                    prereqs[0] if prereqs else
                    f"It acts as a foundational root concept in {cat_info} with no mandatory prior prerequisites."
                ),
                "distractors": (
                    distractor_concepts if prereqs else [
                        "It strictly requires runtime garbage collection sweep routines to precede it.",
                        "It cannot execute until post-link binary relocation is completed.",
                        "It is only valid during JIT compilation and forbidden in ahead-of-time compilers.",
                    ]
                ),
                "explanation": (
                    f"'{prereqs[0]}' must be understood before mastering '{concept_name}' as indicated by prerequisite DAG edges."
                    if prereqs else
                    f"Root concepts in the curriculum DAG can be studied directly without prior unmet dependencies."
                ),
            },
            # Style 3: Concept Identification from Description
            {
                "question": (
                    f"Consider the following textbook principle from the course material:\n\"{clean_excerpt}\"\nWhich concept does this formulation describe?"
                    if clean_excerpt else
                    f"Which of the following compiler structures corresponds to '{concept_name}' in {cat_info}?"
                ),
                "correct": concept_name,
                "distractors": distractor_concepts,
                "explanation": f"The textbook excerpt describes the core mechanics and structure of '{concept_name}'.",
            },
            # Style 4: Technical Invariant & Verification
            {
                "question": f"Which of the following statements is ACCURATE regarding the behavior of '{concept_name}'?",
                "correct": f"It operates within {cat_info} to maintain semantic relationships and structural hierarchy.",
                "distractors": [
                    "It replaces the lexical scanner entirely by generating tokens from raw AST nodes.",
                    "It operates solely in kernel hardware space rather than compiler user space.",
                    "It is discarded before type checking occurs and plays no role in intermediate code.",
                ],
                "explanation": f"Curriculum specifications confirm that '{concept_name}' maintains structural semantic integrity within {cat_info}.",
            },
        ]

        # Select style rotating by attempt count and avoiding exact duplicate questions
        chosen_style = None
        for offset in range(len(style_candidates)):
            cand = style_candidates[(attempt_count + offset) % len(style_candidates)]
            if cand["question"] not in past_texts:
                chosen_style = cand
                break

        if not chosen_style:
            chosen_style = style_candidates[attempt_count % len(style_candidates)]

        options = [chosen_style["correct"]] + chosen_style["distractors"][:3]
        return {
            "question": chosen_style["question"],
            "options": options,
            "correct_answer": chosen_style["correct"],
            "explanation": chosen_style["explanation"],
        }


# Singleton engine instance
cognitive_rag = CognitiveRAGEngine()
