import argparse
import json
import sys
import time
from pathlib import Path

# Force UTF-8 stdout encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add MAIN_DIR to sys.path so `llm.py` can be imported
MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from llm import LLM
DATA_DIR = MAIN_DIR / "outputs" / "data"

INPUT_FILE = DATA_DIR / "mapped_concepts.json"
CHUNK_MAP_FILE = DATA_DIR / "concept_chunk_map.json"
CHUNKS_FILE = DATA_DIR / "content_chunks.json"
OUTPUT_FILE = DATA_DIR / "enriched_concepts.json"

# ----------------------------
# Config Defaults
# ----------------------------
TOP_EVIDENCE_CHUNKS = 4
MAX_CHARS_PER_CHUNK = 750
MIN_EDGE_CONFIDENCE = 0.60

SYS_PROMPT = (
    "You are a domain-agnostic educational Knowledge Graph expert. "
    "You build source-grounded educational concept hierarchies using only the provided textbook chunks."
)

PROMPT = """
You are building a source-grounded educational Knowledge Graph for arbitrary educational subject domains.

The graph should follow this structure:

Coarse-Grained Category Node
    → CONTAINS
Fine-Grained Concept Node

The CURRENT CONCEPT is the fine-grained concept.

Your task is to identify:
1. One coarse-grained category for the current concept.
2. Strong prerequisite concepts required before learning the current concept.

STRICT RULES:
1. Use ONLY concepts from the provided ALL CONCEPTS list.
2. Use ONLY the provided SOURCE CHUNKS as evidence.
3. Do NOT use outside knowledge.
4. Do NOT hallucinate or create new concepts.
5. The current concept itself must NOT be used as its own category or prerequisite.
6. Every category/prerequisite relationship must cite a valid source chunk ID.
7. Every relationship must include a short supporting evidence text from the source chunks.
8. If source evidence is weak or missing, do NOT create that relationship.
9. Confidence must be between 0.0 and 1.0.
10. Return ONLY valid JSON. No explanation.

---

CURRENT CONCEPT:
{concept}

ALL CONCEPTS:
{all_concepts}

---

SOURCE CHUNKS:
{source_chunks}

---

OUTPUT JSON ONLY:

{{
  "concept": "{concept}",
  "node_type": "fine_grained_concept",
  "coarse_grained_category": {{
    "concept": "",
    "confidence": 0.0,
    "evidence_chunk": "",
    "evidence_text": ""
  }},
  "prerequisite_edges": [
    {{
      "prerequisite": "",
      "confidence": 0.0,
      "evidence_chunk": "",
      "evidence_text": ""
    }}
  ]
}}
"""


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Empty file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_parse_json(text):
    try:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return json.loads(text)
    except Exception:
        return None


def build_chunk_lookup(chunks):
    return {
        c["chunk_id"]: c.get("text", "")
        for c in chunks
        if c.get("chunk_id")
    }


def format_source_chunks(concept_name, concept_chunk_map, chunk_lookup):
    chunk_ids = concept_chunk_map.get(concept_name, [])
    selected_chunk_ids = []
    blocks = []

    for cid in chunk_ids[:TOP_EVIDENCE_CHUNKS]:
        text = chunk_lookup.get(cid, "")
        if not text:
            continue

        selected_chunk_ids.append(cid)
        text = text.replace("\n", " ").strip()
        text = text[:MAX_CHARS_PER_CHUNK]
        blocks.append(f"[{cid}]\n{text}")

    if not blocks:
        return "NO SOURCE CHUNKS AVAILABLE.", selected_chunk_ids

    return "\n\n".join(blocks), selected_chunk_ids


def parse_chunk_page(chunk_id):
    try:
        parts = chunk_id.split("_")
        for part in parts:
            if part.startswith("p") and part[1:].isdigit():
                return int(part[1:])
    except Exception:
        pass
    return None


