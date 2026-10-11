"""
embed_chunks.py — Generate dense vector embeddings for all content chunks.

Backend priority (local):
  1. FlagEmbedding BGEM3FlagModel  — preferred for BAAI/bge-m3 (official library)
  2. SentenceTransformer            — fallback for all other HuggingFace models

Remote backend:
  Set USE_EMBEDDING_API=true in .env to POST to an OpenAI-compatible endpoint.

Checkpoint / Resume:
  Partial results are saved to chunk_embeddings.partial.npz after every
  CHECKPOINT_EVERY batches.  If you kill and restart the script, it reads the
  checkpoint and resumes from the next un-processed batch automatically.
  The checkpoint is deleted once the final .npy is written successfully.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

# Force UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

MAIN_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = MAIN_DIR / "outputs" / "data"

INPUT_FILE       = DATA_DIR / "content_chunks.json"
INDEX_FILE       = DATA_DIR / "chunk_index.json"
EMBEDDINGS_FILE  = DATA_DIR / "chunk_embeddings.npy"
CHECKPOINT_FILE  = DATA_DIR / "chunk_embeddings.partial.npz"   # auto-resume

EMBEDDING_MODEL        = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
USE_API                = os.getenv("USE_EMBEDDING_API", "false").lower() in ("true", "1", "yes")
EMBEDDING_API_BASE     = os.getenv("EMBEDDING_API_BASE", "http://10.221.0.164:4000/v1")
EMBEDDING_ENDPOINT     = f"{EMBEDDING_API_BASE.rstrip('/')}/embeddings"
EMBEDDING_API_KEY      = os.getenv("EMBEDDING_API_KEY", "")
BATCH_SIZE             = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
SLEEP_BETWEEN_BATCHES  = float(os.getenv("EMBEDDING_SLEEP", "0.0"))
NORMALIZE_EMBEDDINGS   = True
CHECKPOINT_EVERY       = 5   # save checkpoint every N batches


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_chunks() -> list[dict]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    if not isinstance(chunks, list) or len(chunks) == 0:
        raise ValueError("content_chunks.json is empty or not a list.")
    return chunks


def normalize_vector(vec) -> np.ndarray:
    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr if norm == 0 else arr / norm


def _fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def save_checkpoint(vectors: list[np.ndarray], next_batch: int) -> None:
    """Persist completed batches to disk so a restart can resume."""
    if not vectors:
        return
    combined = np.vstack(vectors)
    np.savez(CHECKPOINT_FILE, embeddings=combined, next_batch=np.array(next_batch))


def load_checkpoint(total_batches: int) -> tuple[list[np.ndarray], int]:
    """
    Returns (completed_vectors, resume_batch_index).
    resume_batch_index == 0 means start from scratch.
    """
    if not CHECKPOINT_FILE.exists():
        return [], 0

    try:
        ckpt = np.load(CHECKPOINT_FILE)
        embeddings = ckpt["embeddings"]          # shape: (n_chunks_done, dim)
        next_batch = int(ckpt["next_batch"])
    except Exception as e:
        print(f"[embed] WARNING: Could not load checkpoint ({e}). Starting fresh.")
        CHECKPOINT_FILE.unlink(missing_ok=True)
        return [], 0

    if next_batch >= total_batches or embeddings.shape[0] == 0:
        # Checkpoint is stale / complete — ignore it
        CHECKPOINT_FILE.unlink(missing_ok=True)
        return [], 0

    print(f"[embed] Resuming from checkpoint: {next_batch}/{total_batches} batches done "
          f"({embeddings.shape[0]} chunks embedded so far)")
    return [embeddings], next_batch


# ---------------------------------------------------------------------------
# Remote API backend
# ---------------------------------------------------------------------------

def get_embeddings_api(texts: list[str]) -> np.ndarray:
    import requests  # noqa: PLC0415

    if not EMBEDDING_API_KEY:
        raise ValueError("EMBEDDING_API_KEY not set. Add it to your .env file.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
    }
    payload = {"model": EMBEDDING_MODEL, "input": texts}
    resp = requests.post(EMBEDDING_ENDPOINT, headers=headers, json=payload, timeout=120)

    if resp.status_code != 200:
        raise RuntimeError(f"Embedding API error {resp.status_code}: {resp.text}")

    data = resp.json()
    if "data" not in data:
        raise ValueError(f"Invalid API response (no 'data' key): {data}")

    embeddings = []
    for item in data["data"]:
        vec = item["embedding"]
        if NORMALIZE_EMBEDDINGS:
            vec = normalize_vector(vec).tolist()
        embeddings.append(vec)

    return np.array(embeddings, dtype=np.float32)


# ---------------------------------------------------------------------------
# Local backend — FlagEmbedding (bge-m3 official)
# ---------------------------------------------------------------------------

def _load_flag_model():
    try:
        from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "FlagEmbedding is not installed.\n"
            "Run:  pip install FlagEmbedding"
        ) from exc

    # Determine device
    try:
        import torch  # noqa: PLC0415
        if torch.cuda.is_available():
            device      = "cuda:0"
            gpu_name    = torch.cuda.get_device_name(0)
            vram_gb     = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"[embed] GPU detected  : {gpu_name} ({vram_gb:.1f} GB VRAM)")
        else:
            device   = "cpu"
            print("[embed] WARNING: CUDA not available — running on CPU (slow).")
            print("[embed]          Install CUDA PyTorch:")
            print("[embed]            pip install torch --index-url https://download.pytorch.org/whl/cu124 --upgrade")
    except ImportError:
        device = "cpu"
        print("[embed] WARNING: torch not installed — running on CPU.")

    use_fp16 = (device != "cpu")
    print(f"[embed] Loading BGEM3FlagModel '{EMBEDDING_MODEL}' on {device} (fp16={use_fp16}) ...")
    print("[embed] (This may take 10–30 seconds to load weights — please wait)")
    sys.stdout.flush()

    model = BGEM3FlagModel(
        EMBEDDING_MODEL,
        use_fp16=use_fp16,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        devices=[device],
    )
    print(f"[embed] Model loaded successfully on {device}.")
    return model, device


def _load_st_model():
    try:
        import torch  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers or torch not installed.\n"
            "Run:  pip install sentence-transformers torch"
        ) from exc

    if torch.cuda.is_available():
        device   = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[embed] GPU: {gpu_name}")
    else:
        device = "cpu"
        print("[embed] WARNING: CUDA not available — running on CPU.")

    print(f"[embed] Loading SentenceTransformer '{EMBEDDING_MODEL}' on {device} ...")
    sys.stdout.flush()
    model = SentenceTransformer(EMBEDDING_MODEL, device=device)
    print(f"[embed] Model loaded on {device}.")
    return model, device


def _encode_flag(model, batch: list[str]) -> np.ndarray:
    out = model.encode(
        batch,
        batch_size=len(batch),
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return np.array(out["dense_vecs"], dtype=np.float32)


def _encode_st(model, batch: list[str]) -> np.ndarray:
    vecs = model.encode(
        batch,
        batch_size=len(batch),
        show_progress_bar=False,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
    )
    return np.array(vecs, dtype=np.float32)


# ---------------------------------------------------------------------------
# Main local embedding loop (with checkpoint/resume)
# ---------------------------------------------------------------------------

def get_embeddings_local(texts: list[str]) -> np.ndarray:
    is_bge_m3 = "bge-m3" in EMBEDDING_MODEL.lower()

    # Load model
    if is_bge_m3:
        try:
            model, device = _load_flag_model()
            encode_fn = lambda batch: _encode_flag(model, batch)   # noqa: E731
            backend_name = f"FlagEmbedding BGEM3 ({device})"
        except ImportError as e:
            print(f"[embed] WARNING: {e}")
            print("[embed] Falling back to SentenceTransformer.")
            model, device = _load_st_model()
            encode_fn = lambda batch: _encode_st(model, batch)     # noqa: E731
            backend_name = f"SentenceTransformer fallback ({device})"
    else:
        model, device = _load_st_model()
        encode_fn = lambda batch: _encode_st(model, batch)         # noqa: E731
        backend_name = f"SentenceTransformer ({device})"

    print(f"[embed] Backend : {backend_name}")

    total = len(texts)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    # --- Resume from checkpoint if available ---
    completed_vecs, start_batch = load_checkpoint(total_batches)

    print(f"[embed] Encoding {total} chunks | {total_batches} batches "
          f"(batch_size={BATCH_SIZE}) | resume_batch={start_batch}")
    print()

    batch_times: list[float] = []

    for batch_idx in range(start_batch, total_batches):
        start_char = batch_idx * BATCH_SIZE
        batch = texts[start_char : start_char + BATCH_SIZE]

        t0 = time.time()
        vecs = encode_fn(batch)
        elapsed = time.time() - t0

        completed_vecs.append(vecs)
        batch_times.append(elapsed)

        # Progress line
        done = batch_idx + 1
        pct = int(done / total_batches * 100)
        avg_t = sum(batch_times) / len(batch_times)
        remaining = (total_batches - done) * avg_t
        eta_str = _fmt_time(remaining)

        print(
            f"\r[embed] Batch {done}/{total_batches} ({pct}%) | "
            f"{elapsed:.1f}s/batch | ETA {eta_str}          ",
            end="",
            flush=True,
        )

        # Checkpoint every N batches
        if (done % CHECKPOINT_EVERY == 0) or done == total_batches:
            save_checkpoint(completed_vecs, done)

        if SLEEP_BETWEEN_BATCHES > 0:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    print()  # newline after progress
    return np.vstack(completed_vecs)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Chunk Embeddings Generator")
    print("=" * 60)
    print(f"[INPUT]  Chunks     : {INPUT_FILE}")
    print(f"[OUTPUT] Index      : {INDEX_FILE}")
    print(f"[OUTPUT] Embeddings : {EMBEDDINGS_FILE}")
    print(f"[MODEL]  {EMBEDDING_MODEL}")
    print(f"[MODE]   {'API' if USE_API else 'Local (HuggingFace)'}")
    print(f"[CKPT]   Saves every {CHECKPOINT_EVERY} batches → {CHECKPOINT_FILE.name}")
    print()

    chunks = load_chunks()
    print(f"[embed] Loaded {len(chunks)} chunks")

    texts = [c["text"] for c in chunks]
    metadata = [
        {
            "chunk_id":    c["chunk_id"],
            "book_name":   c.get("book_name", ""),
            "page_number": c.get("page_number", -1),
        }
        for c in chunks
    ]

    # ---- Embed ----
    if USE_API:
        print(f"[embed] Using API endpoint: {EMBEDDING_ENDPOINT}")
        all_vectors: list[np.ndarray] = []
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(texts), BATCH_SIZE):
            batch_no = i // BATCH_SIZE + 1
            batch = texts[i : i + BATCH_SIZE]
            print(f"[embed] API batch {batch_no}/{total_batches} ({len(batch)} chunks)")
            try:
                vecs = get_embeddings_api(batch)
            except Exception as exc:
                print(f"[embed] ERROR at batch {batch_no}: {exc}")
                raise
            all_vectors.append(vecs)
            time.sleep(SLEEP_BETWEEN_BATCHES)

        embedding_matrix = np.vstack(all_vectors)
    else:
        embedding_matrix = get_embeddings_local(texts)

    # ---- Save final outputs ----
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    np.save(EMBEDDINGS_FILE, embedding_matrix)

    # Clean up checkpoint now that we have the final file
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("[embed] Checkpoint file removed (no longer needed).")

    print()
    print("=" * 60)
    print("  Embedding generation complete!")
    print("=" * 60)
    print(f"[OUTPUT] chunk_index.json     : {len(metadata)} entries")
    print(f"[OUTPUT] chunk_embeddings.npy : shape {embedding_matrix.shape}")
    print(f"[OUTPUT] Saved to: {DATA_DIR}")


if __name__ == "__main__":
    main()
