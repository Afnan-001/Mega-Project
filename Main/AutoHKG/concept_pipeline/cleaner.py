"""
cleaner.py — Text cleaning and PDF/publisher noise detection.
"""

from __future__ import annotations

import re
from typing import List


# ---------------------------------------------------------------------------
# Noise patterns — publisher / OCR / web boilerplate
# ---------------------------------------------------------------------------
_NOISE_PATTERNS: List[re.Pattern] = [
    re.compile(r"written\s+by\s+bookey", re.IGNORECASE),
    re.compile(r"check\s+more\s+about", re.IGNORECASE),
    re.compile(r"listen.*?audiobook", re.IGNORECASE),
    re.compile(r"about\s+the\s+(book|author)", re.IGNORECASE),
    re.compile(r"get\s+(the\s+)?full\s+(book|summary)", re.IGNORECASE),
    re.compile(r"bookey\s+app", re.IGNORECASE),
    re.compile(r"scan\s+(the\s+)?qr\s+code", re.IGNORECASE),
    re.compile(r"copyright\s+©", re.IGNORECASE),
    re.compile(r"all\s+rights\s+reserved", re.IGNORECASE),
    re.compile(r"isbn[\s\-]?\d[\d\-]{9,}", re.IGNORECASE),
    re.compile(r"printed\s+in", re.IGNORECASE),
    re.compile(r"visit\s+(us\s+at\s+)?www\.", re.IGNORECASE),
    re.compile(r"http[s]?://\S+"),
    re.compile(r"www\.\S+\.(com|org|net|edu)"),
    # Bibliography / reference lines: "[1] Author, Title, ..."
    re.compile(r"^\[\d+\]\s+[A-Z][a-z]+,", re.MULTILINE),
]

# Fragments that should be replaced with a space (inline noise)
_INLINE_REPLACEMENTS: List[tuple[re.Pattern, str]] = [
    # OCR page numbers "- 14 -" or "—14—"
    (re.compile(r"[-—]{1,2}\s*\d{1,4}\s*[-—]{1,2}"), " "),
    # Lone numbers on a line (page number artefacts)
    (re.compile(r"(?<!\w)\d{1,4}(?!\w)(?=\s|$)"), " "),
    # Repeated whitespace
    (re.compile(r"\s{2,}"), " "),
]

# Short chunks that are almost certainly header/footer noise
_MIN_MEANINGFUL_CHARS = 80


def clean_text(text: str) -> str:
    """
    Normalise a raw chunk text:
    - Rejoin hyphenated words across line breaks
    - Collapse newlines to spaces
    - Remove inline OCR / publisher noise
    - Normalise whitespace
    """
    # Rejoin words split by hyphen at linebreaks (e.g. proc-\n-essors -> processors)
    text = re.sub(r"([a-zA-Z]{2,})-\s*[\r\n]+\s*([a-zA-Z]{2,})", r"\1\2", text)

    # Strip control characters and unprintable bytes
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    # Collapse line breaks
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

    # Strip publisher / web / reference noise patterns inline
    for pattern in _NOISE_PATTERNS:
        text = pattern.sub(" ", text)

    # Apply inline replacements
    for pattern, repl in _INLINE_REPLACEMENTS[:-1]:   # skip whitespace collapse for now
        text = pattern.sub(repl, text)

    # Final whitespace normalisation
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def is_noise_chunk(text: str) -> bool:
    """
    Return True if the chunk is dominated by publisher / boilerplate noise
    and should be excluded from concept extraction.
    """
    if len(text.strip()) < _MIN_MEANINGFUL_CHARS:
        return True

    return False


def filter_noise_chunks(chunks: list[dict]) -> list[dict]:
    """
    Remove noise chunks in-place and return a cleaned list.
    Adds a `_cleaned_text` key to each surviving chunk.
    """
    kept = []
    dropped = 0
    for chunk in chunks:
        raw = chunk.get("text", "")
        cleaned = clean_text(raw)
        if is_noise_chunk(cleaned):
            dropped += 1
            continue
        chunk["_cleaned_text"] = cleaned
        kept.append(chunk)

    print(f"[cleaner] Kept {len(kept)} chunks, dropped {dropped} noise chunks")
    return kept
