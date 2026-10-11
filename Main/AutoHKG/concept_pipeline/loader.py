"""
loader.py — Loads content_chunks.json into memory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


def load_chunks(path: str | Path) -> List[Dict[str, Any]]:
    """
    Load a JSON file containing a list of chunk dicts.

    Each chunk must have at minimum:
        - chunk_id    : str
        - text        : str
        - page_number : int
        - book_name   : str  (optional but expected)

    Returns
    -------
    list[dict]
        Validated list of chunk dicts.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array at top level, got {type(data).__name__}")

    # Soft-validate and filter empty chunks
    valid: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = item.get("text", "").strip()
        if not text:
            continue
        valid.append(item)

    print(f"[loader] Loaded {len(valid)} non-empty chunks from '{path.name}'")
    return valid
