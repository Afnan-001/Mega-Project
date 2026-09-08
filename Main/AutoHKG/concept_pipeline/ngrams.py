"""
ngrams.py — Extracts 1-to-4-gram candidates from the corpus using sklearn.

TF-IDF is also computed here over the full chunk corpus so that each
candidate gets a corpus-level importance signal.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import re


# ---------------------------------------------------------------------------
# Generic / noise n-grams to block at extraction time
# ---------------------------------------------------------------------------
_BLOCK_UNIGRAMS = {
    "chapter", "section", "figure", "table", "page", "example", "exercise",
    "problem", "note", "part", "unit", "book", "author", "publisher",
    "edition", "year", "method", "way", "use", "form", "type", "kind",
    "set", "list", "number", "system", "model", "data", "information",
    "concept", "result", "value", "case", "step", "level", "order",
    "fact", "term", "group", "class", "time", "end", "user", "application",
    "server", "file", "line", "need", "also", "well", "often",
    "called", "used", "given", "based", "shown", "many", "however",
    "therefore", "thus", "i.e", "e.g", "etc", "fig",
}

# Pure grammatical stop words (should not start or end any multi-word n-gram)
_PURE_STOPWORDS = {
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", "can",
    "a", "an", "the", "this", "that", "these", "those",
    "it", "he", "she", "they", "we", "i", "you",
    "in", "on", "at", "to", "for", "of", "by", "with", "from",
    "and", "or", "but", "not", "if", "as", "so", "than",
    "which", "where", "when", "what", "how", "who", "each",
    "its", "their", "our", "your", "his", "her",
}


def _token_ok(token: str) -> bool:
    """A token is acceptable if it contains at least one alphabetic char."""
    return bool(re.search(r"[a-zA-Z]", token))


def _ngram_ok(tokens: List[str]) -> bool:
    """
    Reject n-grams that:
    - as single words are in _BLOCK_UNIGRAMS or _PURE_STOPWORDS
    - consist entirely of stop/generic words
    - start or end with a pure grammatical stop word
    - contain no alphabetic characters
    """
    lower_tokens = [t.lower() for t in tokens]
    n = len(lower_tokens)

    if n == 1:
        if lower_tokens[0] in _BLOCK_UNIGRAMS or lower_tokens[0] in _PURE_STOPWORDS:
            return False
        return _token_ok(tokens[0])

    # Multi-word n-grams:
    # 1. All tokens are stop/generic words
    if all(t in _BLOCK_UNIGRAMS or t in _PURE_STOPWORDS for t in lower_tokens):
        return False

    # 2. First or last token is a pure grammatical stop word
    if lower_tokens[0] in _PURE_STOPWORDS or lower_tokens[-1] in _PURE_STOPWORDS:
        return False

    # 3. Must have at least one alphabetic token
    if not any(_token_ok(t) for t in tokens):
        return False

    return True


def extract_ngrams(
    texts: List[str],
    n_range: Tuple[int, int] = (1, 4),
    min_df: int = 2,
    max_df_ratio: float = 0.7,
) -> Tuple[Dict[str, int], Dict[str, float]]:
    """
    Extract n-gram frequencies and TF-IDF scores from the corpus.

    Parameters
    ----------
    texts : list[str]
        One string per chunk.
    n_range : tuple[int, int]
        Min and max n-gram sizes (inclusive).
    min_df : int
        Minimum document frequency (skip very rare n-grams).
    max_df_ratio : float
        Maximum document frequency ratio (skip corpus-wide terms).

    Returns
    -------
    freq_dict : dict[str, int]   — n-gram → total count
    tfidf_dict : dict[str, float] — n-gram → max TF-IDF score across docs
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer  # noqa: PLC0415
    except ImportError:
        print("[ngrams] scikit-learn not installed; skipping n-gram extraction")
        return {}, {}

    # --- Frequency (CountVectorizer) ---
    count_vec = CountVectorizer(
        ngram_range=n_range,
        min_df=min_df,
        max_df=max_df_ratio,
        token_pattern=r"(?u)\b[a-zA-Z0-9][a-zA-Z0-9\+\*\-]*\b",
        strip_accents="unicode",
    )

    try:
        count_matrix = count_vec.fit_transform(texts)
    except ValueError:
        return {}, {}

    vocab = count_vec.get_feature_names_out()
    total_counts = count_matrix.sum(axis=0).A1

    freq_dict: Dict[str, int] = {}
    for term, count in zip(vocab, total_counts):
        tokens = term.split()
        if _ngram_ok(tokens):
            freq_dict[term] = int(count)

    # --- TF-IDF ---
    tfidf_vec = TfidfVectorizer(
        ngram_range=n_range,
        min_df=min_df,
        max_df=max_df_ratio,
        token_pattern=r"(?u)\b[a-zA-Z0-9][a-zA-Z0-9\+\*\-]*\b",
        strip_accents="unicode",
        sublinear_tf=True,
    )

    try:
        tfidf_matrix = tfidf_vec.fit_transform(texts)
    except ValueError:
        return freq_dict, {}

    tfidf_vocab = tfidf_vec.get_feature_names_out()
    # Use max TF-IDF across all documents for each term
    max_tfidf = tfidf_matrix.max(axis=0).toarray().flatten()

    tfidf_dict: Dict[str, float] = {}
    for term, score in zip(tfidf_vocab, max_tfidf):
        tokens = term.split()
        if _ngram_ok(tokens):
            tfidf_dict[term] = float(score)

    print(f"[ngrams] Extracted {len(freq_dict)} n-grams with TF-IDF scores")
    return freq_dict, tfidf_dict
