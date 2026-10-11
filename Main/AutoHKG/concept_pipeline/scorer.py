"""
scorer.py — Combines all NLP signals into a final score per candidate concept.

Scoring Formula
---------------
final_score =
    w_tfidf   * tfidf_score           # corpus-level statistical importance
  + w_freq    * freq_norm             # relative frequency (normalized 0-1)
  + w_np      * noun_phrase_score     # NLTK NP evidence (0 or 1)
  + w_yake    * yake_score            # PositionalRank inverted score (0-1)
  + w_heading * heading_score         # appears in detected chapter/section headings
  + w_def     * definition_score      # appears in "X is defined as…" patterns
  + w_spread  * chunk_spread_score    # proportion of chunks that contain it
  + w_tech    * technical_term_score  # matches technical abbreviation / seed list
  - p_generic * generic_penalty       # in generic English word list
  - p_noise   * noise_penalty         # matched noise / boilerplate pattern

Quality Gates (applied BEFORE scoring)
---------------------------------------
1. Signal Agreement Gate: a candidate must have evidence from ≥2 independent
   signals (tfidf, np, yake, heading, definition, technical, spread) OR be an
   explicit technical term / heading / definition.  Single-signal candidates
   are discarded immediately (they are almost always noise).
2. Length Gate: single-word candidates shorter than 4 chars are dropped unless
   they are in the technical seed list.
3. Structure Gate: candidates with more than 5 words are dropped (too long to
   be a standalone concept).

Weight rationale
----------------
heading (3.0), definition (3.0): Ground-truth signals — chapter titles and
    "X is defined as" are the most authoritative domain signals.
tfidf (2.5): Strong unsupervised corpus-level signal.
yake (2.0): Captures positional and contextual keyword evidence.
technical (6.0): Abbreviations and domain-specific seeds need a hard lift.
noun_phrase (1.5): Grammatical validity confirms phrase structure.
chunk_spread (1.5): Concepts that appear across many chunks are stable.
freq_norm (1.0): Frequency alone is insufficient; used as a soft tiebreaker.
generic_penalty (4.0): Aggressive to block noise words from sneaking through.
noise_penalty (5.0): Hard block for publisher / boilerplate patterns.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Set, Tuple
from concept_pipeline.technical_terms import GENERIC_SEED_TERMS

_SEED_SET: Set[str] = {s.lower().strip() for s in GENERIC_SEED_TERMS}

# ---------------------------------------------------------------------------
# Weights (change here to tune the pipeline)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "tfidf":    2.5,
    "freq":     1.0,
    "np":       1.5,
    "yake":     2.0,
    "heading":  3.0,
    "definition": 3.0,
    "spread":   1.5,
    "technical": 6.0,
}

PENALTIES = {
    "generic":  4.0,
    "noise":    5.0,
}

# Minimum number of INDEPENDENT signals a candidate must have to pass the
# signal-agreement gate (applied before scoring).
MIN_SIGNAL_AGREEMENT = 2

# Maximum number of words in a valid concept phrase
MAX_PHRASE_WORDS = 5

# Minimum character length for single-word concepts (unless technical/heading/def)
MIN_SINGLE_WORD_CHARS = 4

# ---------------------------------------------------------------------------
# Generic English words that should never be concepts
# ---------------------------------------------------------------------------
_GENERIC_WORDS: Set[str] = {
    "system", "data", "information", "method", "process", "way",
    "example", "case", "problem", "result", "value", "number",
    "level", "order", "type", "kind", "form", "part", "term",
    "figure", "table", "note", "page", "chapter", "section",
    "book", "author", "edition", "publisher", "year",
    "concept", "concepts", "fact", "group", "class", "step", "end",
    "user", "application", "server", "file", "line",
    "need", "also", "well", "often", "called", "used", "uses", "using",
    "given", "based", "shown", "many", "following",
    "important", "necessary", "different", "various",
    "first", "second", "third", "next", "previous",
    "large", "small", "simple", "complex", "general",
    "specific", "similar", "common", "certain", "possible",
    "main", "single", "multiple", "new", "old", "current",
    # Common English words and filler fragments that leak through
    "ability", "able", "above", "access", "action", "actions", "address", "after", "again", "age", "ago",
    "already", "although", "another", "approach", "area", "around", "arra",
    "base", "basis", "before", "begin", "below", "between", "block", "building",
    "break", "bring", "build", "call", "change", "choose", "code",
    "come", "consider", "contain", "contents", "control", "cost", "course", "create",
    "declare", "define", "describe", "design", "detail", "depth", "digit", "discuss", "domain",
    "either", "else", "entire", "entry", "even", "every", "exercise", "exercises", "exist", "exit", "expressions",
    "false", "find", "finite", "flo", "follow", "from", "full", "function", "give", "go", "goto",
    "handle", "happen", "highlight", "hold", "however", "ideal", "inc", "include", "increase", "input", "instance", "instr", "intr",
    "issue", "issues", "item", "keep", "know", "language", "large", "later", "lead",
    "leave", "less", "like", "logical", "long", "look", "lose",
    "make", "mean", "meet", "mention", "might", "minus", "mop", "move",
    "naa", "name", "node", "non", "null", "num", "often", "once", "ops", "option", "original", "other", "out",
    "output", "overall", "over", "pass", "place", "point", "position", "possible", "pref", "program",
    "provide", "put", "rank", "rate", "reach", "read", "reason", "refer", "region", "reuse", "right", "rule", "rules",
    "remain", "remove", "require", "return", "role", "run",
    "say", "science", "see", "seem", "share", "show", "since", "situation",
    "size", "solve", "sort", "sor", "source", "space", "start",
    "state", "still", "store", "string", "structure", "sub", "take", "tell", "temp", "terminal", "there", "these", "those",
    "therefore", "thing", "think", "though", "through", "then", "tion", "tions", "top", "trees", "true",
    "together", "try", "turn", "under", "understand", "until", "undef", "union",
    "upon", "view", "want", "where", "while", "work", "write", "ysis", "uction", "ucture",
    "about", "bad", "bags", "basics", "bit", "blob", "br", "bs", "bu",
    "ibm", "idb", "isbn", "ace", "acm", "add", "ai", "aj", "ay",
    "bccampus", "bcit", "adrienne", "cation", "ollo",
}

# Noise patterns for candidate phrases
_NOISE_PHRASE_PATTERNS: List[re.Pattern] = [
    re.compile(r"[\x00-\x1f\x7f-\x9f]"),             # unprintable control chars
    re.compile(r"^[^a-zA-Z]"),                         # starts with non-letter (digits, symbols)
    re.compile(r"\b(exercise|exercises|summary|references?|chapter|section)\b", re.IGNORECASE), # exercise/boilerplate
    re.compile(r"written by", re.IGNORECASE),
    re.compile(r"about the (book|author)", re.IGNORECASE),
    re.compile(r"check more", re.IGNORECASE),
    re.compile(r"listen.*audiobook", re.IGNORECASE),
    re.compile(r"^(fig|figure|table|equation)\s*\d+", re.IGNORECASE),
    re.compile(r"^\d+(\.\d+)*$"),                # pure numbers
    # Dummy formal grammar strings e.g. "aa ab", "aa ab ba", "aab aaab", "ab ba"
    re.compile(r"^(?:[a-z]{1,2}\s+)+[a-z]{1,2}$", re.IGNORECASE),
    # OCR artefacts: isolated single letter before/after a space ("c ity", "d ata", "v er")
    re.compile(r"\b[a-z]\b", re.IGNORECASE),
    re.compile(r"^(c\s+ity|d\s+ata|attribute\s+d)$", re.IGNORECASE),
    # Common OCR split-word fragments (e.g. "ab out", "abstr act", "ac cepting", "ac kno", "sp ecific")
    re.compile(r"^(ab\s+out|abstr\s+act|ac\s+cepting|ac\s+cording|ac\s+hiev|ac\s+kno|sp\s+ecific|di\s+ffe?r)\b", re.IGNORECASE),
    re.compile(r"^(ab|ac|sp|tr|ont|sc)\s+[a-z]{2,}", re.IGNORECASE),
    # Phrases starting with prepositions or conversational connectors ("about the...", "according to...")
    re.compile(r"^(about|according|achieving|across|above|along|against|among|around|because|before|behind|below|beneath|beside|between|beyond|during|except|inside|into|near|onto|outside|over|through|under|underneath|until|upon|within|without)\s+", re.IGNORECASE),
    # Attribute with single letter/digit suffix ("attribute d", "attribute 1")
    re.compile(r"\b(attribute|relation|table)\s+[a-z\d]$", re.IGNORECASE),
    # Dummy attribute letters / random letter sequences ("abcde", "abcd")
    re.compile(r"^(abcde|abcd|xyz)$", re.IGNORECASE),
    re.compile(r"^[b-df-hj-np-tv-z]{3,}$", re.IGNORECASE),
    # Generic option / verb phrase fragments
    re.compile(r"^(another|some|any|although|there)\s+(option|choice|case|way|type|there)$", re.IGNORECASE),
]

_MIN_SINGLE_WORD_LEN = 5


def _is_noise_phrase(phrase: str) -> bool:
    for pattern in _NOISE_PHRASE_PATTERNS:
        if pattern.search(phrase):
            return True
    return False


_PURE_STOP_TOKENS: Set[str] = {
    "a", "an", "the", "this", "that", "these", "those", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "can", "if", "than", "so", "as", "but",
    "and", "or", "not", "it", "he", "she", "they", "we", "i", "you", "which", "where",
    "when", "what", "how", "who", "each", "its", "their", "our", "your", "his", "her",
    "by", "with", "from", "in", "on", "at", "to", "for", "of", "into", "onto", "upon",
}

_INVALID_INNER_TOKENS: Set[str] = {
    "for", "of", "in", "on", "at", "to", "from", "with", "by", "about", "into", "onto", "through", "during", "upon", "under", "over",
    "and", "or", "but", "nor", "if", "that", "whether", "because", "which", "where", "when", "how", "who", "whom",
    "what", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "have", "has", "had", "would", "could", "should", "may", "might", "must", "can",
    "so", "than", "this", "these", "those", "each", "its", "their", "our", "your", "his", "her",
}


def _is_generic(phrase: str) -> bool:
    tokens = phrase.lower().split()
    if not tokens:
        return True
    # Single generic word or single stop word
    if len(tokens) == 1 and (tokens[0] in _GENERIC_WORDS or tokens[0] in _PURE_STOP_TOKENS):
        return True
    # Start or end with a pure grammatical stop word
    if tokens[0] in _PURE_STOP_TOKENS or tokens[-1] in _PURE_STOP_TOKENS:
        return True
    # Contains sentence fragment connectors or verbs
    if any(t in _INVALID_INNER_TOKENS for t in tokens):
        return True
    # All tokens are generic or stop words
    if all(t in _GENERIC_WORDS or t in _PURE_STOP_TOKENS for t in tokens):
        return True
    return False


def _freq_normalize(freq: int, max_freq: int) -> float:
    if max_freq == 0:
        return 0.0
    return math.log1p(freq) / math.log1p(max_freq)


def _spread_score(phrase: str, chunk_spread: Dict[str, int], total_chunks: int) -> float:
    """Proportion of chunks containing the phrase (capped at 0.5 to avoid generic)."""
    count = chunk_spread.get(phrase, 0)
    if total_chunks == 0:
        return 0.0
    ratio = count / total_chunks
    # Concepts appearing in > 50% of chunks are likely too generic
    if ratio > 0.5:
        return 0.0
    return ratio * 2.0  # scale to [0, 1]


def compute_chunk_spread(
    phrases: Set[str], texts: List[str]
) -> Dict[str, int]:
    """
    For each phrase, count how many chunks contain it.
    This is done once before scoring.
    """
    spread: Dict[str, int] = {p: 0 for p in phrases}
    total = len(texts)
    print(f"[scorer] Computing chunk spread for {len(phrases)} candidate phrases...")

    for i, text in enumerate(texts):
        lower = text.lower()
        for phrase in phrases:
            if phrase in lower:
                spread[phrase] += 1
        if (i + 1) % 500 == 0 or (i + 1) == total:
            pct = int((i + 1) / total * 100)
            print(f"[scorer] Chunk spread: {pct}% ({i+1}/{total}) ...", end="\r", flush=True)

    print(f"\n[scorer] Chunk spread calculation complete")
    return spread


def score_candidates(
    candidates: Dict[str, int],          # phrase → frequency
    tfidf_scores: Dict[str, float],       # phrase → tfidf
    np_set: Set[str],                     # set of lowercased noun phrases
    yake_scores: Dict[str, float],        # phrase → yake importance (0-1)
    heading_set: Set[str],                # lowercased heading phrases
    definition_set: Set[str],             # lowercased definition terms
    technical_set: Set[str],              # lowercased technical terms
    chunk_spread: Dict[str, int],         # phrase → chunk count
    total_chunks: int,
) -> List[Dict]:
    """
    Score all candidate phrases and return a sorted list of dicts.

    Returns
    -------
    list[dict]  (sorted by final_score descending)
        Each dict contains candidate, scores, and rejection reasons.
    """
    max_freq = max(candidates.values(), default=1)
    scored: List[Dict] = []

    for phrase, freq in candidates.items():
        phrase_lower = phrase.lower().strip()
        words = phrase_lower.split()
        reasons: List[str] = []

        # --- Structure Gate: reject phrases that are too long (> MAX_PHRASE_WORDS) ---
        if len(words) > MAX_PHRASE_WORDS:
            reasons.append("too_many_words")
            scored.append({
                "candidate": phrase, "normalized": phrase_lower, "frequency": freq,
                "tfidf_score": 0, "freq_norm": 0, "noun_phrase": False,
                "yake_score": 0, "heading": False, "definition": False,
                "chunk_spread": 0, "technical_term": False,
                "generic_penalty": 0, "noise_penalty": 1.0,
                "final_score": -100.0, "rejection_reasons": reasons,
            })
            continue

        # --- Signal scores ---
        s_tfidf = tfidf_scores.get(phrase_lower, tfidf_scores.get(phrase, 0.0))
        s_freq  = _freq_normalize(freq, max_freq)
        s_np    = 1.0 if phrase_lower in np_set else 0.0
        s_yake  = yake_scores.get(phrase_lower, 0.0)
        s_head  = 1.0 if phrase_lower in heading_set else 0.0
        s_def   = 1.0 if phrase_lower in definition_set else 0.0
        s_spread = _spread_score(phrase_lower, chunk_spread, total_chunks)
        s_tech  = 1.0 if (phrase_lower in technical_set or phrase_lower in _SEED_SET) else 0.0

        # --- Penalties ---
        noise_pen = 0.0
        generic_pen = 0.0

        if _is_noise_phrase(phrase_lower):
            noise_pen = 1.0
            reasons.append("noise_phrase")

        if _is_generic(phrase_lower):
            generic_pen = 1.0
            reasons.append("generic_term")

        # --- Single-word gates ---
        if len(words) == 1:
            # Block very short single words unless they are explicit technical terms
            if len(phrase_lower) < MIN_SINGLE_WORD_CHARS and not (s_tech or s_head or s_def):
                noise_pen = 1.0
                reasons.append("single_word_too_short")
            elif not (s_tech or s_head or s_def):
                noise_pen = 1.0
                reasons.append("single_word_non_technical")

        # --- Signal Agreement Gate ---
        # Count how many independent strong signals support this candidate.
        # High-evidence anchors (heading, definition, technical) count automatically.
        # For others, require at least MIN_SIGNAL_AGREEMENT signals.
        is_anchor = bool(s_head or s_def or s_tech)
        signal_count = sum([
            1 if s_tfidf > 0.05 else 0,   # meaningful TF-IDF (not near-zero)
            1 if s_np else 0,
            1 if s_yake > 0.05 else 0,    # meaningful positional rank score
            1 if s_spread > 0.05 else 0,  # appears in multiple chunks
            1 if s_head else 0,
            1 if s_def else 0,
            1 if s_tech else 0,
        ])
        if not is_anchor and signal_count < MIN_SIGNAL_AGREEMENT:
            noise_pen = 1.0
            reasons.append(f"weak_signal_agreement({signal_count}/{MIN_SIGNAL_AGREEMENT})")

        # --- Multi-word bonus: only for well-supported 2–5 word phrases ---
        # Requires meaningful TF-IDF AND at least 2 structural signals
        structural_signals = sum([bool(s_np), bool(s_head), bool(s_def), bool(s_tech), s_tfidf > 0.08])
        multi_word_bonus = (
            2.5 if 2 <= len(words) <= 4
                and s_tfidf > 0.08
                and structural_signals >= 2
            else 0.0
        )

        # --- Final score ---
        if noise_pen >= 1.0 or generic_pen >= 1.0:
            final_score = -100.0
        else:
            final_score = (
                WEIGHTS["tfidf"]      * s_tfidf
              + WEIGHTS["freq"]       * s_freq
              + WEIGHTS["np"]         * s_np
              + WEIGHTS["yake"]       * s_yake
              + WEIGHTS["heading"]    * s_head
              + WEIGHTS["definition"] * s_def
              + WEIGHTS["spread"]     * s_spread
              + WEIGHTS["technical"]  * s_tech
              + multi_word_bonus
              - PENALTIES["generic"]  * generic_pen
              - PENALTIES["noise"]    * noise_pen
            )

        scored.append({
            "candidate":        phrase,
            "normalized":       phrase_lower,
            "frequency":        freq,
            "tfidf_score":      round(s_tfidf, 4),
            "freq_norm":        round(s_freq, 4),
            "noun_phrase":      bool(s_np),
            "yake_score":       round(s_yake, 4),
            "heading":          bool(s_head),
            "definition":       bool(s_def),
            "chunk_spread":     chunk_spread.get(phrase_lower, 0),
            "technical_term":   bool(s_tech),
            "generic_penalty":  generic_pen,
            "noise_penalty":    noise_pen,
            "signal_count":     signal_count,
            "final_score":      round(final_score, 4),
            "rejection_reasons": reasons,
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored


def filter_candidates(
    scored: List[Dict],
    min_score: Optional[float] = None,
    top_k: Optional[int] = None,
) -> List[Dict]:
    """
    Filter candidates by minimum score and/or top-K count.

    Parameters
    ----------
    scored     : output of score_candidates()
    min_score  : drop everything below this threshold
    top_k      : keep at most this many candidates

    Returns
    -------
    Filtered and ranked list.
    """
    filtered = [c for c in scored if c["final_score"] > 0]

    if min_score is not None:
        filtered = [c for c in filtered if c["final_score"] >= min_score]

    if top_k is not None:
        filtered = filtered[:top_k]

    return filtered


def rank_candidates(scored: List[Dict], top_k: int) -> List[Dict]:
    """Return the top-K candidates by final_score."""
    return scored[:top_k]
