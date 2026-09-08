"""
technical_terms.py — Detects technical abbreviations and domain-specific terms.

These are lifted regardless of their TF-IDF score because they are inherently
meaningful (SQL, ACID, 3NF, B-tree, 1:N, etc.).
"""

from __future__ import annotations

import re
from typing import Dict, List, Set


# ---------------------------------------------------------------------------
# Curated DBMS seed terms (always included if found in corpus)
# ---------------------------------------------------------------------------
DBMS_SEED_TERMS: Set[str] = {
    # SQL & languages
    "SQL", "DDL", "DML", "DCL", "TCL", "PL/SQL", "T-SQL", "HQL", "XQuery",
    "SPARQL", "MDX",
    # Architectures & standards
    "DBMS", "RDBMS", "OODBMS", "ORDBMS", "NoSQL", "NewSQL",
    "3-tier architecture", "2-tier architecture", "client-server architecture",
    # Normal forms
    "1NF", "2NF", "3NF", "BCNF", "4NF", "5NF", "6NF", "DKNF",
    "3NF Synthesis",
    # Relationship cardinalities
    "1:1 relationship", "1:N relationship", "M:N relationship",
    "one-to-one", "one-to-many", "many-to-many",
    # ACID & transactions
    "ACID", "atomicity", "consistency", "isolation", "durability",
    "two-phase locking", "2PL", "strict 2PL",
    "MVCC", "multiversion concurrency control",
    "deadlock", "livelock", "serializability",
    "conflict serializability", "view serializability",
    "transaction", "commit", "rollback", "savepoint",
    # Indexing & storage
    "B-tree", "B+ tree", "B* tree", "indexing",
    "hash index", "clustered index", "non-clustered index",
    "bitmap index", "dense index", "sparse index",
    "ISAM", "heap file", "sequential file",
    # Query processing
    "query optimization", "query processing",
    "relational algebra", "relational calculus",
    "tuple relational calculus", "domain relational calculus",
    "join", "natural join", "outer join", "left join", "right join",
    "cross join", "theta join", "equijoin", "semi-join", "anti-join",
    "selection", "projection", "union", "intersection", "difference",
    "Cartesian product", "division",
    # ER model
    "ER model", "E-R model", "EER model", "entity-relationship model", "entity relationship",
    "entity", "attribute", "relationship", "weak entity",
    "composite attribute", "derived attribute", "multivalued attribute",
    "participation constraint", "cardinality ratio",
    "total participation", "partial participation",
    "identifying relationship", "recursive relationship",
    # Relational model
    "relational model", "relation", "tuple", "domain",
    "primary key", "foreign key", "candidate key", "superkey",
    "alternate key", "composite key", "natural key", "surrogate key",
    "referential integrity", "entity integrity",
    # Normalization
    "normalization", "denormalization",
    "functional dependency", "trivial functional dependency",
    "multivalued dependency", "join dependency",
    "Armstrong's axioms", "closure", "canonical cover",
    "lossless join", "dependency preservation",
    # Recovery
    "database recovery", "ARIES", "write-ahead log", "WAL",
    "checkpoint", "redo", "undo", "shadow paging",
    "log-based recovery", "deferred update", "immediate update",
    # Concurrency
    "concurrency control", "lock", "shared lock", "exclusive lock",
    "timestamp ordering", "optimistic concurrency control",
    "phantom read", "dirty read", "non-repeatable read",
    "isolation level", "READ COMMITTED", "REPEATABLE READ",
    "SERIALIZABLE", "READ UNCOMMITTED",
    # Distributed & advanced
    "distributed database", "distributed DBMS",
    "replication", "fragmentation", "horizontal fragmentation",
    "vertical fragmentation", "federated database",
    "data warehouse", "OLAP", "OLTP", "ETL",
    "star schema", "snowflake schema", "fact table", "dimension table",
    # XML & other
    "XML", "JSON", "RDF", "OWL", "ontology",
    "XPath", "XSLT", "XML schema", "DTD",
    # Object model
    "object-oriented database", "object-relational mapping", "ORM",
    "inheritance", "encapsulation", "polymorphism",
    # Misc
    "data model", "schema", "instance", "metadata",
    "data dictionary", "system catalog", "view",
    "stored procedure", "trigger", "assertion", "constraint",
    "data independence", "physical data independence",
    "logical data independence",
    "data abstraction", "view level", "logical level", "physical level",
    "three-schema architecture", "ANSI/SPARC",
}

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
