"""
noun_phrases.py — Fast NP extraction using NLTK POS tagging + regex chunker.

spaCy's noun_chunks requires the full dependency parser which is very slow
on large corpora. Instead we use:
  1. NLTK's averaged_perceptron_tagger for POS tagging (fast, no parser)
  2. NLTK's RegexpParser with a grammar that captures NP patterns:
       NP: {<DT>? <JJ>* <NN.*>+}   — optional determiner, adjectives, nouns
       NP: {<NNP>+}                 — proper noun sequences
  3. Sampling: only every SAMPLE_EVERY-th chunk for corpora > SAMPLE_THRESHOLD

This runs in ~10-30 seconds on a 4000-chunk corpus vs 10+ minutes for spaCy.
"""

from __future__ import annotations

from typing import Dict, List


SAMPLE_THRESHOLD = 500    # if more chunks than this, sample
SAMPLE_EVERY     = 2      # use every 2nd chunk (50% sample)
MAX_TOKENS       = 400    # max tokens per chunk to POS-tag


# NP grammar: (optional DT) + (any JJ/VBG/VBN) + (one or more NN*)
_NP_GRAMMAR = r"""
    NP: {<DT>?<JJ.*|VBG|VBN>*<NN.*>+}
        {<NNP>+}
"""

# Single words that are not meaningful standalone concepts
_BLOCK = {
    "chapter", "section", "figure", "table", "page", "example",
    "exercise", "problem", "note", "part", "unit", "book",
    "author", "publisher", "edition", "year", "method", "way",
    "use", "form", "type", "kind", "set", "list", "number",
    "system", "model", "data", "information", "concept",
    "result", "value", "case", "step", "level", "order",
    "fact", "term", "group", "class", "time", "end",
    "user", "application", "server", "file", "line",
}

# Determiners to strip from the start of NPs
_DET = {"a", "an", "the", "this", "that", "these", "those", "each", "every"}


def _ensure_nltk():
    """Download required NLTK data if not present."""
    import nltk  # noqa: PLC0415
    resources = {
        "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
        "averaged_perceptron_tagger_eng": "taggers/averaged_perceptron_tagger_eng",
        "punkt": "tokenizers/punkt",
        "punkt_tab": "tokenizers/punkt_tab",
    }
    for res_name, res_path in resources.items():
        try:
            nltk.data.find(res_path)
        except LookupError:
            try:
                nltk.download(res_name, quiet=True)
            except Exception:
                pass


def _extract_nps_from_text(text: str, chunker) -> List[str]:
    """Extract NPs from a single text string using NLTK."""
    import nltk  # noqa: PLC0415

    try:
        tokens = nltk.word_tokenize(text)[:MAX_TOKENS]
        tagged = nltk.pos_tag(tokens)
        tree   = chunker.parse(tagged)

        nps = []
        for subtree in tree.subtrees(filter=lambda t: t.label() == "NP"):
            words = [w.lower() for w, _ in subtree.leaves()]

            # Strip leading determiners
            while words and words[0] in _DET:
                words = words[1:]

            if not words:
                continue

            phrase = " ".join(words)
            n = len(words)

            if n < 1 or n > 6:
                continue
            if n == 1 and phrase in _BLOCK:
                continue
            if not any(c.isalpha() for c in phrase):
                continue

            nps.append(phrase)

        return nps

    except Exception:
        return []


def extract_noun_phrases(texts: List[str], batch_size: int = 0) -> Dict[str, int]:
    """
    Extract noun-phrase candidates from the corpus using NLTK.

    For large corpora, samples every SAMPLE_EVERY-th chunk.

    Returns
    -------
    dict[str, int]
        lowercased noun phrase → occurrence count
    """
    try:
        import nltk  # noqa: PLC0415
        from nltk.chunk import RegexpParser  # noqa: PLC0415
    except ImportError:
        print("[noun_phrases] NLTK not installed; skipping NP extraction")
        return {}

    _ensure_nltk()

    total = len(texts)

    # Smart sampling
    if total > SAMPLE_THRESHOLD:
        sampled = texts[::SAMPLE_EVERY]
        print(f"[noun_phrases] Corpus={total} chunks — sampling every "
              f"{SAMPLE_EVERY}nd chunk ({len(sampled)} chunks)")
    else:
        sampled = texts

    chunker   = RegexpParser(_NP_GRAMMAR)
    np_counts: Dict[str, int] = {}
    n         = len(sampled)

    for i, text in enumerate(sampled):
        for phrase in _extract_nps_from_text(text, chunker):
            np_counts[phrase] = np_counts.get(phrase, 0) + 1

        if (i + 1) % 100 == 0 or (i + 1) == n:
            pct = int((i + 1) / n * 100)
            print(f"[noun_phrases] {pct}% ({i+1}/{n}) ...", end="\r")

    print(f"\n[noun_phrases] Extracted {len(np_counts)} unique noun phrases")
    return np_counts
