"""
server/services/cognitive_rag.py — Cognitive-RAG Context Builder & MCQ Question Generator.
Selects optimal concepts along the prerequisite DAG and generates dynamic, grounded assessment items.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any
import networkx as nx
from dotenv import load_dotenv

from server.config import settings
from server.models.knowledge import (
    ConceptChunkMappingDocument,
    ContentChunkDocument,
    EnrichedConceptDocument,
    KnowledgeGraphDocument,
)
from server.models.student import (
    QuizAttemptDocument,
    StudentMasteryDocument,
    StudentNavigationStateDocument,
)

# Ensure .env is loaded into os.environ and Main/ is importable for Main/llm.py
load_dotenv(settings.PROJECT_ROOT / ".env", override=False)
_main_dir_str = str(settings.MAIN_DIR)
if _main_dir_str not in sys.path:
    sys.path.insert(0, _main_dir_str)

logger = logging.getLogger("server.services.cognitive_rag")

# Graph-Aware Navigation Thresholds (matching Main/CogRAG/adaptive_engine.py)
MASTERY_THRESHOLD = 0.85
WEAK_THRESHOLD = 0.40
RECENT_WINDOW = 5

DIFFICULTY_GUIDANCE = {
    "easy": "Easy (definition-based, terminology recognition, or foundational identification)",
    "medium": "Medium (comparison-based, why/how reasoning, or relationship analysis)",
    "hard": "Hard (application scenario, debugging/error spotting, or best architectural design choice)",
}

QUESTION_GEN_PROMPT = """You are an expert educational assessment designer.
Generate an educational Multiple-Choice Question (MCQ) testing comprehension of the concept: "{concept_name}".

