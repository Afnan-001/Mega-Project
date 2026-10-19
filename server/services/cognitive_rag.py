"""
server/services/cognitive_rag.py — Cognitive-RAG Context Builder & MCQ Question Generator.
Selects optimal concepts along the prerequisite DAG and prompts LLM with grounded textbook evidence.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any
import networkx as nx

from server.models.knowledge import (
    ConceptChunkMappingDocument,
    ContentChunkDocument,
    EnrichedConceptDocument,
    KnowledgeGraphDocument,
)
from server.models.student import StudentMasteryDocument

logger = logging.getLogger("server.services.cognitive_rag")

QUESTION_GEN_PROMPT = """You are an expert educational assessment designer.
Generate an educational Multiple-Choice Question (MCQ) testing comprehension of the concept: "{concept_name}".

STRICT CONSTRAINTS:
1. Base the question and options EXCLUSIVELY on the provided SOURCE TEXT CHUNKS below.
2. Do NOT invent facts or cite external information not grounded in the chunks.
3. Formulate exactly 4 distinct answer choices (A, B, C, D).
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

SOURCE TEXT CHUNKS:
{source_chunks_text}
"""


class CognitiveRAGEngine:
    """Cognitive-RAG engine selecting target concepts and generating grounded assessment questions."""

    async def get_next_target_concept(
        self,
        course_id: str,
        student_id: str,
    ) -> tuple[str, str]:
        """
        Evaluates DAG prerequisites and student's current BKT mastery profile.
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

        # Evaluate eligibility for each concept
        ready_to_learn: list[tuple[str, float]] = []
        mastered: list[tuple[str, float]] = []

        for node in G.nodes():
            p_mastery = mastery_map.get(node, 0.10)
            in_edges = list(G.predecessors(node))

            # Prerequisite condition: all prerequisites must have mastery >= 0.70
            prereqs_met = all(mastery_map.get(p, 0.10) >= 0.70 for p in in_edges)

            if p_mastery >= 0.85:
                mastered.append((node, p_mastery))
            elif prereqs_met:
                ready_to_learn.append((node, p_mastery))

        # Select concept with lowest mastery among ready concepts
        if ready_to_learn:
            ready_to_learn.sort(key=lambda x: x[1])
            return ready_to_learn[0][0], "In Progress"

        # If everything is mastered or all remaining are locked, select node with lowest mastery
        all_concepts = [(n, mastery_map.get(n, 0.10)) for n in G.nodes()]
        all_concepts.sort(key=lambda x: x[1])
        if all_concepts:
            return all_concepts[0][0], "In Progress"

        return kg_doc.nodes[0]["id"], "In Progress"

    async def generate_mcq_for_concept(
        self,
        course_id: str,
        concept_name: str,
    ) -> dict[str, Any]:
        """
        Retrieves grounded evidence chunks and prompts LLM to produce an educational MCQ.
        """
        # 1. Retrieve grounded chunk IDs for this concept
        mapping_doc = await ConceptChunkMappingDocument.find_one(
            ConceptChunkMappingDocument.course_id == course_id,
            ConceptChunkMappingDocument.concept_name == concept_name,
        )

        chunk_ids = []
        if mapping_doc and mapping_doc.qualifying_chunks:
            chunk_ids = [q["chunk_id"] for q in mapping_doc.qualifying_chunks[:3]]

        # 2. Retrieve chunk text content
        chunks_docs = []
        if chunk_ids:
            chunks_docs = await ContentChunkDocument.find(
                ContentChunkDocument.course_id == course_id,
                {"chunk_id": {"$in": chunk_ids}},
            ).to_list()

        # If no mapped chunks found, fallback to searching chunks containing the concept
        if not chunks_docs:
            chunks_docs = await ContentChunkDocument.find(
                ContentChunkDocument.course_id == course_id,
                {"text": {"$regex": re.escape(concept_name), "$options": "i"}},
            ).limit(2).to_list()

        source_blocks = []
        evidence_chunk_ids = []
        for c in chunks_docs:
            evidence_chunk_ids.append(c.chunk_id)
            source_blocks.append(f"[{c.chunk_id}]: {c.text[:800]}")

        source_text = "\n\n".join(source_blocks) if source_blocks else f"Core technical concept: {concept_name}."

        # 3. Retrieve category information
        enriched = await EnrichedConceptDocument.find_one(
            EnrichedConceptDocument.course_id == course_id,
            EnrichedConceptDocument.concept == concept_name,
        )
        cat_info = ", ".join(enriched.coarse_grained_category) if enriched and enriched.coarse_grained_category else "General Topic"

        # 4. Invoke LLM
        prompt = QUESTION_GEN_PROMPT.format(
            concept_name=concept_name,
            category_info=cat_info,
            source_chunks_text=source_text,
        )

        parsed_q = None
        try:
            from llm import LLM
            llm = LLM(sys_msg="You are an expert assessment question generator.", temperature=0.2)
            resp = llm.get_response(prompt)

            # Strip code fences if present
            clean_resp = resp.strip()
            if "```" in clean_resp:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_resp)
                if match:
                    clean_resp = match.group(1).strip()

            parsed_q = json.loads(clean_resp)
        except Exception as e:
            logger.warning("LLM MCQ generation failed (%s). Using fallback template.", e)

        # Fallback question template if LLM is unavailable or returned unparseable JSON
        if not parsed_q or "question" not in parsed_q or "options" not in parsed_q:
            parsed_q = {
                "question": f"Which of the following statements best describes '{concept_name}' in this subject?",
                "options": [
                    f"It is a core foundational component associated with {cat_info}.",
                    f"It is a deprecated secondary routine not used in {cat_info}.",
                    f"It represents an unrelated operating system interrupt.",
                    f"It is an obsolete hardware specification.",
                ],
                "correct_answer": f"It is a core foundational component associated with {cat_info}.",
                "explanation": f"According to course documentation, {concept_name} plays an essential role in {cat_info}.",
            }

        # Validate options structure
        options = parsed_q.get("options", [])
        if not isinstance(options, list) or len(options) < 4:
            options = [
                parsed_q.get("correct_answer", f"A valid representation of {concept_name}"),
                f"A secondary unrelated feature of {concept_name}",
                f"An obsolete protocol not applicable to {concept_name}",
                f"A hardware-level failure mode for {concept_name}",
            ]

        correct_ans = parsed_q.get("correct_answer", options[0])
        if correct_ans not in options:
            options[0] = correct_ans

        q_id = f"q_{uuid.uuid4().hex[:10]}"

        return {
            "question_id": q_id,
            "course_id": course_id,
            "concept_name": concept_name,
            "question_text": parsed_q["question"],
            "options": options,
            "correct_option": correct_ans,
            "explanation": parsed_q.get("explanation", f"Reference from course material on {concept_name}."),
            "evidence_chunk_ids": evidence_chunk_ids,
        }


# Singleton engine instance
cognitive_rag = CognitiveRAGEngine()
