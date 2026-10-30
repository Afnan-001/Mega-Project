"""
question_generator.py — Grounded multi-concept MCQ generation engine with psychometric cognitive weights.
Generates difficulty-calibrated assessment items grounded exclusively in retrieved textbook chunks.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("corgag.question_gen")

CURRENT_DIR = Path(__file__).resolve().parent
MAIN_DIR = CURRENT_DIR.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from llm import LLM
from retriever import (
    embed_query,
    get_chunk_lookup,
    normalize_vector,
    retrieve_context_for_concepts,
)

OUTPUTS_DIR = MAIN_DIR / "outputs"
DATA_DIR = OUTPUTS_DIR / "data"
OUTPUT_FILE = DATA_DIR / "generated_mcqs.json"

SEMANTIC_DUPLICATE_THRESHOLD = 0.82
FAIL_OPEN_ON_EMBEDDING_ERROR = True
CONCEPT_WEIGHT_SUM_TOLERANCE = 0.02

# Initialize domain-generalized educational LLM
llm = LLM(
    sys_msg=(
        "You are an expert psychometrician and senior professor specializing in educational "
        "assessment, item response theory, and Bayesian Knowledge Tracing (BKT). "
        "Your mission is to generate psychometrically valid, factually grounded exam questions "
        "where cognitive concept weights precisely reflect the knowledge dependencies required."
    ),
    temperature=0.4,
)

QUESTION_STYLES = {
    "easy": [
        "definition-based",
        "terminology-based",
        "basic identification",
        "simple concept recognition",
    ],
    "medium": [
        "comparison-based",
        "why/how reasoning",
        "identify the correct statement",
        "concept relationship question",
    ],
    "hard": [
        "application scenario",
        "error spotting / debugging",
        "case-based reasoning",
        "best design choice",
    ],
}

PROMPT = """You are generating exactly ONE grounded academic multiple-choice question (MCQ) optimized for Bayesian Knowledge Tracing (BKT) evaluation.

HARD CONSTRAINTS:
1) Use ONLY the provided CONTEXT and AVAILABLE CHUNK IDS. Do NOT invent facts or cite outside knowledge.
2) Formulate exactly 4 distinct choices labeled "A. ", "B. ", "C. ", "D. ". Exactly one is correct; 3 are plausible distractors.
3) Provide a concise explanation citing evidence from the chunks.
4) Avoid repeating the same questions listed under RECENT QUESTIONS TO AVOID.
5) Return valid JSON only. No markdown fences, no conversational filler.

---
PRIMARY CONCEPT:
{primary_concept}

ALLOWED CONCEPTS (choose from this list only):
{allowed_concepts}

DIFFICULTY:
{difficulty}

QUESTION STYLE TO USE:
{question_style}

RECENT QUESTIONS TO AVOID:
{recent_questions}

AVAILABLE CHUNK IDS:
{available_chunk_ids}

CONTEXT:
{context}

---
CRITICAL INSTRUCTIONS FOR COGNITIVE CONCEPT WEIGHTS:
- Single Concept: If the context does not naturally test secondary concepts, assign 1.0 entirely to PRIMARY CONCEPT.
- Core Dependency (0.25 - 0.40): Assign to a secondary concept ONLY if solving or eliminating distractors strictly requires understanding that concept.
- Mathematical Constraint: The sum of all weights must equal exactly 1.0. The PRIMARY CONCEPT must always hold the strict maximum weight (>= 0.51).

