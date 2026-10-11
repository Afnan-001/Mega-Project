"""
technical_terms.py — Detects technical abbreviations and domain-specific terms.

These are lifted regardless of their TF-IDF score because they are inherently
meaningful (SQL, ACID, 3NF, B-tree, 1:N, etc.).
"""

from __future__ import annotations

import re
from typing import Dict, List, Set


# ---------------------------------------------------------------------------
# Curated generic educational & technical seed terms
# ---------------------------------------------------------------------------
GENERIC_SEED_TERMS: Set[str] = {
    # CS, Systems & Architecture
    "API", "CPU", "RAM", "GPU", "IO", "OS", "SDK", "IDE", "GUI", "CLI",
    "HTTP", "HTTPS", "IP", "TCP", "UDP", "DNS", "URL", "URI", "JSON", "XML",
    "RAM", "ROM", "CACHE", "FIFO", "LIFO", "LRU", "ALU", "ISA", "DMA",
    # Data & Databases
    "SQL", "DDL", "DML", "ACID", "DBMS", "RDBMS", "NoSQL", "RDF",
    # Algorithms, Math & Complexity
    "O(N)", "Big-O", "NP-hard", "NP-complete", "DFS", "BFS", "Dijkstra",
    "binary search", "hash table", "linked list", "binary tree", "graph",
    "matrix", "vector", "eigenvalue", "eigenvector", "derivative", "integral",
    # Software & Compilers
    "AST", "IR", "lexer", "parser", "compiler", "interpreter", "assembler",
    "recursion", "iteration", "polymorphism", "inheritance", "encapsulation",
    "abstraction", "concurrency", "multithreading", "deadlock", "mutex",
}

# Backward compatibility alias
DBMS_SEED_TERMS: Set[str] = GENERIC_SEED_TERMS

# ---------------------------------------------------------------------------
# Regex patterns for technical abbreviations not in the seed list
# ---------------------------------------------------------------------------
_ABBREV_PATTERNS: List[re.Pattern] = [
    # Normal forms: 1NF, 2NF, 3NF, BCNF, 4NF …
    re.compile(r"\b(?:[1-9]|BC|DK)NF\b", re.IGNORECASE),
    # ALL-CAPS abbreviations 3–8 letters: SQL, XML, ACID, MVCC, RDBMS, BCNF …
    re.compile(r"\b[A-Z]{3,8}\b"),
    # Cardinality: 1:1, 1:N, M:N
    re.compile(r"\b[1MN]:[1MN]\b", re.IGNORECASE),
    # Versioned terms: B-tree, B+ tree, B* tree
    re.compile(r"\bB[+\*]?\s*[Tt]ree\b", re.IGNORECASE),
    # Numeric normal forms with degree: first normal form, second normal form …
    re.compile(r"\b(?:first|second|third|fourth|fifth|boyce[-\s]codd)\s+normal\s+form\b", re.IGNORECASE),
]

# Abbreviations to exclude even if ALL-CAPS (common English / PDF artefacts)
_EXCLUDED_ABBREVS: Set[str] = {
    "A", "I", "THE", "AND", "OR", "IN", "OF", "TO", "FOR", "IS", "IT",
    "BE", "AS", "AT", "BY", "AN", "ARE", "WAS", "HAS", "HAD", "NOT",
    "BUT", "ALL", "CAN", "ITS", "NEW", "ONE", "TWO", "USE", "GET",
    "SET", "LET", "NO", "DO", "SO", "UP", "IF", "ON", "AM", "US",
    "WE", "HE", "SHE", "MY", "HIS", "HER", "ANY", "MAY", "ALSO",
    "PAGE", "FIG", "TABLE", "NOTE", "SEE", "IBID", "ET", "AL",
    "CHAPTER", "SECTION", "FIGURE", "EXAMPLE", "EXERCISE", "PROBLEM",
    "APPENDIX", "REVIEW", "DEFINITION", "THEOREM", "PROOF", "LEMMA",
}


def detect_technical_terms(texts: List[str]) -> Dict[str, int]:
    """
    Scan all texts for technical abbreviations and domain-specific patterns.

    Returns
    -------
    dict[str, int]
        Raw matched term → occurrence count across all texts.
    """
    found: Dict[str, int] = {}

    combined = " ".join(texts)

    # First: scan for regex-based patterns
    for pattern in _ABBREV_PATTERNS:
        for m in pattern.finditer(combined):
            term = m.group(0).strip()
            if term.upper() in _EXCLUDED_ABBREVS:
                continue
            if len(term) < 2:
                continue
            key = term
            found[key] = found.get(key, 0) + 1

    # Second: check which seed terms actually appear in the corpus
    combined_lower = combined.lower()
    for seed in DBMS_SEED_TERMS:
        if seed.lower() in combined_lower:
            found[seed] = found.get(seed, combined_lower.count(seed.lower()))

    print(f"[technical_terms] Found {len(found)} technical term occurrences")
    return found
