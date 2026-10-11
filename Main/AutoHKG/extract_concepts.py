from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

# Load Environment Variables
load_dotenv()

# Paths & Defaults
DATA_DIR = MAIN_DIR / "outputs" / "data"
DEFAULT_INPUT = DATA_DIR / "content_chunks.json"
DEFAULT_OUTPUT = DATA_DIR / "concepts.json"


def extract_concepts_nlp(
    input_file: Path,
    output_file: Path,
    limit: int = 0,
    top_k: int = 1000,
    min_score: float = 3.0,
) -> list[str]:
    """Extract key concept terms using traditional NLP algorithms (concept_pipeline)."""
    from concept_pipeline.loader import load_chunks
    from concept_pipeline.cleaner import filter_noise_chunks
    from concept_pipeline.headings import extract_headings
    from concept_pipeline.definitions import detect_definitions
    from concept_pipeline.technical_terms import detect_technical_terms
    from concept_pipeline.noun_phrases import extract_noun_phrases
    from concept_pipeline.ngrams import extract_ngrams
    from concept_pipeline.yake_extractor import extract_yake_keywords
    from concept_pipeline.scorer import compute_chunk_spread, score_candidates, filter_candidates
    from concept_pipeline.normalizer import merge_candidates
    from concept_pipeline.saver import save_concepts

    print("=" * 60)
    print("  NLP Technical Concept Extractor")
    print("=" * 60)
    print(f"[INPUT]  File  : {input_file}")
    print(f"[OUTPUT] File  : {output_file}")
    if limit > 0:
        print(f"[LIMIT]  First {limit} chunks")

    # 1. Load Chunks
    chunks = load_chunks(input_file)
    if limit > 0:
        chunks = chunks[:limit]
    total_chunks = len(chunks)

    # 2. Clean Text
    chunks = filter_noise_chunks(chunks)
    texts = [c["_cleaned_text"] for c in chunks]

    # 3. Headings
    heading_counts = extract_headings(texts)
    heading_set = set(heading_counts.keys())

    # 4. Definitions
    def_counts = detect_definitions(texts)
    definition_set = set(def_counts.keys())

    # 5. Technical Terms
    tech_counts = detect_technical_terms(texts)
    technical_set = {k.lower() for k in tech_counts.keys()}

    # 6. Noun Phrases
    np_counts = extract_noun_phrases(texts)
    np_set = set(np_counts.keys())

    # 7. N-grams & TF-IDF
    freq_dict, tfidf_dict = extract_ngrams(texts)

    # 8. YAKE / Positional Rank
    yake_scores = extract_yake_keywords(texts)

    # 9. Aggregate Candidates & Frequencies
    # Require raw n-grams to appear in at least 3 chunks (raised from 2 for quality)
    valid_freq_keys = {k for k, v in freq_dict.items() if v >= 3}
    candidate_keys = (
        valid_freq_keys
        | set(np_counts.keys())
        | set(yake_scores.keys())
        | heading_set
        | definition_set
        | technical_set
    )

    raw_candidates: dict[str, int] = {}
    for p in candidate_keys:
        raw_candidates[p] = max(
            freq_dict.get(p, 0),
            np_counts.get(p, 0),
            heading_counts.get(p, 0),
            def_counts.get(p, 0),
            tech_counts.get(p, 0),
            1,
        )

    # 10. Chunk Spread & Scoring
    chunk_spread = compute_chunk_spread(candidate_keys, texts)
    scored = score_candidates(
        candidates=raw_candidates,
        tfidf_scores=tfidf_dict,
        np_set=np_set,
        yake_scores=yake_scores,
        heading_set=heading_set,
        definition_set=definition_set,
        technical_set=technical_set,
        chunk_spread=chunk_spread,
        total_chunks=total_chunks,
    )

    filtered = filter_candidates(scored, min_score=min_score, top_k=top_k * 2 if top_k > 0 else None)

    # 11. Normalize & Merge into Display Forms
    candidate_freqs = {c["candidate"]: c["frequency"] for c in filtered}
    merged_groups = merge_candidates(candidate_freqs)

    final_concepts_dict: dict[str, float] = {}
    for item in filtered:
        cand = item["candidate"]
        canon_key = item["normalized"]
        if canon_key in merged_groups:
            disp = merged_groups[canon_key]["display"]
            if disp not in final_concepts_dict or item["final_score"] > final_concepts_dict[disp]:
                final_concepts_dict[disp] = item["final_score"]

    if top_k > 0 and len(final_concepts_dict) > top_k:
        top_by_score = sorted(final_concepts_dict.keys(), key=lambda x: final_concepts_dict[x], reverse=True)[:top_k]
        sorted_concepts = sorted(top_by_score, key=lambda x: x.lower())
    else:
        sorted_concepts = sorted(list(final_concepts_dict.keys()), key=lambda x: x.lower())

    # 12. Save output
    save_concepts(sorted_concepts, output_file)

    return sorted_concepts


def main():
    parser = argparse.ArgumentParser(
        description="NLP technical concept extractor for textbook chunks."
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to input chunks JSON file (e.g. dbms_chunks.json, compiler_chunks.json)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to output concepts JSON file"
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=0,
        help="Max top concept terms to output (default: 0 = all valid concepts)"
    )
    parser.add_argument(
        "--min-score", "-s",
        type=float,
        default=3.0,
        help="Minimum score threshold for candidates (default: 3.0)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="Maximum chunks to process (0 = process all chunks)"
    )

    args = parser.parse_args()

    extract_concepts_nlp(
        input_file=args.input,
        output_file=args.output,
        limit=args.limit,
        top_k=args.top_k,
        min_score=args.min_score,
    )


if __name__ == "__main__":
    main()
