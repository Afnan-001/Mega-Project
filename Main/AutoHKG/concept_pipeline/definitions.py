"""
definitions.py — Detects definition-pattern sentences in the corpus.

Sentences of the form:
    "X is a ..."          "X is defined as ..."
    "X refers to ..."     "A X is ..."
    "X is called ..."     "X is known as ..."

provide strong evidence that X is a domain concept.

Performance notes
-----------------
- All regexes use simple, non-backtracking patterns with bounded quantifiers.
- Each text is sentence-split first (on ". " boundaries), so regexes
  only run on short sentence fragments rather than full chunk texts.
- Subject capture is limited to 1-6 words with a strict character class.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Max characters of a sentence to feed into regex (avoids long-line blowup)
_MAX_SENT_CHARS = 300

# Simple sentence splitter — split on ". " or ".\n"
_SENT_SPLIT = re.compile(r"\.[\s\n]+")

# ---------------------------------------------------------------------------
# Definition patterns — all use bounded {1,6} quantifiers, no .*
# ---------------------------------------------------------------------------
# Subject pattern: 1-6 words composed of letters, digits, hyphens, slashes
_SUBJ = r"([A-Za-z][A-Za-z0-9\-/]*(?: [A-Za-z][A-Za-z0-9\-/]*){0,5})"

_DEF_PATTERNS: List[re.Pattern] = [
    # "X is defined as / called / known as / referred to as"
    re.compile(
        _SUBJ + r"\s+(?:is|are)\s+(?:defined\s+as|called|known\s+as|referred\s+to\s+as)\b",
        re.IGNORECASE,
    ),
    # "X refers to"
    re.compile(
        _SUBJ + r"\s+refers?\s+to\b",
        re.IGNORECASE,
    ),
    # "A X is a/an/the ..." — term after article, before "is"
    re.compile(
        r"\b[Aa]n?\s+" + _SUBJ + r"\s+is\s+(?:a|an|the)\b",
        re.IGNORECASE,
    ),
    # "The X is a/an ..."
    re.compile(
        r"\bThe\s+" + _SUBJ + r"\s+is\s+(?:a|an)\b",
    ),
    # "X is a <word>" — subject before "is a"
    re.compile(
        _SUBJ + r"\s+is\s+(?:a|an)\s+[A-Za-z]",
        re.IGNORECASE,
    ),
]

# Words that are not domain concepts even if they match
_STOPWORDS = {
    "a", "an", "the", "this", "that", "it", "he", "she", "they",
    "we", "there", "here", "which", "what", "its", "i", "you",
    "one", "some", "any", "each", "both", "all", "most",
    "ability", "above", "after", "again", "age", "ago",
    "already", "another", "approach", "area", "around",
    "base", "basis", "before", "begin", "below", "between",
    "break", "bring", "build", "call", "change", "choose",
    "come", "consider", "contain", "control", "cost", "create",
}

_MIN_LEN   = 3
_MAX_WORDS = 6


def _valid_term(term: str) -> bool:
    term = term.strip()
    if len(term) < _MIN_LEN:
        return False
    words = term.lower().split()
    if not words or words[0] in _STOPWORDS:
        return False
    if len(words) == 1 and words[0] in _STOPWORDS:
        return False
    if len(words) > _MAX_WORDS:
        return False
    if not any(c.isalpha() for c in term):
        return False
    return True


def detect_definitions(texts: List[str]) -> Dict[str, int]:
    """
    Find phrases that appear as subjects of definition-style sentences.

    Splits each chunk into sentences first, then applies bounded regexes
    only to short sentences — avoids catastrophic backtracking.

    Returns
    -------
    dict[str, int]
        lowercased defined term → number of occurrences
    """
    defined: Dict[str, int] = {}

    for text in texts:
        # Split into individual sentences (fast, no regex)
        sentences = _SENT_SPLIT.split(text)

        for sent in sentences:
            sent = sent.strip()
            if len(sent) < _MIN_LEN:
                continue
            # Hard cap per sentence to prevent slow regex on run-on text
            if len(sent) > _MAX_SENT_CHARS:
                sent = sent[:_MAX_SENT_CHARS]

            for pattern in _DEF_PATTERNS:
                m = pattern.search(sent)
                if m:
                    term = m.group(1).strip()
                    if _valid_term(term):
                        key = term.lower().strip()
                        defined[key] = defined.get(key, 0) + 1
                    # Only take first match per sentence per pattern
                    break

    print(f"[definitions] Found {len(defined)} definition-pattern terms")
    return defined