def get_candidate_concepts(
    concept_name,
    all_concept_names,
    all_concepts_set,
    concept_chunk_map,
    selected_chunk_ids,
    source_chunks_text,
    page_proximity_window=10
):
    candidate_pool = set()

    # Signal 1: Co-occurrence in source chunk text
    source_text_lower = source_chunks_text.lower()
    for c in all_concept_names:
        if c == concept_name:
            continue
        if c.lower() in source_text_lower:
            candidate_pool.add(c)

    # Signal 2: Section / Page Proximity
    target_pages = [
        parse_chunk_page(cid)
        for cid in selected_chunk_ids
        if parse_chunk_page(cid) is not None
    ]

    if target_pages:
        min_page = min(target_pages) - page_proximity_window
        max_page = max(target_pages) + page_proximity_window

        for other_concept, mapped_chunks in concept_chunk_map.items():
            if other_concept == concept_name or other_concept not in all_concepts_set:
                continue

            for cid in mapped_chunks[:5]:
                page = parse_chunk_page(cid)
                if page is not None and min_page <= page <= max_page:
                    candidate_pool.add(other_concept)
                    break

    if len(candidate_pool) < 10:
        for c in all_concept_names:
            if c != concept_name:
                candidate_pool.add(c)
            if len(candidate_pool) >= 30:
                break

    return sorted(list(candidate_pool))


def verify_citation_grounding(evidence_text, evidence_chunk, chunk_lookup):
    chunk_text = chunk_lookup.get(evidence_chunk, "").lower()
    ev_text = evidence_text.lower().strip()

    if not ev_text or not chunk_text:
        return False

    if ev_text in chunk_text:
        return True

    ev_words = set(ev_text.split())
    chunk_words = set(chunk_text.split())

    if not ev_words:
        return False

    overlap_ratio = len(ev_words & chunk_words) / len(ev_words)
    return overlap_ratio >= 0.70


def validate_category(raw_category, concept_name, all_concepts_set, valid_chunk_ids, chunk_lookup):
    if not isinstance(raw_category, dict):
        return None

    category = raw_category.get("concept", "")
    confidence = raw_category.get("confidence", 0.0)
    evidence_chunk = raw_category.get("evidence_chunk", "")
    evidence_text = raw_category.get("evidence_text", "")

    if not isinstance(category, str):
        return None

    category = category.strip()

    if isinstance(evidence_chunk, str):
        evidence_chunk = evidence_chunk.strip("[] \t\r\n")

    if not category or category == concept_name or category not in all_concepts_set:
        return None

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    if confidence < MIN_EDGE_CONFIDENCE:
        return None

    if evidence_chunk not in valid_chunk_ids:
        return None

    if not isinstance(evidence_text, str) or not evidence_text.strip():
        return None

    if not verify_citation_grounding(evidence_text, evidence_chunk, chunk_lookup):
        return None

    return {
        "concept": category,
        "confidence": round(confidence, 3),
        "evidence_chunk": evidence_chunk,
        "evidence_text": evidence_text.strip()
    }


def validate_prerequisite_edges(raw_edges, concept_name, all_concepts_set, valid_chunk_ids, chunk_lookup):
    if not isinstance(raw_edges, list):
        return []

    valid_edges = []
    seen = set()

    for edge in raw_edges:
        if not isinstance(edge, dict):
            continue

        prereq = edge.get("prerequisite", "")
        confidence = edge.get("confidence", 0.0)
        evidence_chunk = edge.get("evidence_chunk", "")
        evidence_text = edge.get("evidence_text", "")

        if not isinstance(prereq, str):
            continue

        prereq = prereq.strip()

        if isinstance(evidence_chunk, str):
            evidence_chunk = evidence_chunk.strip("[] \t\r\n")

        if not prereq or prereq == concept_name or prereq not in all_concepts_set or prereq in seen:
            continue

        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        if confidence < MIN_EDGE_CONFIDENCE:
            continue

        if evidence_chunk not in valid_chunk_ids:
            continue

        if not isinstance(evidence_text, str) or not evidence_text.strip():
            continue

        if not verify_citation_grounding(evidence_text, evidence_chunk, chunk_lookup):
            continue

        valid_edges.append({
            "prerequisite": prereq,
            "confidence": round(confidence, 3),
            "evidence_chunk": evidence_chunk,
            "evidence_text": evidence_text.strip()
        })

        seen.add(prereq)

    return valid_edges


