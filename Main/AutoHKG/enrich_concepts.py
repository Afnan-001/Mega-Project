import json
import time
from pathlib import Path

from llm import LLM

# ----------------------------
# Files
# ----------------------------
MAIN_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = MAIN_DIR / "outputs" / "data"

INPUT_FILE = DATA_DIR / "merged_concepts.json"
CHUNK_MAP_FILE = DATA_DIR / "concept_chunk_map.json"
CHUNKS_FILE = DATA_DIR / "dbms_chunks.json"
OUTPUT_FILE = DATA_DIR / "enriched_concepts.json"

# ----------------------------
# Config
# ----------------------------
TOP_EVIDENCE_CHUNKS = 6
MAX_CHARS_PER_CHUNK = 900
MIN_EDGE_CONFIDENCE = 0.60
SLEEP_BETWEEN_CALLS = 0.5

# ----------------------------
# LLM
# ----------------------------
llm = LLM(
    sys_msg=(
        "You are a DBMS knowledge graph expert. "
        "You build source-grounded educational concept hierarchies using only the provided textbook chunks."
    ),
    temperature=0
)

# ----------------------------
# Prompt
# ----------------------------
PROMPT = """
You are building a source-grounded educational Knowledge Graph for Database Management Systems (DBMS).

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

# ----------------------------
# Load JSON
# ----------------------------
def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"Empty file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ----------------------------
# Safe JSON Parsing
# ----------------------------
def safe_parse_json(text):
    try:
        text = text.strip()

        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        return json.loads(text)

    except Exception:
        return None

# ----------------------------
# Normalize List Values
# ----------------------------
def ensure_list(value):
    if isinstance(value, list):
        return [v.strip() for v in value if isinstance(v, str) and v.strip()]

    if isinstance(value, str) and value.strip():
        return [value.strip()]

    return []

# ----------------------------
# Build Chunk Lookup
# ----------------------------
def build_chunk_lookup(chunks):
    return {
        c["chunk_id"]: c.get("text", "")
        for c in chunks
        if c.get("chunk_id")
    }

# ----------------------------
# Format Source Chunks
# ----------------------------
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

# ----------------------------
# Validate Category
# ----------------------------
def validate_category(raw_category, concept_name, all_concepts_set, valid_chunk_ids):
    if not isinstance(raw_category, dict):
        return None

    category = raw_category.get("concept", "")
    confidence = raw_category.get("confidence", 0.0)
    evidence_chunk = raw_category.get("evidence_chunk", "")
    evidence_text = raw_category.get("evidence_text", "")

    if not isinstance(category, str):
        return None

    category = category.strip()

    if not category:
        return None

    if category == concept_name:
        return None

    if category not in all_concepts_set:
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

    return {
        "concept": category,
        "confidence": round(confidence, 3),
        "evidence_chunk": evidence_chunk,
        "evidence_text": evidence_text.strip()
    }

# ----------------------------
# Validate Prerequisite Edges
# ----------------------------
def validate_prerequisite_edges(raw_edges, concept_name, all_concepts_set, valid_chunk_ids):
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

        if not prereq:
            continue

        if prereq == concept_name:
            continue

        if prereq not in all_concepts_set:
            continue

        if prereq in seen:
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

        valid_edges.append({
            "prerequisite": prereq,
            "confidence": round(confidence, 3),
            "evidence_chunk": evidence_chunk,
            "evidence_text": evidence_text.strip()
        })

        seen.add(prereq)

    return valid_edges

# ----------------------------
# Validate Full LLM Output
# ----------------------------
def validate_enrichment(updated, concept_name, all_concepts_set, valid_chunk_ids):
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
        valid_chunk_ids=valid_chunk_ids
    )

    prerequisite_edges = validate_prerequisite_edges(
        raw_edges=updated.get("prerequisite_edges", []),
        concept_name=concept_name,
        all_concepts_set=all_concepts_set,
        valid_chunk_ids=valid_chunk_ids
    )

    coarse_categories = []
    parent_concept = []

    if category_edge:
        coarse_categories = [category_edge["concept"]]
        parent_concept = [category_edge["concept"]]

    prerequisites = [
        edge["prerequisite"]
        for edge in prerequisite_edges
    ]

    return {
        "concept": concept_name,
        "node_type": "fine_grained_concept",

        # Paper-style hierarchy
        "coarse_grained_category": coarse_categories,

        # Backward compatibility with old graph/retriever code
        "parent_concept": parent_concept,
        "prerequisites": prerequisites,

        # Source-grounded edge metadata
        "category_edge": category_edge,
        "prerequisite_edges": prerequisite_edges
    }

# ----------------------------
# Enrichment Function
# ----------------------------
def enrich_concept(concept_obj, all_concepts, all_concepts_set, concept_chunk_map, chunk_lookup):
    concept_name = concept_obj["concept"]

    source_chunks, valid_chunk_ids = format_source_chunks(
        concept_name=concept_name,
        concept_chunk_map=concept_chunk_map,
        chunk_lookup=chunk_lookup
    )

    for attempt in range(3):
        try:
            prompt = PROMPT.format(
                concept=concept_name,
                all_concepts=", ".join(all_concepts),
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
                valid_chunk_ids=set(valid_chunk_ids)
            )

            return validated

        except Exception as e:
            print(f"⚠️ Retry {attempt + 1} failed for {concept_name}: {e}")
            time.sleep(2)

    return {
        "concept": concept_name,
        "node_type": "fine_grained_concept",
        "coarse_grained_category": [],
        "parent_concept": [],
        "category_edge": None,
        "prerequisites": [],
        "prerequisite_edges": []
    }

# ----------------------------
# Main
# ----------------------------
def main():

    concepts = load_json(INPUT_FILE)
    concept_chunk_map = load_json(CHUNK_MAP_FILE)
    chunks = load_json(CHUNKS_FILE)

    chunk_lookup = build_chunk_lookup(chunks)

    all_concept_names = [
        c["concept"]
        for c in concepts
        if isinstance(c, dict) and c.get("concept")
    ]

    all_concepts_set = set(all_concept_names)

    enriched = []

    print(f"✅ Loaded {len(all_concept_names)} concepts")
    print(f"✅ Loaded {len(concept_chunk_map)} concept-chunk mappings")
    print(f"✅ Loaded {len(chunk_lookup)} chunks")
    print("\n--- STARTING SOURCE-GROUNDED COARSE/FINE ENRICHMENT ---\n")

    for i, concept in enumerate(concepts):

        if not isinstance(concept, dict) or not concept.get("concept"):
            continue

        concept_name = concept["concept"]

        print(f"[{i + 1}/{len(concepts)}] Enriching: {concept_name}")

        updated = enrich_concept(
            concept_obj=concept,
            all_concepts=all_concept_names,
            all_concepts_set=all_concepts_set,
            concept_chunk_map=concept_chunk_map,
            chunk_lookup=chunk_lookup
        )

        enriched.append(updated)

        time.sleep(SLEEP_BETWEEN_CALLS)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    concepts_with_category = sum(
        1 for c in enriched if c.get("coarse_grained_category")
    )

    concepts_with_prereqs = sum(
        1 for c in enriched if c.get("prerequisites")
    )

    total_prereq_edges = sum(
        len(c.get("prerequisite_edges", []))
        for c in enriched
    )

    total_category_edges = sum(
        1 for c in enriched if c.get("category_edge")
    )

    print("\n✅ Enriched concepts saved!")
    print(f"📦 Output file: {OUTPUT_FILE}")
    print(f"📦 Total Concepts: {len(enriched)}")
    print(f"✅ Concepts with coarse-grained category: {concepts_with_category}")
    print(f"✅ Concepts with prerequisites: {concepts_with_prereqs}")
    print(f"✅ Source-grounded category edges: {total_category_edges}")
    print(f"✅ Source-grounded prerequisite edges: {total_prereq_edges}")

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    main()