DIFFICULTY LEVEL:
{difficulty_guidance}

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
    """Cognitive-RAG engine selecting target concepts along the prerequisite DAG and generating grounded MCQs."""

    def __init__(self):
        self._question_cache: dict[str, dict[str, Any]] = {}
        self._chunk_file_cache: dict[str, list[dict[str, Any]]] = {}
        self._chunk_map_file_cache: dict[str, dict[str, list[str]]] = {}
        self._llm_client: Any = None
        self._tutor_llm_client: Any = None

    def _get_llm_client(self):
        """Lazily initialize and reuse Main/llm.py LLM singleton (preserves key/model rotation & RPM state)."""
        if self._llm_client is None:
            from llm import LLM
            self._llm_client = LLM(
                sys_msg=(
                    "You are an expert psychometrician and senior professor specializing in educational "
                    "assessment, item response theory, and Bayesian Knowledge Tracing (BKT). "
                    "Generate psychometrically valid, textbook-grounded MCQ questions in strict JSON."
                ),
                temperature=0.4,
            )
        return self._llm_client

    def get_tutor_llm_client(self):
        """Lazily initialize and reuse Main/llm.py LLM singleton for AI Tutor."""
        if self._tutor_llm_client is None:
            from llm import LLM
            self._tutor_llm_client = LLM(
                sys_msg=(
                    "You are an encouraging, expert academic AI Tutor specializing in computer science "
                    "and curriculum topics. Explain concepts clearly with precise textbook citations."
                ),
                temperature=0.3,
            )
        return self._tutor_llm_client

    def get_cached_question(self, question_id: str) -> dict[str, Any] | None:
        """Retrieve question payload from server cache for secure answer verification."""
        return self._question_cache.get(question_id)

    @staticmethod
    def _build_prereq_dag(kg_doc: KnowledgeGraphDocument) -> nx.DiGraph:
        """Build directed prerequisite DAG with edge confidence weights."""
        G = nx.DiGraph()
        for node in kg_doc.nodes:
            if node.get("type") == "fine_grained_concept":
                G.add_node(node["id"])

        for edge in kg_doc.edges:
            if edge.get("relation") == "PREREQUISITE_FOR":
                src, tgt = edge["source"], edge["target"]
                if src in G and tgt in G:
                    try:
                        conf = float(edge.get("confidence", 0.60))
                    except Exception:
                        conf = 0.60
                    G.add_edge(src, tgt, relation="PREREQUISITE_FOR", confidence=conf)
        return G

    @staticmethod
    def _get_difficulty(p_know: float) -> str:
        """Calibrate MCQ difficulty from student's BKT mastery (mirrors CogRAG adaptive_engine)."""
        if p_know < WEAK_THRESHOLD:
            return "easy"
        if p_know < MASTERY_THRESHOLD:
            return "medium"
        return "hard"

    @staticmethod
    def _weakest_unmastered(
        concepts: list[str],
        mastery_map: dict[str, float],
        recent_set: set[str],
        exclude_recent: bool = True,
    ) -> str | None:
        recent = recent_set if exclude_recent else set()
        candidates = [
            c for c in concepts
            if mastery_map.get(c, 0.10) < MASTERY_THRESHOLD and c not in recent
        ]
        if not candidates:
            candidates = [
                c for c in concepts
                if mastery_map.get(c, 0.10) < MASTERY_THRESHOLD
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda c: mastery_map.get(c, 0.10))

    @staticmethod
    def _select_preferred_successor(
        G: nx.DiGraph,
        concept: str,
        mastery_map: dict[str, float],
        recent_set: set[str],
    ) -> str | None:
        """Select highest-priority unmastered outgoing PREREQUISITE_FOR successor."""
        if concept not in G:
            return None
        unmastered: list[tuple[str, float]] = []
        for _, dst, edge_data in G.out_edges(concept, data=True):
            if edge_data.get("relation") == "PREREQUISITE_FOR":
                if mastery_map.get(dst, 0.10) < MASTERY_THRESHOLD:
                    conf = float(edge_data.get("confidence", 0.60))
                    unmastered.append((dst, conf))
        if not unmastered:
            return None

        # Rank by: not in recent window, highest edge confidence, lowest mastery
        unmastered.sort(
            key=lambda item: (
                1 if item[0] in recent_set else 0,
                -item[1],
                mastery_map.get(item[0], 0.10),
            )
        )
        return unmastered[0][0]

    def _global_fallback_concept(
        self,
        G: nx.DiGraph,
        mastery_map: dict[str, float],
        recent_set: set[str],
    ) -> str:
        """Prefer weakest unmastered root concept (0 incoming prereqs), else weakest global unmastered."""
        roots = [n for n in G.nodes() if G.in_degree(n) == 0]
        root_choice = self._weakest_unmastered(roots, mastery_map, recent_set, exclude_recent=True)
        if root_choice:
            return root_choice

        all_nodes = list(G.nodes())
        unmastered = self._weakest_unmastered(all_nodes, mastery_map, recent_set, exclude_recent=True)
        if unmastered:
            return unmastered

        return min(all_nodes, key=lambda c: mastery_map.get(c, 0.10))

    async def _get_or_create_nav_state(
        self,
        student_id: str,
        course_id: str,
    ) -> StudentNavigationStateDocument:
        nav = await StudentNavigationStateDocument.find_one(
            StudentNavigationStateDocument.student_id == student_id,
            StudentNavigationStateDocument.course_id == course_id,
        )
        if not nav:
            nav = StudentNavigationStateDocument(
                student_id=student_id,
                course_id=course_id,
            )
            await nav.insert()
        return nav

    async def set_current_concept(
        self,
        course_id: str,
        student_id: str,
        concept_name: str,
    ) -> None:
        """Sync navigation state when a student manually selects a concept to study."""
        nav = await self._get_or_create_nav_state(student_id, course_id)
        if nav.current_concept != concept_name:
            nav.current_concept = concept_name
            recent = [c for c in (nav.recent_concepts or []) if c]
            recent.append(concept_name)
            nav.recent_concepts = recent[-RECENT_WINDOW:]
            nav.updated_at = datetime.now(timezone.utc)
            await nav.save()

    async def select_next_concept_with_navigation(
        self,
        course_id: str,
        student_id: str,
        last_concept_answered: str | None = None,
        last_is_correct: bool | None = None,
    ) -> dict[str, Any]:
        """
        Graph-Aware Adaptive Navigation Policy (mirrors Main/CogRAG/adaptive_engine.py):
        1. First run -> weakest unmastered root concept (0 incoming prerequisites).
        2. Return-target mode -> once all prerequisites of return_target are mastered (>=0.85),
           resume return_target; otherwise remediate weakest unmastered prerequisite.
        3. Weak mastery (<=0.40) on wrong/initial state -> step backward along incoming
           PREREQUISITE_FOR edge to weakest unmastered predecessor and store return_target.
        4. Mastered (>=0.85) -> advance forward along outgoing PREREQUISITE_FOR edge to
           highest-confidence unmastered successor (or global fallback if branch complete).
        5. Moderate mastery (0.40 < p < 0.85, or climbing after correct answer) -> continue
           practicing current concept toward 85% mastery.
        """
        kg_doc = await KnowledgeGraphDocument.find_one(
            KnowledgeGraphDocument.course_id == course_id
        )
        if not kg_doc or not kg_doc.nodes:
            raise ValueError(f"Knowledge graph not found or empty for course: {course_id}")

        G = self._build_prereq_dag(kg_doc)
        if not G.nodes():
            raise ValueError(f"Knowledge graph has no fine-grained concepts for course: {course_id}")

        # Fetch student's current mastery states
        mastery_records = await StudentMasteryDocument.find(
            StudentMasteryDocument.student_id == student_id,
            StudentMasteryDocument.course_id == course_id,
        ).to_list()
        mastery_map = {r.concept_name: r.mastery_probability for r in mastery_records}

        nav = await self._get_or_create_nav_state(student_id, course_id)

        # If caller just answered a specific concept, anchor traversal to that concept
        if last_concept_answered and last_concept_answered in G:
            nav.current_concept = last_concept_answered

        current = nav.current_concept
        return_target = nav.return_target
        recent_set = set(nav.recent_concepts or [])

        chosen: str
        transition_type: str
        reason: str

        # 1. First run / uninitialized
        if not current or current not in G:
            chosen = self._global_fallback_concept(G, mastery_map, recent_set)
            nav.return_target = None
            transition_type = "root"
            reason = f"Starting with foundational concept '{chosen}'."

        # 2. Return-target remediation mode
        elif return_target and return_target in G:
            target_prereqs = list(G.predecessors(return_target))
            unmastered_target = [
                c for c in target_prereqs
                if mastery_map.get(c, 0.10) < MASTERY_THRESHOLD
            ]

            if not unmastered_target:
                # All prerequisites of return_target are now mastered -> resume return_target!
                chosen = return_target
                nav.return_target = None
                transition_type = "resume_target"
                reason = f"Prerequisites mastered! Returning to target concept '{chosen}'."
            else:
                current_p = mastery_map.get(current, 0.10)
                if current in unmastered_target:
                    # If wrong answer and this prerequisite itself has an unmastered prerequisite, step deeper
                    deeper_preds = [
                        p for p in G.predecessors(current)
                        if mastery_map.get(p, 0.10) < MASTERY_THRESHOLD and p != return_target
                    ]
                    if last_is_correct is False and current_p <= WEAK_THRESHOLD and deeper_preds:
                        chosen = self._weakest_unmastered(deeper_preds, mastery_map, recent_set) or deeper_preds[0]
                        transition_type = "remediate_predecessor"
                        reason = f"Stepping back to prerequisite '{chosen}' to reinforce '{current}' (return target: '{return_target}')."
                    else:
                        chosen = current
                        transition_type = "remediate_predecessor"
                        reason = f"Continuing prerequisite '{chosen}' before returning to '{return_target}'."
                else:
                    # Current prerequisite was mastered (or changed); move to next unmastered prereq of return_target
                    next_prereq = self._weakest_unmastered(unmastered_target, mastery_map, recent_set)
                    chosen = next_prereq or unmastered_target[0]
                    transition_type = "remediate_predecessor"
                    reason = f"Prerequisite '{current}' completed — remediating '{chosen}' before returning to '{return_target}'."

        else:
            current_p = mastery_map.get(current, 0.10)

            # 3. Weak concept (<= 0.40) on wrong answer or initial entry -> remediate to weakest predecessor
            if current_p <= WEAK_THRESHOLD and last_is_correct is not True:
                unmastered_preds = [
                    p for p in G.predecessors(current)
                    if mastery_map.get(p, 0.10) < MASTERY_THRESHOLD
                ]
                pred = self._weakest_unmastered(unmastered_preds, mastery_map, recent_set)
                if pred:
                    nav.return_target = current
                    chosen = pred
                    transition_type = "remediate_predecessor"
                    reason = f"Stepping back to prerequisite '{pred}' to build foundation for '{current}'."
                else:
                    chosen = current
                    transition_type = "practice_current"
                    reason = f"Reinforcing foundational concept '{current}' at easy difficulty (no unmet prerequisites)."

            # 4. Mastered concept (>= 0.85) -> advance forward along outgoing PREREQUISITE_FOR edge
            elif current_p >= MASTERY_THRESHOLD:
                next_succ = self._select_preferred_successor(G, current, mastery_map, recent_set)
                if next_succ:
                    chosen = next_succ
                    transition_type = "advance_successor"
                    reason = f"Mastered '{current}'! Advancing along knowledge graph to successor '{next_succ}'."
                else:
                    fallback = self._global_fallback_concept(G, mastery_map, recent_set)
                    nav.return_target = None
                    chosen = fallback
                    transition_type = "fallback"
                    reason = f"Mastered '{current}' (branch complete) — moving to next unmastered concept '{fallback}'."

            # 5. Moderate mastery (or climbing after a correct answer) -> continue practicing current concept
            else:
                chosen = current
                transition_type = "practice_current"
                reason = f"Progressing on '{current}' ({round(current_p * 100, 1)}%) — continuing practice toward 85% mastery."

        # Persist updated navigation state
        nav.current_concept = chosen
        updated_recent = [c for c in (nav.recent_concepts or []) if c]
        if not updated_recent or updated_recent[-1] != chosen:
            updated_recent.append(chosen)
        nav.recent_concepts = updated_recent[-RECENT_WINDOW:]
        nav.last_transition_type = transition_type
        nav.last_transition_reason = reason
        nav.updated_at = datetime.now(timezone.utc)
        await nav.save()

        chosen_p = mastery_map.get(chosen, 0.10)
        if chosen_p >= MASTERY_THRESHOLD:
            status_label = "Mastered"
        elif chosen_p > 0.10:
            status_label = "In Progress"
        else:
            status_label = "Ready to Learn"

        return {
            "concept_name": chosen,
            "status": status_label,
            "transition_type": transition_type,
            "navigation_reason": reason,
            "return_target": nav.return_target,
        }

    async def get_next_target_concept(
        self,
        course_id: str,
        student_id: str,
    ) -> tuple[str, str]:
        """Backwards-compatible wrapper returning (selected_concept_name, status)."""
        result = await self.select_next_concept_with_navigation(
            course_id=course_id,
            student_id=student_id,
        )
        return result["concept_name"], result["status"]

    async def get_grounded_chunks_for_concept(
        self,
        course_id: str,
        concept_name: str,
        evidence_chunk: str = "",
        evidence_text: str = "",
        max_chunks: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Retrieve grounded textbook chunks (chunk_id, page_number, text) for a concept
        from MongoDB or precomputed course/Main JSON artifacts.
        """
        source_chunks: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        def _add_chunk(cid: str, text: str, page_number: int | None = None):
            clean_text = (text or "").strip()
            if not clean_text or cid in seen_ids:
                return
            seen_ids.add(cid)
            source_chunks.append({
                "chunk_id": cid,
                "page_number": page_number,
                "text": clean_text[:1000],
            })

        # 1. Check MongoDB ContentChunkDocument via ConceptChunkMappingDocument + regex match
        mapping_doc = await ConceptChunkMappingDocument.find_one(
            ConceptChunkMappingDocument.course_id == course_id,
            ConceptChunkMappingDocument.concept_name == concept_name,
        )
        priority_ids: list[str] = []
        if evidence_chunk:
            priority_ids.append(evidence_chunk)
        if mapping_doc and mapping_doc.qualifying_chunks:
            for entry in mapping_doc.qualifying_chunks:
                cid = entry.get("chunk_id") if isinstance(entry, dict) else str(entry)
                if cid and cid not in priority_ids:
                    priority_ids.append(cid)

        if priority_ids:
            mapped_docs = await ContentChunkDocument.find(
                ContentChunkDocument.course_id == course_id,
                {"chunk_id": {"$in": priority_ids[:max_chunks]}},
            ).to_list()
            for doc in mapped_docs:
                _add_chunk(doc.chunk_id, doc.text, getattr(doc, "page_number", None))

        if len(source_chunks) < max_chunks:
            regex_docs = await ContentChunkDocument.find(
                ContentChunkDocument.course_id == course_id,
                {"text": {"$regex": re.escape(concept_name), "$options": "i"}},
            ).limit(max_chunks).to_list()
            for doc in regex_docs:
                if len(source_chunks) >= max_chunks:
                    break
                _add_chunk(doc.chunk_id, doc.text, getattr(doc, "page_number", None))

        # 2. Fallback to precomputed JSON files on disk if MongoDB chunks are empty
        if len(source_chunks) < max_chunks:
            chunk_file = settings.COURSE_OUTPUTS_DIR / course_id / "content_chunks.json"
            if not chunk_file.exists():
                chunk_file = settings.MAIN_DIR / "outputs" / "data" / "content_chunks.json"

            map_file = settings.COURSE_OUTPUTS_DIR / course_id / "concept_chunk_map.json"
            if not map_file.exists():
                map_file = settings.MAIN_DIR / "outputs" / "data" / "concept_chunk_map.json"

            if chunk_file.exists():
                try:
                    if course_id not in self._chunk_file_cache:
                        with open(chunk_file, "r", encoding="utf-8") as f:
                            self._chunk_file_cache[course_id] = json.load(f)
                    all_chunks = self._chunk_file_cache[course_id]
                    chunk_by_id = {c.get("chunk_id"): c for c in all_chunks if c.get("chunk_id")}

                    if map_file.exists() and course_id not in self._chunk_map_file_cache:
                        try:
                            with open(map_file, "r", encoding="utf-8") as f:
                                self._chunk_map_file_cache[course_id] = json.load(f)
                        except Exception:
                            self._chunk_map_file_cache[course_id] = {}

                    cc_map = self._chunk_map_file_cache.get(course_id, {})
                    disk_priority_ids = list(priority_ids)
                    for cid in cc_map.get(concept_name, []):
                        if cid not in disk_priority_ids:
                            disk_priority_ids.append(cid)

                    for cid in disk_priority_ids:
                        if len(source_chunks) >= max_chunks:
                            break
                        if cid in chunk_by_id:
                            m = chunk_by_id[cid]
                            _add_chunk(cid, m.get("text", ""), m.get("page_number"))

                    if len(source_chunks) < max_chunks:
                        cname_lower = concept_name.lower()
                        for m in all_chunks:
                            if len(source_chunks) >= max_chunks:
                                break
                            if cname_lower in m.get("text", "").lower():
                                _add_chunk(
                                    m.get("chunk_id", "chunk"),
                                    m.get("text", ""),
                                    m.get("page_number"),
                                )
                except Exception as ex:
                    logger.warning("Could not read local chunks file: %s", ex)

        # 3. Final fallback to EnrichedConceptDocument evidence_text
        if not source_chunks:
            if not evidence_text:
                enriched = await EnrichedConceptDocument.find_one(
                    EnrichedConceptDocument.course_id == course_id,
                    EnrichedConceptDocument.concept == concept_name,
                )
                if enriched and enriched.category_edge:
                    evidence_text = enriched.category_edge.get("evidence_text", "")
                    if not evidence_chunk:
                        evidence_chunk = enriched.category_edge.get("evidence_chunk", "")
            if evidence_text:
                _add_chunk(evidence_chunk or "kg_evidence", evidence_text, None)

        return source_chunks

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
        # 1. Check past attempts and current mastery for difficulty calibration
        past_attempts = []
        current_mastery = 0.10
        if student_id:
            past_attempts = await QuizAttemptDocument.find(
                QuizAttemptDocument.student_id == student_id,
                QuizAttemptDocument.course_id == course_id,
                QuizAttemptDocument.concept_name == concept_name,
            ).to_list()
            mastery_doc = await StudentMasteryDocument.find_one(
                StudentMasteryDocument.student_id == student_id,
                StudentMasteryDocument.course_id == course_id,
                StudentMasteryDocument.concept_name == concept_name,
            )
            if mastery_doc:
                current_mastery = mastery_doc.mastery_probability
        difficulty = self._get_difficulty(current_mastery)
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

        # 3. Retrieve grounded textbook chunks from DB or precomputed files
        source_chunks = await self.get_grounded_chunks_for_concept(
            course_id=course_id,
            concept_name=concept_name,
            evidence_chunk=evidence_chunk,
            evidence_text=evidence_text,
            max_chunks=3,
        )
        evidence_chunk_ids = [c["chunk_id"] for c in source_chunks]
        source_blocks = [f"[{c['chunk_id']}]: {c['text'][:800]}" for c in source_chunks]

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

        # 5. Check if LLM provider (Gemini with API key or local Ollama) is configured
        load_dotenv(settings.PROJECT_ROOT / ".env", override=False)
        parsed_q = None
        llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
        has_gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEYS", "").strip())
        llm_available = (llm_provider == "ollama") or has_gemini_key
        if llm_available:
            try:
                recent_avoid = "\n".join(f"- {q}" for q in list(past_question_texts)[:3]) if past_question_texts else "None"
                prompt = QUESTION_GEN_PROMPT.format(
                    concept_name=concept_name,
                    difficulty_guidance=DIFFICULTY_GUIDANCE.get(difficulty, DIFFICULTY_GUIDANCE["medium"]),
                    category_info=cat_info,
                    recent_questions_text=recent_avoid,
                    source_chunks_text=source_text,
                )
                llm = self._get_llm_client()
                resp = await asyncio.to_thread(llm.get_response, prompt)
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
            "source_chunks": source_chunks,
            "difficulty": difficulty,
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
