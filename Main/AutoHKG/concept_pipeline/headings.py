"""
headings.py — Detects chapter/section headings and ToC entries.

Headings act as ground-truth concept signals: if "Query Optimization"
is a chapter title, "query optimization" must be a concept.
"""

from __future__ import annotations

import re
from typing import List, Dict, Set


# ---------------------------------------------------------------------------
# Heading detection regexes
# ---------------------------------------------------------------------------
_CHAPTER_RE = re.compile(
    r"chapter\s+\d+[\.:–\-]?\s*(.+)",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(
    r"(?:section|part|unit|module)\s+[\d\.]+[\.:–\-]?\s*(.+)",
    re.IGNORECASE,
)
# Numbered section e.g. "8.3 Query Optimization"
_NUMBERED_SECTION_RE = re.compile(
    r"^\d+(?:\.\d+){1,3}\s+([A-Z][A-Za-z0-9 '\-]{4,80})$",
    re.MULTILINE,
)
# ALL-CAPS short lines (likely headings)
_ALL_CAPS_RE = re.compile(
    r"^([A-Z][A-Z\s\-]{4,60})$",
    re.MULTILINE,
)

# Known boilerplate heading words to exclude
_BOILERPLATE_HEADINGS: Set[str] = {
    "about the book", "about the author", "contents", "table of contents",
    "preface", "acknowledgements", "bibliography", "references", "index",
    "appendix", "introduction", "summary", "exercises", "problems",
    "review questions", "further reading", "notes", "glossary",
}


def _clean_heading(raw: str) -> str:
    """Strip trailing punctuation, page numbers and normalise."""
    raw = re.sub(r"\s*\.\s*\d+\s*$", "", raw)   # remove "....... 42"
    raw = re.sub(r"[\.]{3,}", "", raw)            # remove dot leaders
    raw = raw.strip(" .:–-")
    return raw.strip()


def extract_headings(texts: List[str]) -> Dict[str, int]:
    """
    Scan all chunk texts for chapter/section headings.

    Returns
    -------
    dict[str, int]
        Mapping of lowercased heading phrase → occurrence count.
        The caller will use these as high-weight concept signals.
    """
    heading_counts: Dict[str, int] = {}

    for text in texts:
        # Chapter headings
        for m in _CHAPTER_RE.finditer(text):
            h = _clean_heading(m.group(1))
            if h and len(h) > 3:
                _add(heading_counts, h)

        # Named section headings
        for m in _SECTION_RE.finditer(text):
            h = _clean_heading(m.group(1))
            if h and len(h) > 3:
                _add(heading_counts, h)

        # Numbered sections
        for m in _NUMBERED_SECTION_RE.finditer(text):
            h = _clean_heading(m.group(1))
            if h and len(h) > 3:
                _add(heading_counts, h)

        # ALL-CAPS lines (potential headings)
        for m in _ALL_CAPS_RE.finditer(text):
            h = m.group(1).strip().lower()
            if h and len(h) > 3 and h not in _BOILERPLATE_HEADINGS:
                _add(heading_counts, h)

    # Remove boilerplate
    heading_counts = {
        k: v for k, v in heading_counts.items()
        if k not in _BOILERPLATE_HEADINGS and len(k.split()) >= 1
    }

    print(f"[headings] Detected {len(heading_counts)} unique heading phrases")
    return heading_counts


def _add(d: Dict[str, int], key: str) -> None:
    key = key.lower().strip()
    d[key] = d.get(key, 0) + 1