OUTPUT JSON SCHEMA:
{{
  "question": "<concise unambiguous question stem>",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "A",
  "explanation": "<justification citing chunk evidence>",
  "source_chunks": ["CHUNK_ID_1", "CHUNK_ID_2"],
  "concepts_covered": ["PRIMARY_CONCEPT", "SECONDARY_CONCEPT"],
  "concept_weights": {{
    "PRIMARY_CONCEPT": 0.70,
    "SECONDARY_CONCEPT": 0.30
  }}
}}
"""


def normalize_concept_list(concepts: Optional[List[str]]) -> List[str]:
    cleaned: List[str] = []
    for c in concepts or []:
        if isinstance(c, str):
            val = c.strip()
            if val and val not in cleaned:
                cleaned.append(val)
    return cleaned


def build_question_key(primary_concept: str, secondary_concepts: Optional[List[str]] = None) -> str:
    sec = normalize_concept_list(secondary_concepts)
    if not sec:
        return primary_concept
    return f"{primary_concept}__{'|'.join(sec)}"


def load_existing() -> Dict[str, Any]:
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def normalize_question_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def save_mcq(
    primary_concept: str,
    difficulty: str,
    question: Dict[str, Any],
    secondary_concepts: Optional[List[str]] = None,
) -> bool:
    data = load_existing()
    q_key = build_question_key(primary_concept, secondary_concepts)

    if q_key not in data:
        data[q_key] = {"easy": [], "medium": [], "hard": []}
    if difficulty not in data[q_key]:
        data[q_key][difficulty] = []

    norm_target = normalize_question_text(question.get("question", ""))
    existing = [
        normalize_question_text(q.get("question", ""))
        for q in data[q_key][difficulty]
        if "question" in q
    ]
    if norm_target in existing:
        return False

    data[q_key][difficulty].append(question)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return True


def generate_id(existing: Dict[str, Any], primary_concept: str, difficulty: str, secondary_concepts: Optional[List[str]] = None) -> str:
    q_key = build_question_key(primary_concept, secondary_concepts)
    count = len(existing.get(q_key, {}).get(difficulty, [])) + 1
    safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", q_key)[:40]
    return f"{safe_key}_{difficulty}_{count}"


def get_existing_question(
    concept: str,
    difficulty: str,
    asked_ids: Set[str],
    wrong_ids: Set[str],
    secondary_concepts: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    data = load_existing()
    q_key = build_question_key(concept, secondary_concepts)
    if q_key not in data or difficulty not in data[q_key]:
        return None

    wrong_pool: List[Dict[str, Any]] = []
    fresh_pool: List[Dict[str, Any]] = []

    for q in data[q_key][difficulty]:
        qid = q.get("id")
        if not qid:
            continue
        if qid in wrong_ids:
            wrong_pool.append(q)
        elif qid not in asked_ids:
            fresh_pool.append(q)

    if wrong_pool:
        return random.choice(wrong_pool)
    if fresh_pool:
        return random.choice(fresh_pool)
    return None


def get_recent_metadata(
    concept: str,
    difficulty: str,
    limit: int = 6,
    secondary_concepts: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    data = load_existing()
    q_key = build_question_key(concept, secondary_concepts)
    if q_key not in data or difficulty not in data[q_key]:
        return [], []

    questions = data[q_key][difficulty][-limit:]
    recent_q = [q.get("question", "") for q in questions if q.get("question")]
    recent_chunks: List[str] = []
    for q in questions:
        chunks = q.get("source_chunks", [])
        if isinstance(chunks, list):
            recent_chunks.extend([cid for cid in chunks if isinstance(cid, str) and cid.strip()])

    return recent_q, recent_chunks


def choose_question_style(concept: str, difficulty: str, secondary_concepts: Optional[List[str]] = None) -> str:
    existing = load_existing()
    q_key = build_question_key(concept, secondary_concepts)
    count = len(existing.get(q_key, {}).get(difficulty, []))
    styles = QUESTION_STYLES.get(difficulty, QUESTION_STYLES["medium"])
    return styles[count % len(styles)]


def choose_diverse_chunks(all_chunks: List[str], recent_chunks: List[str], max_chunks: int = 4) -> List[str]:
    if not all_chunks:
        return []
    preferred = [c for c in all_chunks if c not in recent_chunks]
    fallback = [c for c in all_chunks if c in recent_chunks]
    random.shuffle(preferred)
    random.shuffle(fallback)
    selected = preferred[:max_chunks]
    if len(selected) < max_chunks:
        selected.extend(fallback[: max_chunks - len(selected)])
    return selected


def build_context(selected_chunks: List[str]) -> str:
    chunk_lookup = get_chunk_lookup()
    blocks = []
    for cid in selected_chunks:
        text = chunk_lookup.get(cid, "")
        if text:
            blocks.append(f"[{cid}]\n{text[:900]}")
    return "\n\n".join(blocks)


def is_semantically_duplicate(
    new_question: str,
    old_questions: List[str],
    threshold: float = SEMANTIC_DUPLICATE_THRESHOLD,
) -> Tuple[bool, float, Optional[str]]:
    if not old_questions:
        return False, 0.0, None

    try:
        new_vec = embed_query(new_question)
        old_vecs = np.array([embed_query(q) for q in old_questions], dtype=np.float32)

        # Cosine similarities via inner product
        sims = old_vecs @ new_vec
        max_idx = int(np.argmax(sims))
        max_score = float(sims[max_idx])
        most_sim_q = old_questions[max_idx]

        if max_score >= threshold:
            return True, max_score, most_sim_q
        return False, max_score, most_sim_q
    except Exception as e:
        logger.warning("Semantic duplicate check failed: %s", e)
        if FAIL_OPEN_ON_EMBEDDING_ERROR:
            return False, 0.0, None
        raise


def normalize_concept_weights(
    concept_weights: Any,
    primary_concept: str,
    allowed_concepts: List[str],
    fallback_secondary: Optional[List[str]] = None,
) -> Dict[str, float]:
    allowed_set = set(allowed_concepts)
    fallback_sec = normalize_concept_list(fallback_secondary)

    cleaned: Dict[str, float] = {}
    if isinstance(concept_weights, dict):
        for k, v in concept_weights.items():
            if isinstance(k, str) and k.strip() in allowed_set:
                try:
                    w = float(v)
                    if w > 0:
                        cleaned[k.strip()] = w
                except Exception:
                    continue

    if primary_concept not in cleaned:
        if not fallback_sec:
            return {primary_concept: 1.0}
        per_sec = round(0.30 / len(fallback_sec), 4)
        cleaned = {primary_concept: 0.70}
        for s in fallback_sec:
            cleaned[s] = per_sec

    total = sum(cleaned.values())
    if total <= 0:
        return {primary_concept: 1.0}

    norm = {c: round(w / total, 4) for c, w in cleaned.items()}
    primary_w = norm.get(primary_concept, 0.0)
    max_w = max(norm.values()) if norm else 0.0

    if primary_w < max_w:
        norm[primary_concept] = max_w + 0.05
        tot = sum(norm.values())
        norm = {c: round(w / tot, 4) for c, w in norm.items()}

    drift = round(1.0 - sum(norm.values()), 4)
    if drift != 0:
        norm[primary_concept] = round(norm[primary_concept] + drift, 4)

    return norm


def generate_question(
    concept_name: str,
    difficulty: str = "medium",
    asked_ids: Optional[Set[str]] = None,
    wrong_ids: Optional[Set[str]] = None,
    secondary_concepts: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    asked_set = set(asked_ids or [])
    wrong_set = set(wrong_ids or [])
    sec_concepts = normalize_concept_list(secondary_concepts)
    allowed_concepts = [concept_name] + [c for c in sec_concepts if c != concept_name]

    # 1. Reuse existing question if available
    existing_q = get_existing_question(
        concept_name, difficulty, asked_set, wrong_set, secondary_concepts=sec_concepts
    )
    if existing_q:
        return existing_q

    # 2. Retrieve grounded context
    retrieval_data = retrieve_context_for_concepts(
        primary_concept=concept_name, secondary_concepts=sec_concepts
    )
    if not retrieval_data or not retrieval_data.get("chunks"):
        logger.warning("Retrieval failed for concept: %s", concept_name)
        return None

    # 3. Select diverse chunks
    recent_q, recent_chunks = get_recent_metadata(
        concept_name, difficulty, limit=6, secondary_concepts=sec_concepts
    )
    style = choose_question_style(concept_name, difficulty, secondary_concepts=sec_concepts)
    selected_chunks = choose_diverse_chunks(list(retrieval_data["chunks"]), recent_chunks, max_chunks=4)
    if not selected_chunks:
        return None

    formatted_context = build_context(selected_chunks)
    if not formatted_context.strip():
        return None

    recent_q_text = "\n".join([f"- {q}" for q in recent_q[-5:]]) if recent_q else "None"

    prompt = PROMPT.format(
        primary_concept=concept_name,
        allowed_concepts=", ".join(allowed_concepts),
        difficulty=difficulty,
        question_style=style,
        recent_questions=recent_q_text,
        available_chunk_ids=", ".join(selected_chunks),
        context=formatted_context,
    )

    response = llm.get_response(prompt)
    clean_resp = response.strip()

    # Strip code block fences
    if "```" in clean_resp:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_resp)
        if m:
            clean_resp = m.group(1).strip()

    try:
        q_data = json.loads(clean_resp)
        if not isinstance(q_data, dict):
            return None

        # Validate required fields
        if "question" not in q_data or "options" not in q_data or "answer" not in q_data:
            return None

        options = q_data["options"]
        if not isinstance(options, list) or len(options) != 4:
            return None

        answer = str(q_data["answer"]).strip().upper()
        if answer not in ["A", "B", "C", "D"]:
            if any(answer == opt.strip()[:1].upper() for opt in options):
                answer = answer[0]
            else:
                answer = "A"
        q_data["answer"] = answer

        # Check semantic duplicate
        existing_texts = [
            q.get("question", "")
            for q in load_existing().get(build_question_key(concept_name, sec_concepts), {}).get(difficulty, [])
            if q.get("question")
        ]
        is_dup, _, _ = is_semantically_duplicate(q_data["question"], existing_texts)
        if is_dup:
            logger.info("Semantic duplicate rejected for %s", concept_name)
            return None

        # Sanitize source chunks
        src_chunks = [cid for cid in q_data.get("source_chunks", []) if cid in selected_chunks]
        if not src_chunks:
            src_chunks = selected_chunks[:2]
        q_data["source_chunks"] = src_chunks

        # Calculate cognitive weights
        norm_weights = normalize_concept_weights(
            concept_weights=q_data.get("concept_weights"),
            primary_concept=concept_name,
            allowed_concepts=allowed_concepts,
            fallback_secondary=sec_concepts,
        )
        q_data["concepts_covered"] = list(norm_weights.keys())
        q_data["concept_weights"] = norm_weights
        q_data["primary_concept"] = concept_name
        q_data["secondary_concepts"] = sec_concepts
        q_data["difficulty"] = difficulty
        if "explanation" not in q_data or not q_data["explanation"]:
            q_data["explanation"] = f"Grounded in textbook evidence for {concept_name}."

        existing_all = load_existing()
        q_id = generate_id(existing_all, concept_name, difficulty, secondary_concepts=sec_concepts)
        q_data["id"] = q_id

        save_mcq(concept_name, difficulty, q_data, secondary_concepts=sec_concepts)
        return q_data

    except Exception as e:
        logger.warning("Error parsing generated question JSON (%s): %s", e, clean_resp[:200])
        return None


if __name__ == "__main__":
    test_c = sys.argv[1] if len(sys.argv) > 1 else "Compiler"
    test_d = sys.argv[2] if len(sys.argv) > 2 else "medium"
    print(f"Generating {test_d} question for '{test_c}'...")
    res = generate_question(test_c, test_d)
    if res:
        print("\n--- GENERATED QUESTION ---")
        print(f"ID: {res['id']}")
        print(f"Stem: {res['question']}")
        for opt in res["options"]:
            print(f"  {opt}")
        print(f"Answer: {res['answer']}")
        print(f"Weights: {res['concept_weights']}")
        print(f"Explanation: {res.get('explanation')}")
    else:
        print("Failed to generate question.")