def validate_enrichment(updated, concept_name, all_concepts_set, valid_chunk_ids, chunk_lookup):
    if not isinstance(updated, dict):
        return {
            "concept": concept_name,
            "node_type": "fine_grained_concept",
            "coarse_grained_category": [],
            "parent_concept": [],
            "category_edge": None,
            "prerequisites": [],
            "prerequisite_edges": []
        }

    category_edge = validate_category(
        raw_category=updated.get("coarse_grained_category"),
        concept_name=concept_name,
        all_concepts_set=all_concepts_set,
        valid_chunk_ids=valid_chunk_ids,
        chunk_lookup=chunk_lookup
    )

    prerequisite_edges = validate_prerequisite_edges(
        raw_edges=updated.get("prerequisite_edges"),
        concept_name=concept_name,
        all_concepts_set=all_concepts_set,
        valid_chunk_ids=valid_chunk_ids,
        chunk_lookup=chunk_lookup
    )

    coarse_grained_category = [category_edge["concept"]] if category_edge else []
    parent_concept = coarse_grained_category
    prerequisites = [p["prerequisite"] for p in prerequisite_edges]

    return {
        "concept": concept_name,
        "node_type": "fine_grained_concept",
        "coarse_grained_category": coarse_grained_category,
        "parent_concept": parent_concept,
        "prerequisites": prerequisites,
        "category_edge": category_edge,
        "prerequisite_edges": prerequisite_edges
    }


def enrich_concept(concept_obj, all_concepts, all_concepts_set, concept_chunk_map, chunk_lookup, llm):
    concept_name = concept_obj["concept"]

    source_chunks, valid_chunk_ids = format_source_chunks(
        concept_name=concept_name,
        concept_chunk_map=concept_chunk_map,
        chunk_lookup=chunk_lookup
    )

    if not valid_chunk_ids or source_chunks == "NO SOURCE CHUNKS AVAILABLE.":
        print(f"  [UNGROUNDED] {concept_name} has 0 valid chunks.")
        return {
            "concept": concept_name,
            "node_type": "fine_grained_concept",
            "coarse_grained_category": [],
            "parent_concept": [],
            "category_edge": None,
            "prerequisites": [],
            "prerequisite_edges": []
        }

    candidate_concepts = get_candidate_concepts(
        concept_name=concept_name,
        all_concept_names=all_concepts,
        all_concepts_set=all_concepts_set,
        concept_chunk_map=concept_chunk_map,
        selected_chunk_ids=valid_chunk_ids,
        source_chunks_text=source_chunks,
        page_proximity_window=10
    )

    for attempt in range(3):
        try:
            prompt = PROMPT.format(
                concept=concept_name,
                all_concepts=", ".join(candidate_concepts),
                source_chunks=source_chunks
            )

            response = llm.get_response(prompt)
            updated = safe_parse_json(response)

            if not updated:
                raise ValueError("Invalid JSON from LLM")

            validated = validate_enrichment(
                updated=updated,
                concept_name=concept_name,
                all_concepts_set=all_concepts_set,
                valid_chunk_ids=set(valid_chunk_ids),
                chunk_lookup=chunk_lookup
            )

            return validated

        except Exception as e:
            print(f"  ⚠️ Retry {attempt + 1} failed for {concept_name}: {e}")
            time.sleep(1)

    return {
        "concept": concept_name,
        "node_type": "fine_grained_concept",
        "coarse_grained_category": [],
        "parent_concept": [],
        "category_edge": None,
        "prerequisites": [],
        "prerequisite_edges": []
    }


