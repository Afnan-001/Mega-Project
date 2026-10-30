"""
retriever.py — Semantic and graph-augmented context retriever for Cognitive-RAG.
Fetches concept neighborhoods from knowledge_graph.gml and ranks grounded textbook chunks.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("corgag.retriever")

MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

OUTPUTS_DIR = MAIN_DIR / "outputs"
DATA_DIR = OUTPUTS_DIR / "data"

# File path candidates
GRAPH_CANDIDATES = [
    OUTPUTS_DIR / "graph_model" / "knowledge_graph.gml",
    MAIN_DIR / "graph_model" / "knowledge_graph.gml",
]
CHUNK_MAP_FILE = DATA_DIR / "concept_chunk_map.json"
CHUNK_INDEX_FILE = DATA_DIR / "chunk_index.json"
CHUNK_EMBEDDINGS_FILE = DATA_DIR / "chunk_embeddings.npy"

CHUNKS_FILE_CANDIDATES = [
    DATA_DIR / "content_chunks.json",
    DATA_DIR / "dbms_chunks.json",
]

# Embedding configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
USE_EMBEDDING_API = os.getenv("USE_EMBEDDING_API", "false").lower() == "true"
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", "").rstrip("/")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")

# Lazy singletons
_GRAPH: Optional[nx.DiGraph] = None
_CHUNK_LOOKUP: Optional[Dict[str, str]] = None
_CONCEPT_CHUNK_MAP: Optional[Dict[str, List[str]]] = None
_CHUNK_INDEX: Optional[List[Dict[str, Any]]] = None
_CHUNK_ID_TO_ROW: Optional[Dict[str, int]] = None
_CHUNK_EMBEDDINGS: Optional[np.ndarray] = None
_LOCAL_MODEL = None


def normalize_vector(vec: np.ndarray) -> np.ndarray:
    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr if norm == 0 else arr / norm


def get_graph() -> nx.DiGraph:
    global _GRAPH
    if _GRAPH is not None:
        return _GRAPH

    for path in GRAPH_CANDIDATES:
        if path.exists():
            try:
                _GRAPH = nx.read_gml(path)
                return _GRAPH
            except Exception as e:
                logger.warning("Failed to read graph from %s: %s", path, e)

    # Empty graph fallback
    _GRAPH = nx.DiGraph()
    return _GRAPH


def get_chunk_lookup() -> Dict[str, str]:
    global _CHUNK_LOOKUP
    if _CHUNK_LOOKUP is not None:
        return _CHUNK_LOOKUP

    for path in CHUNKS_FILE_CANDIDATES:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                _CHUNK_LOOKUP = {c["chunk_id"]: c.get("text", "") for c in chunks if "chunk_id" in c}
                return _CHUNK_LOOKUP
            except Exception as e:
                logger.warning("Failed to read chunks from %s: %s", path, e)

    _CHUNK_LOOKUP = {}
    return _CHUNK_LOOKUP


def get_concept_chunk_map() -> Dict[str, List[str]]:
    global _CONCEPT_CHUNK_MAP
    if _CONCEPT_CHUNK_MAP is not None:
        return _CONCEPT_CHUNK_MAP

    if CHUNK_MAP_FILE.exists():
        try:
            with open(CHUNK_MAP_FILE, "r", encoding="utf-8") as f:
                _CONCEPT_CHUNK_MAP = json.load(f)
                return _CONCEPT_CHUNK_MAP
        except Exception as e:
            logger.warning("Failed to read concept chunk map: %s", e)

    _CONCEPT_CHUNK_MAP = {}
    return _CONCEPT_CHUNK_MAP


def get_chunk_embeddings_data() -> Tuple[Dict[str, int], Optional[np.ndarray]]:
    global _CHUNK_ID_TO_ROW, _CHUNK_EMBEDDINGS, _CHUNK_INDEX
    if _CHUNK_ID_TO_ROW is not None and _CHUNK_EMBEDDINGS is not None:
        return _CHUNK_ID_TO_ROW, _CHUNK_EMBEDDINGS

    if CHUNK_INDEX_FILE.exists() and CHUNK_EMBEDDINGS_FILE.exists():
        try:
            with open(CHUNK_INDEX_FILE, "r", encoding="utf-8") as f:
                _CHUNK_INDEX = json.load(f)
            _CHUNK_ID_TO_ROW = {item["chunk_id"]: i for i, item in enumerate(_CHUNK_INDEX)}
            _CHUNK_EMBEDDINGS = np.load(CHUNK_EMBEDDINGS_FILE).astype(np.float32)
            # Ensure unit L2 normalization
            norms = np.linalg.norm(_CHUNK_EMBEDDINGS, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            _CHUNK_EMBEDDINGS = _CHUNK_EMBEDDINGS / norms
            return _CHUNK_ID_TO_ROW, _CHUNK_EMBEDDINGS
        except Exception as e:
            logger.warning("Failed to load chunk embeddings: %s", e)

    _CHUNK_ID_TO_ROW = {}
    _CHUNK_EMBEDDINGS = None
    return _CHUNK_ID_TO_ROW, _CHUNK_EMBEDDINGS


def embed_query(text: str) -> np.ndarray:
    """
    Embeds query text using the same model as the chunk embeddings (default: BAAI/bge-m3).
    """
    global _LOCAL_MODEL
    if USE_EMBEDDING_API and EMBEDDING_API_BASE:
        import requests
        endpoint = f"{EMBEDDING_API_BASE}/embeddings"
        headers = {"Content-Type": "application/json"}
        if EMBEDDING_API_KEY:
            headers["Authorization"] = f"Bearer {EMBEDDING_API_KEY}"
        payload = {"model": EMBEDDING_MODEL, "input": text}
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                vec = data["data"][0]["embedding"]
                return normalize_vector(vec)
        logger.warning("Remote embedding API failed, falling back to local model.")

    if _LOCAL_MODEL is None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _LOCAL_MODEL = SentenceTransformer(EMBEDDING_MODEL, device=device)
        except Exception as e:
            logger.warning("Could not load SentenceTransformer (%s). Using pseudo-embedding.", e)
            return np.zeros((1024,), dtype=np.float32)

    vec = _LOCAL_MODEL.encode(text, normalize_embeddings=True)
    return np.array(vec, dtype=np.float32)


# ----------------------------
# Graph Traversal Helpers
# ----------------------------
def get_parents(graph: nx.DiGraph, concept: str) -> List[str]:
    if not graph or concept not in graph:
        return []
    return [
        src for src, _, data in graph.in_edges(concept, data=True)
        if data.get("relation") == "CONTAINS"
    ]


def get_prerequisites(graph: nx.DiGraph, concept: str) -> List[str]:
    if not graph or concept not in graph:
        return []
    return [
        src for src, _, data in graph.in_edges(concept, data=True)
        if data.get("relation") == "PREREQUISITE_FOR"
    ]


def get_neighbors(graph: nx.DiGraph, concept: str) -> List[str]:
    if not graph or concept not in graph:
        return []
    return [
        dst for _, dst, data in graph.out_edges(concept, data=True)
        if data.get("relation") == "PREREQUISITE_FOR"
    ]


def get_chunks_for_concept(concept: str) -> List[str]:
    mapping = get_concept_chunk_map()
    return mapping.get(concept, [])


def build_query_text(concept: str, parents: List[str], prereqs: List[str], neighbors: List[str]) -> str:
    parts = [f"Concept: {concept}"]
    if parents:
        parts.append(f"Parent categories: {', '.join(parents)}")
    if prereqs:
        parts.append(f"Prerequisite concepts: {', '.join(prereqs)}")
    return "\n".join(parts)


def rank_chunks_semantically(candidate_chunk_ids: List[str], query_text: str) -> List[Tuple[float, str]]:
    id_to_row, embeddings = get_chunk_embeddings_data()
    if embeddings is None or not id_to_row:
        # Fallback to order in candidate list
        return [(1.0 - (i * 0.01), cid) for i, cid in enumerate(candidate_chunk_ids)]

    query_vec = embed_query(query_text)
    if query_vec.shape[0] != embeddings.shape[1]:
        logger.warning(
            "Vector dimension mismatch (query %s vs chunk %s). Fallback.",
            query_vec.shape, embeddings.shape
        )
        return [(1.0 - (i * 0.01), cid) for i, cid in enumerate(candidate_chunk_ids)]

    scored = []
    for cid in candidate_chunk_ids:
        idx = id_to_row.get(cid)
        if idx is not None:
            sim = float(np.dot(query_vec, embeddings[idx]))
            scored.append((sim, cid))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


# ----------------------------
# Core Retrieval Functions
# ----------------------------
def retrieve_context(concept_name: str, max_chunks: int = 10, candidate_limit: int = 100) -> Optional[Dict[str, Any]]:
    graph = get_graph()
    chunk_lookup = get_chunk_lookup()

    parents = get_parents(graph, concept_name)
    prereqs = get_prerequisites(graph, concept_name)
    neighbors = get_neighbors(graph, concept_name)

    candidate_ids: Set[str] = set()
    candidate_ids.update(get_chunks_for_concept(concept_name))
    for p in prereqs:
        candidate_ids.update(get_chunks_for_concept(p))
    for p in parents:
        candidate_ids.update(get_chunks_for_concept(p))
    for n in neighbors:
        candidate_ids.update(get_chunks_for_concept(n))

    if not candidate_ids:
        candidate_ids = set(chunk_lookup.keys())

    candidate_list = list(candidate_ids)[:candidate_limit]
    query_text = build_query_text(concept_name, parents, prereqs, neighbors)
    scored_chunks = rank_chunks_semantically(candidate_list, query_text)

    if not scored_chunks:
        return None

    top_chunks = scored_chunks[:max_chunks]
    selected_cids = [cid for _, cid in top_chunks]
    texts = [chunk_lookup[cid] for cid in selected_cids if cid in chunk_lookup and chunk_lookup[cid]]

    if not texts:
        return None

    return {
        "concept": concept_name,
        "parents": parents,
        "prerequisites": prereqs,
        "neighbors": neighbors,
        "chunks": selected_cids,
        "scores": [{"chunk_id": cid, "similarity": round(s, 4)} for s, cid in top_chunks],
        "query_text": query_text,
        "context": "\n\n".join(texts),
    }


def retrieve_context_for_concepts(
    primary_concept: str,
    secondary_concepts: Optional[List[str]] = None,
    max_chunks: int = 12,
    candidate_limit: int = 160,
) -> Optional[Dict[str, Any]]:
    graph = get_graph()
    chunk_lookup = get_chunk_lookup()

    secondary_concepts = secondary_concepts or []
    concept_list = [primary_concept] + [c for c in secondary_concepts if c != primary_concept]

    concept_graph_context = {}
    candidate_ids: Set[str] = set()

    for c in concept_list:
        parents = get_parents(graph, c)
        prereqs = get_prerequisites(graph, c)
        neighbors = get_neighbors(graph, c)
        concept_graph_context[c] = {"parents": parents, "prerequisites": prereqs, "neighbors": neighbors}

        candidate_ids.update(get_chunks_for_concept(c))
        for p in prereqs:
            candidate_ids.update(get_chunks_for_concept(p))
        for p in parents:
            candidate_ids.update(get_chunks_for_concept(p))

    if not candidate_ids:
        candidate_ids = set(chunk_lookup.keys())

    candidate_list = list(candidate_ids)[:candidate_limit]

    query_parts = [f"Primary Concept: {primary_concept}"]
    if secondary_concepts:
        query_parts.append(f"Secondary Concepts: {', '.join(secondary_concepts)}")
    for c in concept_list:
        ctx = concept_graph_context[c]
        query_parts.append(build_query_text(c, ctx["parents"], ctx["prerequisites"], ctx["neighbors"]))

    query_text = "\n\n".join(query_parts)
    scored_chunks = rank_chunks_semantically(candidate_list, query_text)

    if not scored_chunks:
        return None

    top_chunks = scored_chunks[:max_chunks]
    selected_cids = [cid for _, cid in top_chunks]
    texts = [chunk_lookup[cid] for cid in selected_cids if cid in chunk_lookup and chunk_lookup[cid]]

    if not texts:
        return None

    return {
        "primary_concept": primary_concept,
        "secondary_concepts": [c for c in concept_list if c != primary_concept],
        "concepts": concept_list,
        "concept_graph_context": concept_graph_context,
        "chunks": selected_cids,
        "scores": [{"chunk_id": cid, "similarity": round(s, 4)} for s, cid in top_chunks],
        "query_text": query_text,
        "context": "\n\n".join(texts),
    }


# Backwards compatibility proxy for chunk_lookup
class _ChunkLookupProxy(dict):
    def get(self, key, default=""):
        return get_chunk_lookup().get(key, default)
    def __getitem__(self, key):
        return get_chunk_lookup()[key]
    def __contains__(self, key):
        return key in get_chunk_lookup()
    def keys(self):
        return get_chunk_lookup().keys()

chunk_lookup = _ChunkLookupProxy()
G = get_graph()


if __name__ == "__main__":
    test_concept = sys.argv[1] if len(sys.argv) > 1 else "Compiler"
    print(f"Retrieving context for '{test_concept}'...")
    res = retrieve_context(test_concept)
    if res:
        print(f"Found {len(res['chunks'])} chunks. Top chunk: {res['chunks'][0]}")
        print("Sample context snippet:")
        print(res["context"][:300] + "...")
    else:
        print("No context retrieved.")
