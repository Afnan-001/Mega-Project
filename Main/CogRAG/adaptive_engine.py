"""
adaptive_engine.py — Graph-aware Adaptive Learning & Bayesian Knowledge Tracing (BKT) Engine.
Coordinates student learning paths, prerequisite remediation, difficulty modulation, and cognitive mastery updates.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("corgag.adaptive_engine")

CURRENT_DIR = Path(__file__).resolve().parent
MAIN_DIR = CURRENT_DIR.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from confidence import compute_confidence
from question_generator import generate_question
from retriever import get_graph

OUTPUTS_DIR = MAIN_DIR / "outputs"
DATA_DIR = OUTPUTS_DIR / "data"

MASTERY_FILE = DATA_DIR / "mastery_scores.json"
NAVIGATION_STATE_FILE = DATA_DIR / "navigation_state.json"

# Standard BKT Hyperparameters
P_G = float(os.getenv("BKT_P_G", "0.25"))      # Guess probability
P_S = float(os.getenv("BKT_P_S", "0.10"))      # Slip probability
P_T = float(os.getenv("BKT_P_T", "0.15"))      # Learning transition probability
P_L0 = float(os.getenv("BKT_P_L0", "0.10"))    # Initial prior mastery

# Navigation & Mastery Thresholds
MASTERY_THRESHOLD = 0.85
WEAK_THRESHOLD = 0.40
RECENT_WINDOW = 5
MAX_PREREQ_CANDIDATES_FOR_LLM = 4

# Confidence Estimation Settings
RECENT_ANSWERS_WINDOW = 10
CONFIDENCE_HIGH_THRESHOLD = 0.75
CONFIDENCE_LOW_THRESHOLD = 0.25
ATTEMPT_CONFIDENCE_WEIGHT = 0.5
CONSISTENCY_CONFIDENCE_WEIGHT = 0.5
ATTEMPT_SATURATION_RATE = 0.35
MIN_ATTEMPTS_FOR_CONFIDENCE = 6


def load_mastery() -> Dict[str, Dict[str, Any]]:
    if not MASTERY_FILE.exists():
        return {}
    try:
        with open(MASTERY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_mastery(data: Dict[str, Any]) -> None:
    MASTERY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MASTERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def normalize_recent_answers(recent_answers: List[Any]) -> List[int]:
    if not isinstance(recent_answers, list):
        return []
    cleaned = []
    for item in recent_answers:
        if item in (0, 1):
            cleaned.append(int(item))
        elif isinstance(item, bool):
            cleaned.append(int(item))
        elif isinstance(item, (int, float)):
            cleaned.append(1 if item >= 0.5 else 0)
    return cleaned[-RECENT_ANSWERS_WINDOW:]


def ensure_mastery_entry(entry: Any) -> Dict[str, Any]:
    base = {
        "p_know": P_L0,
        "confidence": 0.0,
        "questions_attempted": 0,
        "correct_answers": 0,
        "recent_answers": [],
        "asked_question_ids": [],
        "wrong_question_ids": [],
    }
    if not isinstance(entry, dict):
        entry = {}

    merged = {**base, **entry}
    try:
        merged["p_know"] = max(0.001, min(0.999, float(merged.get("p_know", P_L0))))
    except Exception:
        merged["p_know"] = P_L0

    merged["questions_attempted"] = max(0, int(merged.get("questions_attempted", 0)))
    merged["correct_answers"] = max(0, min(merged["questions_attempted"], int(merged.get("correct_answers", 0))))
    merged["asked_question_ids"] = [qid for qid in merged.get("asked_question_ids", []) if isinstance(qid, str) and qid]
    merged["wrong_question_ids"] = [qid for qid in merged.get("wrong_question_ids", []) if isinstance(qid, str) and qid]
    merged["recent_answers"] = normalize_recent_answers(merged.get("recent_answers", []))

    merged["confidence"] = compute_confidence(
        questions_attempted=merged["questions_attempted"],
        recent_answers=merged["recent_answers"],
        attempt_weight=ATTEMPT_CONFIDENCE_WEIGHT,
        consistency_weight=CONSISTENCY_CONFIDENCE_WEIGHT,
        saturation_rate=ATTEMPT_SATURATION_RATE,
        min_attempts_for_reliability=MIN_ATTEMPTS_FOR_CONFIDENCE,
    )
    return merged


def get_confidence_level(confidence: float) -> str:
    if confidence >= CONFIDENCE_HIGH_THRESHOLD:
        return "high"
    if confidence <= CONFIDENCE_LOW_THRESHOLD:
        return "low"
    return "moderate"


# ----------------------------
# Navigation State Management
# ----------------------------
def load_navigation_state() -> Dict[str, Any]:
    if NAVIGATION_STATE_FILE.exists():
        try:
            with open(NAVIGATION_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"current_concept": None, "return_target": None, "recent_concepts": []}


def save_navigation_state(state: Dict[str, Any]) -> None:
    NAVIGATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cleaned_recent = [c.strip() for c in state.get("recent_concepts", []) if isinstance(c, str) and c.strip()]
    payload = {
        "current_concept": state.get("current_concept"),
        "return_target": state.get("return_target"),
        "recent_concepts": cleaned_recent[-RECENT_WINDOW:],
    }
    with open(NAVIGATION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def get_current_concept() -> Optional[str]:
    return load_navigation_state().get("current_concept")


def set_current_concept(concept: Optional[str]) -> None:
    state = load_navigation_state()
    state["current_concept"] = concept
    save_navigation_state(state)


def get_return_target() -> Optional[str]:
    return load_navigation_state().get("return_target")


def set_return_target(concept: Optional[str]) -> None:
    state = load_navigation_state()
    state["return_target"] = concept
    save_navigation_state(state)


def clear_return_target() -> None:
    state = load_navigation_state()
    state["return_target"] = None
    save_navigation_state(state)


def push_recent_concept(concept: str) -> None:
    state = load_navigation_state()
    history = state.get("recent_concepts", [])
    history.append(concept)
    state["recent_concepts"] = history
    save_navigation_state(state)


def get_recent_history() -> List[str]:
    return load_navigation_state().get("recent_concepts", [])


def get_mastery(concept: str) -> Dict[str, Any]:
    data = load_mastery()
    data[concept] = ensure_mastery_entry(data.get(concept, {}))
    save_mastery(data)
    return data[concept]


# ----------------------------
# Graph Traversal Helpers
# ----------------------------
def get_root_concepts(graph: nx.DiGraph | None = None) -> List[str]:
    G = graph or get_graph()
    roots = []
    for node in G.nodes():
        incoming = [src for src, _, d in G.in_edges(node, data=True) if d.get("relation") == "PREREQUISITE_FOR"]
        if len(incoming) == 0:
            roots.append(node)
    return roots


def get_prerequisite_nodes(concept: str, graph: nx.DiGraph | None = None) -> List[str]:
    G = graph or get_graph()
    if concept not in G:
        return []
    return [src for src, _, d in G.in_edges(concept, data=True) if d.get("relation") == "PREREQUISITE_FOR"]


def get_successor_nodes(concept: str, graph: nx.DiGraph | None = None) -> List[str]:
    G = graph or get_graph()
    if concept not in G:
        return []
    return [dst for _, dst, d in G.out_edges(concept, data=True) if d.get("relation") == "PREREQUISITE_FOR"]


def get_successor_candidates(concept: str, graph: nx.DiGraph | None = None) -> List[Dict[str, Any]]:
    G = graph or get_graph()
    if concept not in G:
        return []
    candidates = []
    for _, dst, edge_data in G.out_edges(concept, data=True):
        if edge_data.get("relation") == "PREREQUISITE_FOR":
            conf = edge_data.get("confidence", 0.60)
            try:
                conf = float(conf)
            except Exception:
                conf = 0.60
            candidates.append({"concept": dst, "edge_confidence": conf})
    return candidates


def select_preferred_successor(successor_candidates: List[Dict[str, Any]], data: Dict[str, Any]) -> Optional[str]:
    if not successor_candidates:
        return None
    recent = set(get_recent_history())
    unmastered = [
        item for item in successor_candidates
        if item["concept"] in data and data[item["concept"]]["p_know"] < MASTERY_THRESHOLD
    ]
    if not unmastered:
        return None

    # Rank by: not recent, highest confidence edge, lowest mastery
    unmastered.sort(
        key=lambda item: (
            1 if item["concept"] in recent else 0,
            -item["edge_confidence"],
            data[item["concept"]]["p_know"],
        )
    )
    return unmastered[0]["concept"]


def get_difficulty(concept: str) -> str:
    p = get_mastery(concept)["p_know"]
    if p < WEAK_THRESHOLD:
        return "easy"
    if p < MASTERY_THRESHOLD:
        return "medium"
    return "hard"


def weakest_unmastered(concepts: List[str], data: Dict[str, Any], exclude_recent: bool = True) -> Optional[str]:
    recent = set(get_recent_history()) if exclude_recent else set()
    candidates = [
        c for c in concepts
        if c in data and data[c]["p_know"] < MASTERY_THRESHOLD and c not in recent
    ]
    if not candidates:
        candidates = [c for c in concepts if c in data and data[c]["p_know"] < MASTERY_THRESHOLD]
    if not candidates:
        return None
    return min(candidates, key=lambda c: data[c]["p_know"])


def global_fallback_concept(data: Dict[str, Any]) -> str:
    roots = get_root_concepts()
    root_choice = weakest_unmastered(roots, data, exclude_recent=True)
    if root_choice:
        return root_choice

    all_concepts = list(data.keys())
    unmastered = weakest_unmastered(all_concepts, data, exclude_recent=True)
    if unmastered:
        return unmastered

    if all_concepts:
        return min(all_concepts, key=lambda c: data[c]["p_know"])
    return "Concept"


def select_secondary_concepts(primary_concept: str, data: Dict[str, Any]) -> List[str]:
    unmastered_prereqs = [
        c for c in get_prerequisite_nodes(primary_concept)
        if c in data and c != primary_concept and data[c]["p_know"] < MASTERY_THRESHOLD
    ]
    unmastered_prereqs.sort(key=lambda c: data[c]["p_know"])
    return unmastered_prereqs[:MAX_PREREQ_CANDIDATES_FOR_LLM]


# ----------------------------
# Concept Selection Policy
# ----------------------------
def select_next_concept() -> str:
    data = load_mastery()
    if not data:
        # Initialize from graph if empty
        G = get_graph()
        data = {node: ensure_mastery_entry({}) for node in G.nodes()}
        save_mastery(data)

    current = get_current_concept()
    return_target = get_return_target()

    # 1. First run / uninitialized
    if not current or current not in data:
        start = global_fallback_concept(data)
        set_current_concept(start)
        clear_return_target()
        push_recent_concept(start)
        return start

    # 2. Return-target remediation mode
    if return_target and return_target in data:
        target_prereqs = get_prerequisite_nodes(return_target)
        unmastered_target = [c for c in target_prereqs if c in data and data[c]["p_know"] < MASTERY_THRESHOLD]
        if not unmastered_target:
            clear_return_target()
            set_current_concept(return_target)
            push_recent_concept(return_target)
            return return_target

        if current in unmastered_target:
            set_current_concept(current)
            push_recent_concept(current)
            return current

        next_prereq = weakest_unmastered(unmastered_target, data, exclude_recent=True)
        if next_prereq:
            set_current_concept(next_prereq)
            push_recent_concept(next_prereq)
            return next_prereq

    current_entry = data[current]
    current_p = current_entry["p_know"]

    # 3. Weak concept -> remediate to weak prerequisite
    if current_p <= WEAK_THRESHOLD:
        unmastered_preds = [
            c for c in get_prerequisite_nodes(current)
            if c in data and data[c]["p_know"] < MASTERY_THRESHOLD
        ]
        next_concept = weakest_unmastered(unmastered_preds, data, exclude_recent=True)
        if next_concept:
            set_return_target(current)
            set_current_concept(next_concept)
            push_recent_concept(next_concept)
            return next_concept

        set_current_concept(current)
        push_recent_concept(current)
        return current

    # 4. Mastered concept -> advance along prerequisite edge
    if current_p >= MASTERY_THRESHOLD:
        succ_candidates = get_successor_candidates(current)
        next_succ = select_preferred_successor(succ_candidates, data)
        if next_succ:
            set_current_concept(next_succ)
            push_recent_concept(next_succ)
            return next_succ

        fallback = global_fallback_concept(data)
        set_current_concept(fallback)
        clear_return_target()
        push_recent_concept(fallback)
        return fallback

    # 5. Moderate mastery -> practice current concept
    set_current_concept(current)
    push_recent_concept(current)
    return current


# ----------------------------
# Question Orchestration
# ----------------------------
def get_adaptive_question() -> Dict[str, Any]:
    concept = select_next_concept()
    difficulty = get_difficulty(concept)
    data = load_mastery()

    secondary_concepts = select_secondary_concepts(concept, data)
    mastery_data = get_mastery(concept)

    asked_ids = set(mastery_data.get("asked_question_ids", []))
    wrong_ids = set(mastery_data.get("wrong_question_ids", []))

    q = generate_question(
        concept_name=concept,
        difficulty=difficulty,
        asked_ids=asked_ids,
        wrong_ids=wrong_ids,
        secondary_concepts=secondary_concepts,
    )

    return {
        "concept": concept,
        "difficulty": difficulty,
        "secondary_concepts": secondary_concepts,
        "concepts_covered": q.get("concepts_covered", [concept]) if q else [concept],
        "concept_weights": q.get("concept_weights", {concept: 1.0}) if q else {concept: 1.0},
        "question": q,
    }


# ----------------------------
# BKT Latent Mastery Update
# ----------------------------
def update_mastery_multi(
    concepts: List[str],
    question_id: Optional[str],
    correct: bool,
    concept_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    data = load_mastery()
    concept_weights = concept_weights or {}
    updated_records: Dict[str, Any] = {}

    for concept in concepts:
        entry = ensure_mastery_entry(data.get(concept, {}))
        weight = float(concept_weights.get(concept, 1.0))
        weight = max(0.0, min(1.0, weight))

        p = entry["p_know"]
        if correct:
            numerator = p * (1.0 - P_S)
            denominator = numerator + (1.0 - p) * P_G
        else:
            numerator = p * P_S
            denominator = numerator + (1.0 - p) * (1.0 - P_G)

        posterior = p if denominator <= 0 else (numerator / denominator)
        p_new = posterior + (1.0 - posterior) * P_T

        # Scale update magnitude by cognitive weight
        weighted_p = p + weight * (p_new - p)
        entry["p_know"] = round(max(0.01, min(0.99, weighted_p)), 4)

        entry["questions_attempted"] += 1
        if correct:
            entry["correct_answers"] += 1

        if question_id:
            if question_id not in entry["asked_question_ids"]:
                entry["asked_question_ids"].append(question_id)
            if correct and question_id in entry["wrong_question_ids"]:
                entry["wrong_question_ids"].remove(question_id)
            elif not correct and question_id not in entry["wrong_question_ids"]:
                entry["wrong_question_ids"].append(question_id)

        entry["recent_answers"].append(1 if correct else 0)
        entry["recent_answers"] = normalize_recent_answers(entry["recent_answers"])

        entry["confidence"] = compute_confidence(
            questions_attempted=entry["questions_attempted"],
            recent_answers=entry["recent_answers"],
            attempt_weight=ATTEMPT_CONFIDENCE_WEIGHT,
            consistency_weight=CONSISTENCY_CONFIDENCE_WEIGHT,
            saturation_rate=ATTEMPT_SATURATION_RATE,
            min_attempts_for_reliability=MIN_ATTEMPTS_FOR_CONFIDENCE,
        )

        data[concept] = entry
        updated_records[concept] = {**entry, "update_weight": round(weight, 4)}

    save_mastery(data)
    return updated_records


def process_answer(concept: str, question_data: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    expected = str(question_data.get("answer", "")).strip().upper()
    user_resp = str(user_answer).strip().upper()

    # Match A/B/C/D or option text
    correct = (user_resp == expected) or (user_resp.startswith(expected + ".") or user_resp.startswith(expected + ")"))

    concepts_covered = question_data.get("concepts_covered", [concept])
    concept_weights = question_data.get("concept_weights", {c: 1.0 for c in concepts_covered})

    updates = update_mastery_multi(
        concepts=concepts_covered,
        question_id=question_data.get("id"),
        correct=correct,
        concept_weights=concept_weights,
    )

    primary = question_data.get("primary_concept", concept)
    mastery_info = updates.get(primary, next(iter(updates.values()), {}))

    return {
        "correct": correct,
        "expected_answer": expected,
        "explanation": question_data.get("explanation", ""),
        "mastery": mastery_info,
        "mastery_updates": updates,
        "concepts_covered": concepts_covered,
        "concept_weights": concept_weights,
    }


def get_mastered_concepts() -> List[str]:
    return [c for c, v in load_mastery().items() if v.get("p_know", 0) >= MASTERY_THRESHOLD]


def get_weak_concepts() -> List[str]:
    return [c for c, v in load_mastery().items() if v.get("p_know", 0) <= WEAK_THRESHOLD]


def get_overall_progress() -> float:
    data = load_mastery()
    if not data:
        return 0.0
    avg = sum(v.get("p_know", 0.1) for v in data.values()) / len(data)
    return round(avg * 100, 2)


# ----------------------------
# Interactive CLI Learner Loop
# ----------------------------
def interactive_session():
    print("=" * 60)
    print("  AutoHKG / Cognitive-RAG Adaptive Student Session")
    print("=" * 60)
    print(f"Overall Progress: {get_overall_progress()}%")

    while True:
        payload = get_adaptive_question()
        q = payload.get("question")
        if not q:
            print("⚠️ No question generated. Retrying or exiting.")
            break

        print("\n" + "-" * 50)
        print(f"Target Concept: {payload['concept']} (Difficulty: {payload['difficulty']})")
        print(f"Question ID: {q.get('id')}")
        print(f"\n{q.get('question')}\n")
        for opt in q.get("options", []):
            print(f"  {opt}")

        user_input = input("\nEnter your answer (A/B/C/D) or 'q' to quit: ").strip()
        if user_input.lower() == "q":
            print("\nSession ended. Progress saved.")
            break

        result = process_answer(payload["concept"], q, user_input)
        if result["correct"]:
            print("🎉 CORRECT!")
        else:
            print(f"❌ INCORRECT. Correct answer was: {result['expected_answer']}")

        if result.get("explanation"):
            print(f"Explanation: {result['explanation']}")

        print(f"Updated P(Mastery) for {payload['concept']}: {result['mastery'].get('p_know') * 100:.1f}%")
        print(f"Overall Progress: {get_overall_progress()}%")


if __name__ == "__main__":
    if "--interactive" in sys.argv:
        interactive_session()
    else:
        print("Sampling next adaptive question...")
        adaptive_q = get_adaptive_question()
        if adaptive_q.get("question"):
            print(f"Concept: {adaptive_q['concept']}")
            print(f"Question: {adaptive_q['question']['question']}")
            print(f"Options: {adaptive_q['question']['options']}")
            print(f"Correct: {adaptive_q['question']['answer']}")
        else:
            print("No question generated.")