def main():
    parser = argparse.ArgumentParser(description="Enrich Concepts using LLM (Ollama or Gemini)")
    parser.add_argument("--provider", type=str, default="ollama", choices=["ollama", "gemini"], help="LLM Provider (ollama or gemini)")
    parser.add_argument("--model", type=str, default=None, help="Model name (defaults to gemini-3.8-flash for Gemini, qwen2.5:7b-instruct-q4_K_M for Ollama)")
    parser.add_argument("--sleep", type=float, default=None, help="Seconds to sleep between calls")
    args = parser.parse_args()

    model_name = args.model
    if not model_name:
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash") if args.provider == "gemini" else os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")

    sleep_time = args.sleep
    if sleep_time is None:
        sleep_time = 0.5 if args.provider == "ollama" else 1.0

    print("============================================================")
    print("  Source-Grounded Concept Hierarchy & Prerequisite Enricher")
    print("============================================================")
    print(f"[PROVIDER] {args.provider.upper()} (Model: {model_name})")
    print(f"[SLEEP]    {sleep_time}s between LLM calls")
    print(f"[INPUT]    {INPUT_FILE}")
    print(f"[OUTPUT]   {OUTPUT_FILE}")

    concepts = load_json(INPUT_FILE)
    concept_chunk_map = load_json(CHUNK_MAP_FILE)
    chunks = load_json(CHUNKS_FILE)

    chunk_lookup = build_chunk_lookup(chunks)

    if isinstance(concepts, dict) and "concepts" in concepts:
        concepts = concepts["concepts"]
    all_concept_names = [
        c["concept"] if isinstance(c, dict) else c
        for c in concepts
        if (isinstance(c, dict) and c.get("concept")) or isinstance(c, str)
    ]
    all_concepts_set = set(all_concept_names)

    llm = LLM(
        sys_msg=SYS_PROMPT,
        model_name=model_name,
        temperature=0.0,
        provider=args.provider
    )

    # Resume support
    enriched_dict = {}
    if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
        try:
            existing = load_json(OUTPUT_FILE)
            for item in existing:
                if isinstance(item, dict) and item.get("concept"):
                    enriched_dict[item["concept"]] = item
            print(f"[RESUME]   Found existing output with {len(enriched_dict)} processed concepts.")
        except Exception:
            pass

    print(f"\n✅ Loaded {len(all_concept_names)} grounded concepts.")
    print("\n--- STARTING CONCEPT ENRICHMENT ---\n")

    start_time = time.time()
    for i, concept in enumerate(concepts):
        concept_name = concept["concept"] if isinstance(concept, dict) else concept
        if not isinstance(concept_name, str) or not concept_name.strip():
            continue
        concept_name = concept_name.strip()
        concept_obj = {"concept": concept_name}

        if concept_name in enriched_dict:
            print(f"[{i + 1}/{len(concepts)}] Skipped (already done): {concept_name}")
            continue

        t0 = time.time()
        print(f"[{i + 1}/{len(concepts)}] Enriching: {concept_name} ...", end="", flush=True)

        updated = enrich_concept(
            concept_obj=concept_obj,
            all_concepts=all_concept_names,
            all_concepts_set=all_concepts_set,
            concept_chunk_map=concept_chunk_map,
            chunk_lookup=chunk_lookup,
            llm=llm
        )

        dt = time.time() - t0
        cat_str = updated["coarse_grained_category"][0] if updated["coarse_grained_category"] else "None"
        prereq_cnt = len(updated["prerequisites"])
        print(f" ({dt:.1f}s) | Cat: {cat_str} | Prereqs: {prereq_cnt}")

        enriched_dict[concept_name] = updated

        # Save checkpoint periodically
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ordered_enriched = [enriched_dict[c] for c in all_concept_names if c in enriched_dict]
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(ordered_enriched, f, indent=4, ensure_ascii=False)

        if sleep_time > 0:
            time.sleep(sleep_time)

    total_time = time.time() - start_time
    final_enriched = [enriched_dict[c] for c in all_concept_names if c in enriched_dict]

    concepts_with_category = sum(1 for c in final_enriched if c.get("coarse_grained_category"))
    concepts_with_prereqs = sum(1 for c in final_enriched if c.get("prerequisites"))
    total_prereq_edges = sum(len(c.get("prerequisite_edges", [])) for c in final_enriched)
    total_category_edges = sum(1 for c in final_enriched if c.get("category_edge"))

    print("\n============================================================")
    print("  ENRICHMENT COMPLETE!")
    print("============================================================")
    print(f"📦 Total Elapsed Time  : {total_time / 60:.2f} mins")
    print(f"📦 Saved Output        : {OUTPUT_FILE}")
    print(f"📦 Total Concepts      : {len(final_enriched)}")
    print(f"✅ With Category       : {concepts_with_category}")
    print(f"✅ With Prerequisites  : {concepts_with_prereqs}")
    print(f"✅ Category Edges      : {total_category_edges}")
    print(f"✅ Prerequisite Edges  : {total_prereq_edges}")
    print("============================================================")


if __name__ == "__main__":
    main()
