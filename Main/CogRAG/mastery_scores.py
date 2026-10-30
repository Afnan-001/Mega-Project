"""
mastery_scores.py — Initializes and manages baseline Bayesian Knowledge Tracing (BKT) mastery profiles.
Aligns with both CLI execution and server database schema.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

DATA_DIR = MAIN_DIR / "outputs" / "data"
MASTERY_FILE = DATA_DIR / "mastery_scores.json"

# Candidate concept files in order of DAG refinement
CONCEPT_FILE_CANDIDATES = [
    DATA_DIR / "cleaned_enriched_concepts.json",
    DATA_DIR / "enriched_concepts_dag.json",
    DATA_DIR / "enriched_concepts.json",
    DATA_DIR / "mapped_concepts.json",
    DATA_DIR / "clean_concepts.json",
]

# Standard BKT initial prior: P(L_0) = 0.10
DEFAULT_INITIAL_P_KNOW = float(os.getenv("BKT_INITIAL_P_KNOW", "0.10"))


def resolve_concepts_file() -> Path:
    for candidate in CONCEPT_FILE_CANDIDATES:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return CONCEPT_FILE_CANDIDATES[2]


def load_concepts(concepts_file: Path | None = None) -> List[str]:
    target = concepts_file or resolve_concepts_file()
    if not target.exists():
        raise FileNotFoundError(f"Concepts file not found: {target}")

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    concepts: List[str] = []
    if isinstance(data, dict) and "concepts" in data:
        concepts = [c.strip() for c in data["concepts"] if isinstance(c, str) and c.strip()]
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "concept" in item:
                c = item["concept"]
                if isinstance(c, str) and c.strip():
                    concepts.append(c.strip())
            elif isinstance(item, str) and item.strip():
                concepts.append(item.strip())

    # Deduplicate while preserving order
    seen = set()
    unique_concepts = []
    for c in concepts:
        if c not in seen:
            seen.add(c)
            unique_concepts.append(c)

    return unique_concepts


def create_initial_mastery(
    concepts: List[str],
    initial_p_know: float = DEFAULT_INITIAL_P_KNOW,
) -> Dict[str, Dict[str, Any]]:
    mastery_data: Dict[str, Dict[str, Any]] = {}
    for concept in concepts:
        mastery_data[concept] = {
            "p_know": round(float(initial_p_know), 4),
            "confidence": 0.0,
            "questions_attempted": 0,
            "correct_answers": 0,
            "recent_answers": [],
            "asked_question_ids": [],
            "wrong_question_ids": [],
        }
    return mastery_data


def save_mastery(data: Dict[str, Any], output_path: Path | None = None) -> None:
    target = output_path or MASTERY_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✅ Saved mastery profile for {len(data)} concepts to: {target}")


def initialize_mastery_profile(force: bool = False) -> Dict[str, Any]:
    if MASTERY_FILE.exists() and not force:
        try:
            with open(MASTERY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                return data
        except Exception:
            pass

    concepts = load_concepts()
    mastery_data = create_initial_mastery(concepts)
    save_mastery(mastery_data)
    return mastery_data


if __name__ == "__main__":
    concepts = load_concepts()
    print(f"Loaded {len(concepts)} concepts.")
    mastery = create_initial_mastery(concepts)
    save_mastery(mastery)
