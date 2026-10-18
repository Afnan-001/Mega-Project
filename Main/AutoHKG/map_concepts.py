from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
from dotenv import load_dotenv

MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

# Load Environment Variables
load_dotenv()

DATA_DIR = MAIN_DIR / "outputs" / "data"
DEFAULT_CONCEPTS = DATA_DIR / "clean_concepts.json"
DEFAULT_CHUNKS = DATA_DIR / "content_chunks.json"
DEFAULT_EMBEDDINGS = DATA_DIR / "chunk_embeddings.npy"

OUTPUT_MAP = DATA_DIR / "concept_chunk_map.json"
OUTPUT_SCORES = DATA_DIR / "concept_chunk_scores.json"
OUTPUT_GROUNDED_CONCEPTS = DATA_DIR / "mapped_concepts.json"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")


def normalize_vector(vec: np.ndarray) -> np.ndarray:
    """Ensure vector is unit L2 normalized for cosine similarity via dot product."""
    norm = np.linalg.norm(vec, axis=-1, keepdims=True)
    norm = np.where(norm == 0, 1.0, norm)
    return vec / norm


def embed_concepts_local(concepts: list[str]) -> np.ndarray:
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            f"❌ sentence-transformers or torch not installed: {e}\n"
            "Please run: pip install sentence-transformers torch"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"⚡ Encoding {len(concepts)} concept terms using '{EMBEDDING_MODEL}' on {device}...")

    model = SentenceTransformer(EMBEDDING_MODEL, device=device)
    embeddings = model.encode(
        concepts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    return np.array(embeddings, dtype=np.float32)


def detect_knee_elbow_similarity(sorted_sims: np.ndarray, candidate_window: int = 50) -> float:
    """
    Detects the elbow/knee point in the descending similarity curve using maximum distance to the secant line.
    """
    # Restrict curve calculation to candidate window (similarity >= 0.30 or top K)
    valid_mask = sorted_sims >= 0.30
    sub_sims = sorted_sims[valid_mask] if np.any(valid_mask) else sorted_sims

    if len(sub_sims) > candidate_window:
        sub_sims = sub_sims[:candidate_window]

    n_points = len(sub_sims)
    if n_points <= 2:
        return float(sub_sims[-1]) if n_points > 0 else 0.60

    # Curve points P_i = (x_i, y_i) where x is index 1..N and y is similarity
    x = np.arange(1, n_points + 1, dtype=np.float32)
    y = sub_sims.astype(np.float32)

    # Line P1 to PN
    p1 = np.array([x[0], y[0]])
    p2 = np.array([x[-1], y[-1]])

    # Perpendicular distance from each point to the secant line P1-P2
    line_vec = p2 - p1
    line_len = np.linalg.norm(line_vec)
    if line_len == 0:
        return float(y[0])

    line_unit = line_vec / line_len

    distances = []
    for i in range(n_points):
        p = np.array([x[i], y[i]])
        vec_p1_p = p - p1
        proj_len = np.dot(vec_p1_p, line_unit)
        proj_vec = proj_len * line_unit
        perp_vec = vec_p1_p - proj_vec
        distances.append(np.linalg.norm(perp_vec))

    knee_idx = int(np.argmax(distances))
    return float(y[knee_idx])


def map_and_prune_concepts(
    concepts_file: Path,
    chunks_file: Path,
    embeddings_file: Path,
    min_rejection_similarity: float = 0.60,
    max_chunks_cap: int = 25,
) -> tuple[dict, dict, list]:
    print("=" * 60)
    print("  Adaptive Knee/Elbow Cosine-Similarity Concept Mapper & Pruner")
    print("=" * 60)
    print(f"[INPUT]  Concepts File     : {concepts_file}")
    print(f"[INPUT]  Chunks File       : {chunks_file}")
    print(f"[INPUT]  Embeddings File   : {embeddings_file}")
    print(f"[CONFIG] Rejection Floor   : {min_rejection_similarity}")
    print(f"[CONFIG] Max Chunks Cap    : {max_chunks_cap}")

    if not concepts_file.exists():
        raise FileNotFoundError(f"Missing concepts file: {concepts_file}")
    if not chunks_file.exists():
        raise FileNotFoundError(f"Missing chunks file: {chunks_file}")
    if not embeddings_file.exists():
        raise FileNotFoundError(f"Missing embeddings file: {embeddings_file}")

    # Load Concepts
    with open(concepts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "concepts" in data:
        concepts = data["concepts"]
    elif isinstance(data, list):
        concepts = [c["concept"] if isinstance(c, dict) else c for c in data]
    else:
        raise ValueError("Invalid concepts JSON structure.")

    concepts = sorted(list(set(c.strip() for c in concepts if isinstance(c, str) and c.strip())))
    print(f"[INFO] Loaded {len(concepts)} unique candidate concepts.")

    # Load Chunks & Embeddings
    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    chunk_ids = [c["chunk_id"] for c in chunks]
    chunk_embeddings = np.load(embeddings_file)

    if len(chunk_ids) != chunk_embeddings.shape[0]:
        raise ValueError(
            f"Mismatch between chunk count ({len(chunk_ids)}) and embeddings shape ({chunk_embeddings.shape[0]})"
        )

    chunk_embeddings = normalize_vector(chunk_embeddings)

    # Embed Concepts
    concept_embeddings = embed_concepts_local(concepts)
    concept_embeddings = normalize_vector(concept_embeddings)

    # Calculate Cosine Similarity Matrix: [num_concepts, num_chunks]
    print("📐 Computing Cosine Similarity Matrix...")
    similarity_matrix = np.dot(concept_embeddings, chunk_embeddings.T)

    concept_chunk_map = {}
    concept_chunk_scores = {}
    grounded_concepts = []

    pruned_count = 0

    for i, concept in enumerate(concepts):
        sims = similarity_matrix[i]

        # 1. Sort chunks by similarity descending
        sorted_indices = np.argsort(-sims)
        sorted_sims = sims[sorted_indices]
        max_sim = float(sorted_sims[0]) if len(sorted_sims) > 0 else 0.0

        # 2. Rejection Rule: If max similarity < 0.60, reject concept
        if max_sim < min_rejection_similarity:
            pruned_count += 1
            continue

        # 3. Detect Knee/Elbow Point in similarity curve
        elbow_sim = detect_knee_elbow_similarity(sorted_sims)
        final_threshold = max(elbow_sim, min_rejection_similarity)

        # 4. Keep all chunks above final threshold
        qualifying_mask = sorted_sims >= final_threshold
        qualifying_indices = sorted_indices[qualifying_mask]

        # 5. Cap retained chunks at top 25 if more qualify; retain all if <= 25
        if len(qualifying_indices) > max_chunks_cap:
            retained_indices = qualifying_indices[:max_chunks_cap]
        else:
            retained_indices = qualifying_indices

        mapped_chunk_ids = [chunk_ids[idx] for idx in retained_indices]
        mapped_scores = [
            {"chunk_id": chunk_ids[idx], "similarity": round(float(sims[idx]), 4)}
            for idx in retained_indices
        ]

        concept_chunk_map[concept] = mapped_chunk_ids
        concept_chunk_scores[concept] = mapped_scores
        grounded_concepts.append(concept)

    # Save Output Files
    OUTPUT_MAP.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_MAP, "w", encoding="utf-8") as f:
        json.dump(concept_chunk_map, f, indent=4, ensure_ascii=False)

    with open(OUTPUT_SCORES, "w", encoding="utf-8") as f:
        json.dump(concept_chunk_scores, f, indent=4, ensure_ascii=False)

    with open(OUTPUT_GROUNDED_CONCEPTS, "w", encoding="utf-8") as f:
        json.dump({"concepts": grounded_concepts}, f, indent=4, ensure_ascii=False)

    print("=" * 60)
    print("  CONCEPT-TO-CHUNK ADAPTIVE MAPPING & PRUNING SUMMARY")
    print("=" * 60)
    print(f"📦 Total Candidate Concepts Evaluated : {len(concepts)}")
    print(f"✅ Grounded Concepts Retained         : {len(grounded_concepts)}")
    print(f"❌ Rejected Concepts (Max Sim < {min_rejection_similarity}) : {pruned_count}")
    print(f"💾 Saved Chunk Map         : {OUTPUT_MAP}")
    print(f"💾 Saved Similarity Scores : {OUTPUT_SCORES}")
    print(f"💾 Saved Grounded Concepts  : {OUTPUT_GROUNDED_CONCEPTS}")
    print("=" * 60)

    return concept_chunk_map, concept_chunk_scores, grounded_concepts


def main():
    parser = argparse.ArgumentParser(
        description="Source-Grounded Concept-to-Chunk Vector Similarity Mapper & Pruner."
    )
    parser.add_argument(
        "--concepts", "-c",
        type=Path,
        default=DEFAULT_CONCEPTS,
        help="Path to clean_concepts.json"
    )
    parser.add_argument(
        "--chunks", "-k",
        type=Path,
        default=DEFAULT_CHUNKS,
        help="Path to content_chunks.json"
    )
    parser.add_argument(
        "--embeddings", "-e",
        type=Path,
        default=DEFAULT_EMBEDDINGS,
        help="Path to chunk_embeddings.npy"
    )
    parser.add_argument(
        "--min-rejection", "-s",
        type=float,
        default=0.60,
        help="Minimum rejection similarity floor (default: 0.60)"
    )
    parser.add_argument(
        "--max-chunks", "-m",
        type=int,
        default=25,
        help="Maximum chunks cap per concept (default: 25)"
    )

    args = parser.parse_args()

    map_and_prune_concepts(
        concepts_file=args.concepts,
        chunks_file=args.chunks,
        embeddings_file=args.embeddings,
        min_rejection_similarity=args.min_rejection,
        max_chunks_cap=args.max_chunks,
    )


if __name__ == "__main__":
    main()
