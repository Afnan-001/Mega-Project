"""
saver.py — Writes concepts.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict


def save_concepts(concepts: List[str], output_path: str | Path) -> None:
    """
    Write the final concepts list to a JSON file.

    Output format:
    {
        "concepts": ["...", "..."]
    }
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"concepts": concepts}

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=4, ensure_ascii=False)

    print(f"[saver] OK: Wrote {len(concepts)} concepts -> {output_path}")
