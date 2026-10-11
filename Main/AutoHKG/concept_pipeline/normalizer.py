"""
normalizer.py — Normalizes candidate concepts and merges variant forms.

Strategy
--------
1.  Compute a canonical key: lowercase → strip hyphens/dots → collapse spaces.
2.  Group all raw forms that share the same canonical key.
3.  Pick the best display form from the group using a priority order:
      a. Known capitalization from CAP_MAP (highest priority)
      b. Curated seed term from technical_terms.GENERIC_SEED_TERMS
      c. Raw form with the highest frequency in the corpus
      d. Title-cased fallback
4.  Do NOT stem or lemmatize technical abbreviations.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Known canonical capitalisations
# ---------------------------------------------------------------------------
CAP_MAP: Dict[str, str] = {
    # Abbreviations
    "sql": "SQL",
    "ddl": "DDL",
    "dml": "DML",
    "dcl": "DCL",
    "tcl": "TCL",
    "nosql": "NoSQL",
    "newql": "NewQL",
    "xml": "XML",
    "json": "JSON",
    "rdf": "RDF",
    "owl": "OWL",
    "html": "HTML",
    "acid": "ACID",
    "mvcc": "MVCC",
    "dbms": "DBMS",
    "rdbms": "RDBMS",
    "oodbms": "OODBMS",
    "ordbms": "ORDBMS",
    "olap": "OLAP",
    "oltp": "OLTP",
    "etl": "ETL",
    "wal": "WAL",
    "isam": "ISAM",
    "2pl": "2PL",
    "orm": "ORM",
    # Normal forms
    "1nf": "1NF",
    "2nf": "2NF",
    "3nf": "3NF",
    "4nf": "4NF",
    "5nf": "5NF",
    "6nf": "6NF",
    "bcnf": "BCNF",
    "boyce codd normal form": "BCNF",
    "boyce-codd normal form": "BCNF",
    "dknf": "DKNF",
    "3nf synthesis": "3NF Synthesis",
    # Trees & Indexing
    "b tree": "B-tree",
    "b-tree": "B-tree",
    "btree": "B-tree",
    "b+ tree": "B+ tree",
    "b+tree": "B+ tree",
    "b* tree": "B* tree",
    "indexing": "indexing",
    # Models & Relationships
    "er model": "ER model",
    "e r model": "ER model",
    "e-r model": "ER model",
    "eer model": "EER model",
    "entity relationship": "entity relationship",
    "entity relationship model": "entity-relationship model",
    "1 1 relationship": "1:1 relationship",
    "1 n relationship": "1:N relationship",
    "m n relationship": "M:N relationship",
    "1:1 relationship": "1:1 relationship",
    "1:n relationship": "1:N relationship",
    "m:n relationship": "M:N relationship",
    # ANSI
    "ansi sparc": "ANSI/SPARC",
    "ansi/sparc": "ANSI/SPARC",
    "pl sql": "PL/SQL",
    "pl/sql": "PL/SQL",
    "t sql": "T-SQL",
    "t-sql": "T-SQL",
}


def singularize_word(word: str) -> str:
    """Basic English singularization for noun phrase canonical keys."""
    if len(word) <= 3:
        return word
    w_lower = word.lower()
    # Irregular / common technical exceptions
    exceptions = {
        "status": "status", "bus": "bus", "class": "class", "process": "process",
        "access": "access", "address": "address", "alias": "alias", "analysis": "analysis",
        "basis": "basis", "canvas": "canvas", "index": "index", "matrices": "matrix",
        "automata": "automaton", "data": "data", "criteria": "criterion", "queries": "query",
        "entities": "entity", "dependencies": "dependency", "dictionaries": "dictionary",
        "trees": "tree", "axes": "axis", "indices": "index"
    }
    if w_lower in exceptions:
        return exceptions[w_lower]

    if w_lower.endswith("ies") and len(w_lower) > 4:
        return w_lower[:-3] + "y"
    if w_lower.endswith("ses") and not w_lower.endswith("asses"):
        return w_lower[:-2]
    if w_lower.endswith("xes") or w_lower.endswith("ches") or w_lower.endswith("shes"):
        return w_lower[:-2]
    if w_lower.endswith("s") and not w_lower.endswith("ss") and not w_lower.endswith("us") and not w_lower.endswith("is"):
        return w_lower[:-1]
    return word


def _canonical_key(phrase: str) -> str:
    """
    Compute a normalised merge key.
    Lowercases, replaces hyphens/slashes/dots with spaces,
    strips punctuation, collapses whitespace, and singularizes final word.
    """
    key = phrase.lower()
    key = re.sub(r"[/\-]", " ", key)          # hyphens & slashes → space
    key = re.sub(r"[^\w\s\:\+\*]", "", key)   # remove punctuation (keep : + *)
    key = re.sub(r"\s{2,}", " ", key).strip()

    tokens = key.split()
    if tokens:
        tokens[-1] = singularize_word(tokens[-1])
        key = " ".join(tokens)
    return key


def _best_display_form(canonical: str, raw_forms: List[Tuple[str, int]]) -> str:
    """
    Choose the best human-readable display form for a concept.

    Priority:
    1. CAP_MAP entry
    2. The raw form with maximum frequency
    3. Title-case of the canonical key
    """
    # 1. Check CAP_MAP
    if canonical in CAP_MAP:
        return CAP_MAP[canonical]

    # 2. Highest-frequency raw form
    if raw_forms:
        best = max(raw_forms, key=lambda t: t[1])[0]
        # If it looks like an abbreviation (all upper), keep it
        if best.isupper() and len(best) <= 8:
            return best
        return best

    # 3. Title-case fallback
    return canonical.title()


def normalize_concept(phrase: str) -> str:
    """Return the canonical merge key for a phrase."""
    return _canonical_key(phrase)


def merge_candidates(
    raw_candidates: Dict[str, int],
) -> Dict[str, Dict]:
    """
    Merge raw candidate phrases into canonical groups.

    Parameters
    ----------
    raw_candidates : dict[str, int]
        phrase → total frequency count

    Returns
    -------
    dict[str, dict]
        canonical_key → {
            "display": str,          # best human-readable form
            "raw_forms": list[str],  # all raw variants seen
            "frequency": int,        # summed frequency
        }
    """
    groups: Dict[str, Dict] = {}

    for phrase, freq in raw_candidates.items():
        key = _canonical_key(phrase)
        if key not in groups:
            groups[key] = {"raw_forms": [], "frequency": 0}
        groups[key]["raw_forms"].append((phrase, freq))
        groups[key]["frequency"] += freq

    # Assign display forms
    for key, data in groups.items():
        data["display"] = _best_display_form(key, data["raw_forms"])
        data["raw_forms"] = [f for f, _ in data["raw_forms"]]

    return groups
