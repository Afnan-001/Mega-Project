
"""
noun_phrases.py — Lightweight noun-phrase extraction using NLTK POS tagging
and regex chunking.

Improvements:
- Processes the full corpus by default.
- Makes sampling and token limits configurable.
- Avoids the Punkt tokenizer resource dependency.
- Reports failed chunks instead of silently discarding errors.
- Improves phrase normalization and filtering.
- Preserves the original extract_noun_phrases(texts, batch_size=0) interface.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# None means no truncation.
MAX_TOKENS: Optional[int] = None

_NP_GRAMMAR = r"""
    NP: {<DT>?<JJ.*|VBG|VBN>*<NN.*>+}
        {<NNP>+}
"""

# Generic single-word terms that are rarely useful as standalone concepts.
_BLOCK = {
    "chapter", "section", "figure", "table", "page", "example",
    "exercise", "problem", "note", "part", "unit", "book",
    "author", "publisher", "edition", "year", "method", "way",
    "use", "form", "type", "kind", "set", "list", "number",
    "result", "value", "case", "step", "level", "order",
    "fact", "term", "group", "class", "time", "end",
    "user", "file", "line",
}

_DET = {
    "a", "an", "the", "this", "that", "these", "those",
    "each", "every",
}


def _ensure_nltk() -> None:
    """Ensure an English POS tagger is available."""
    import nltk

    # Support current and older NLTK resource names.
    resources = (
        ("averaged_perceptron_tagger_eng",
         "taggers/averaged_perceptron_tagger_eng"),
        ("averaged_perceptron_tagger",
         "taggers/averaged_perceptron_tagger"),
    )

    available = False

    for name, path in resources:
        try:
            nltk.data.find(path)
            available = True
            break
        except LookupError:
            continue

    if not available:
        downloaded = False

        for name, _ in resources:
            try:
                if nltk.download(name, quiet=True):
                    downloaded = True
            except Exception:
                logger.warning(
                    "Could not download NLTK resource %s.", name
                )

        if not downloaded:
            raise RuntimeError(
                "Could not download the NLTK POS tagger. "
                "Install the required NLTK English tagger resource "
                "and retry."
            )

    # Verify that the installed NLTK version can actually tag words.
    try:
        nltk.pos_tag(["database"])
    except LookupError as exc:
        raise RuntimeError(
            "The NLTK POS tagger resource is unavailable or incompatible. "
            "Install the English POS tagger required by your NLTK version."
        ) from exc


def _extract_nps_from_text(
    text: str,
    chunker,
    max_tokens: Optional[int] = None,
) -> List[str]:
    """Extract noun phrases from a single text chunk."""
    import nltk
    from nltk.tokenize import TreebankWordTokenizer

    if not isinstance(text, str) or not text.strip():
        return []

    # This tokenizer does not require Punkt or punkt_tab downloads.
    tokens = TreebankWordTokenizer().tokenize(text)

    if max_tokens is not None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive or None.")
        tokens = tokens[:max_tokens]

    if not tokens:
        return []

    tagged = nltk.pos_tag(tokens)
    tree = chunker.parse(tagged)

    phrases = []

    for subtree in tree.subtrees(
        filter=lambda node: node.label() == "NP"
    ):
        words = [
            word.lower()
            for word, _ in subtree.leaves()
        ]

        # Remove leading determiners.
        while words and words[0] in _DET:
            words.pop(0)

        if not words:
            continue

        # Remove surrounding punctuation from individual tokens.
        # Keep internal punctuation such as hyphens when present.
        phrase = " ".join(words).strip(" \t\n.,;:!?\"'()[]{}")

        if not phrase or not any(char.isalpha() for char in phrase):
            continue

        words = phrase.split()
        word_count = len(words)

        if word_count > 6:
            continue

        if word_count == 1 and phrase in _BLOCK:
            continue

        phrases.append(phrase)

    return phrases


def extract_noun_phrases(
    texts: List[str],
    batch_size: int = 0,
    *,
    sample_every: int = 1,
    max_tokens: Optional[int] = MAX_TOKENS,
    strict: bool = False,
) -> Dict[str, int]:
    """
    Extract noun-phrase candidates from a corpus.

    Parameters
    ----------
    texts:
        List of text chunks.
    batch_size:
        Progress-reporting interval in chunks. Zero disables periodic
        progress reports; final statistics are still printed.
    sample_every:
        Process every Nth chunk. Defaults to 1 (all chunks).
    max_tokens:
        Maximum tokens per chunk. None processes the entire chunk.
    strict:
        If True, stop and raise when a chunk fails. Otherwise, log
        failures and continue processing the remaining chunks.

    Returns
    -------
    Dict[str, int]
        Lowercased noun phrase -> extracted occurrence count.
    """
    if sample_every < 1:
        raise ValueError("sample_every must be at least 1.")

    if batch_size < 0:
        raise ValueError("batch_size cannot be negative.")

    if max_tokens is not None and max_tokens < 1:
        raise ValueError("max_tokens must be positive or None.")

    try:
        import nltk  # noqa: F401
        from nltk.chunk import RegexpParser
    except ImportError as exc:
        raise RuntimeError(
            "NLTK is not installed. Install it with: pip install nltk"
        ) from exc

    _ensure_nltk()

    total = len(texts)
    sampled = texts[::sample_every]
    chunker = RegexpParser(_NP_GRAMMAR)

    if sample_every > 1:
        print(
            f"[noun_phrases] Processing {len(sampled)}/{total} chunks "
            f"(every {sample_every}th chunk)."
        )

    np_counts: Dict[str, int] = {}
    failures = 0
    n = len(sampled)

    for i, text in enumerate(sampled, start=1):
        try:
            phrases = _extract_nps_from_text(
                text, chunker, max_tokens=max_tokens
            )

            for phrase in phrases:
                np_counts[phrase] = np_counts.get(phrase, 0) + 1

        except Exception as exc:
            failures += 1

            logger.warning(
                "NP extraction failed for sampled chunk %d/%d: %s",
                i,
                n,
                exc,
            )

            if strict:
                raise RuntimeError(
                    f"NP extraction failed at sampled chunk {i}/{n}."
                ) from exc

        if batch_size and i % batch_size == 0:
            print(
                f"[noun_phrases] Processed {i}/{n} chunks "
                f"({i / n:.0%})."
            )

    print(
        f"[noun_phrases] Completed: {n} chunks processed, "
        f"{len(np_counts)} unique phrases, "
        f"{failures} failed chunks."
    )

    return np_counts
