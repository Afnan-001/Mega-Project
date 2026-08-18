import sys
import json
import random
import os
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

from retriever import retrieve_context_for_concepts, chunk_lookup

CURRENT_DIR = Path(__file__).resolve().parent
MAIN_DIR = CURRENT_DIR.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from llm import LLM

# ----------------------------
# ✅ Load .env
# ----------------------------
load_dotenv()

# ----------------------------
# ✅ File
# ----------------------------
OUTPUTS_DIR = MAIN_DIR / "outputs"
DATA_DIR = OUTPUTS_DIR / "data"
OUTPUT_FILE = DATA_DIR / "generated_mcqs.json"

# ----------------------------
# ✅ Embedding Config
# ----------------------------
EMBEDDING_API_BASE = os.getenv(
    "EMBEDDING_API_BASE",
    "http://10.221.0.164:4000/v1"
)

EMBEDDING_ENDPOINT = f"{EMBEDDING_API_BASE.rstrip('/')}/embeddings"

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "si-rca-dds-text-embedding-3-small"
)

EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")

# Similarity threshold for detecting same-idea questions
SEMANTIC_DUPLICATE_THRESHOLD = 0.8

# If embedding API fails, continue generation instead of crashing
FAIL_OPEN_ON_EMBEDDING_ERROR = True

# ----------------------------
# ✅ LLM
# ----------------------------
llm = LLM(
    sys_msg=(
        "You are a psychometrician and senior Database Management Systems (DBMS) "
        "professor specializing in item response theory and Bayesian Knowledge "
        "Tracing (BKT). Your goal is to generate psychometrically sound, "
        "multi-concept exam questions where concept weights precisely reflect "
        "the cognitive load required to solve the question."
    ),
    temperature=0.55
)

# ----------------------------
# ✅ Question Style Templates
# ----------------------------
QUESTION_STYLES = {
    "easy": [
        "definition-based",
        "terminology-based",
        "basic identification",
        "simple concept recognition"
    ],
    "medium": [
        "comparison-based",
        "why/how reasoning",
        "identify the correct statement",
        "concept relationship question"
    ],
    "hard": [
        "application scenario",
        "error spotting",
        "case-based reasoning",
        "best design/action choice"
    ]
}

# ----------------------------
# ✅ Prompt
# ----------------------------
PROMPT = """
You are generating exactly ONE grounded DBMS multiple-choice question (MCQ) optimized for Bayesian Knowledge Tracing (BKT) evaluation.

HARD CONSTRAINTS:
1) Use only the provided CONTEXT and AVAILABLE CHUNK IDS.
2) Do not use outside knowledge.
3) Return valid JSON only (no markdown, no explanation, no extra keys).
4) Avoid repeating the same idea/style as RECENT QUESTIONS TO AVOID.

---
PRIMARY CONCEPT:
{primary_concept}

ALLOWED CONCEPTS (choose from this list only):
{allowed_concepts}

DIFFICULTY:
{difficulty}

QUESTION STYLE TO USE:
{question_style}

RECENT QUESTIONS TO AVOID:
{recent_questions}

AVAILABLE CHUNK IDS:
{available_chunk_ids}

CONTEXT:
{context}

---
CRITICAL INSTRUCTIONS FOR CONCEPT WEIGHTS (BKT SPECIFIC):
Concept weights measure the "Knowledge Verification Load". If a concept is deleted from the candidate's mind, would they fail the question?

Assign weights based on this strict rubric:
- Single Concept Question: If the context does not naturally support secondary concepts, map 1.0 entirely to the PRIMARY CONCEPT. Do not force secondary concepts.
- Core Dependency (Weight 0.3 - 0.4): Assign to a secondary concept ONLY if the candidate cannot eliminate distractor options or identify the correct answer without mastering this secondary concept.
- Mentioned but Not Tested (Weight 0.0): If a secondary concept is mentioned in the text but the correct answer can be found without understanding it, its weight MUST be 0.0 (omit it from the JSON).
- Mathematical Rule: The sum of all weights must equal exactly 1.0. The PRIMARY CONCEPT must always hold the strict mathematical maximum weight (e.g., >= 0.51 in a multi-concept setup).

---
EXAMPLE OUTPUT JSON SCHEMA:
{{
  "question": "<single clear MCQ stem>",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "A",
  "source_chunks": ["CHUNK_ID_1", "CHUNK_ID_2"],
  "concepts_covered": ["PRIMARY_CONCEPT", "SECONDARY_CONCEPT"],
  "concept_weights": {{
    "PRIMARY_CONCEPT": 0.65,
    "SECONDARY_CONCEPT": 0.35
  }}
}}

RULES:
- `question`: One concise, unambiguous stem.
- `options`: Exactly 4 options labeled "A. ", "B. ", "C. ", "D. ". The correct option must be perfectly factual; distractors must represent plausible misconceptions.
- `answer`: Exactly one of A/B/C/D matching the correct option.
- `source_chunks`: List of chunk IDs, each must exist in AVAILABLE CHUNK IDS.
- `concepts_covered`: Include PRIMARY CONCEPT; all items must come from ALLOWED CONCEPTS. Omit concepts with 0.0 cognitive weight.
- `concept_weights`: Keys must match concepts_covered exactly.
- `concept_weights` values must be numeric floating points in, summing to exactly 1.0.
- PRIMARY CONCEPT must have the highest weight.

QUALITY TARGET:
- Difficulty should match DIFFICULTY.
- Style should follow QUESTION STYLE TO USE.
- High Psychometric Validity: Ensure that missing knowledge in any listed concept guarantees choosing a distractor option.
"""

CONCEPT_WEIGHT_SUM_TOLERANCE = 0.02


def build_default_concept_weights(primary_concept, secondary_concepts):
    secondary_concepts = normalize_concept_list(secondary_concepts)

    if not secondary_concepts:
        return {primary_concept: 1.0}

    primary_weight = 0.7
    secondary_weight_total = 0.3
    per_secondary = secondary_weight_total / len(secondary_concepts)

    weights = {primary_concept: primary_weight}
    for concept in secondary_concepts:
        weights[concept] = per_secondary

    return weights


def normalize_concept_weights(
    concept_weights,
    primary_concept,
    allowed_concepts,
    fallback_secondary=None
):
    allowed_set = set(allowed_concepts)
    fallback_secondary = normalize_concept_list(fallback_secondary)

    cleaned = {}
    if isinstance(concept_weights, dict):
        for key, value in concept_weights.items():
            if not isinstance(key, str):
                continue

            concept = key.strip()
            if not concept or concept not in allowed_set:
                continue

            try:
                weight = float(value)
            except Exception:
                continue

            if weight <= 0:
                continue

            cleaned[concept] = weight

    if primary_concept not in cleaned:
        default_weights = build_default_concept_weights(primary_concept, fallback_secondary)
        return normalize_concept_weights(
            default_weights,
            primary_concept,
            allowed_concepts,
            fallback_secondary=fallback_secondary
        )

    total = sum(cleaned.values())
    if total <= 0:
        default_weights = build_default_concept_weights(primary_concept, fallback_secondary)
        return normalize_concept_weights(
            default_weights,
            primary_concept,
            allowed_concepts,
            fallback_secondary=fallback_secondary
        )

    normalized = {
        concept: weight / total
        for concept, weight in cleaned.items()
    }

    primary_weight = normalized.get(primary_concept, 0.0)
    highest_weight = max(normalized.values()) if normalized else 0.0

    if primary_weight + 1e-9 < highest_weight:
        boost = highest_weight - primary_weight + 1e-6
        normalized[primary_concept] = primary_weight + boost

        renorm_total = sum(normalized.values())
        normalized = {
            concept: weight / renorm_total
            for concept, weight in normalized.items()
        }

    if abs(sum(normalized.values()) - 1.0) > CONCEPT_WEIGHT_SUM_TOLERANCE:
        renorm_total = sum(normalized.values())
        normalized = {
            concept: weight / renorm_total
            for concept, weight in normalized.items()
        }

    # Keep deterministic ordering: primary first, then descending weight, then name.
    ordered = {primary_concept: round(normalized[primary_concept], 4)}

    others = sorted(
        [c for c in normalized.keys() if c != primary_concept],
        key=lambda c: (-normalized[c], c.lower())
    )

    for concept in others:
        ordered[concept] = round(normalized[concept], 4)

    # Final micro-adjustment for floating drift so weights sum exactly to ~1.
    drift = round(1.0 - sum(ordered.values()), 4)
    if drift != 0:
        ordered[primary_concept] = round(ordered[primary_concept] + drift, 4)

    return ordered


def normalize_concept_list(concepts):
    cleaned = []

    for concept in concepts or []:
        if not isinstance(concept, str):
            continue

        value = concept.strip()
        if not value:
            continue

        if value not in cleaned:
            cleaned.append(value)

    return cleaned


def build_question_key(primary_concept, secondary_concepts=None):
    secondary_concepts = normalize_concept_list(secondary_concepts)

    if not secondary_concepts:
        return primary_concept

    return f"{primary_concept}__{'|'.join(secondary_concepts)}"

# ----------------------------
# ✅ Load Existing Questions
# ----------------------------
def load_existing():
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

# ----------------------------
# ✅ Normalize Question Text
# ----------------------------
def normalize_question(text):
    return " ".join(text.strip().lower().split())

# ----------------------------
# ✅ Save Question
# ----------------------------
def save_mcq(primary_concept, difficulty, question, secondary_concepts=None):
    """
    Saves MCQ only if exact duplicate does not exist.
    Returns True if saved, False if duplicate.
    """
    data = load_existing()

    question_key = build_question_key(primary_concept, secondary_concepts)

    if question_key not in data:
        data[question_key] = {"easy": [], "medium": [], "hard": []}

    if difficulty not in data[question_key]:
        data[question_key][difficulty] = []

    existing_questions = [
        normalize_question(q["question"])
        for q in data[question_key][difficulty]
        if "question" in q
    ]

    if normalize_question(question["question"]) in existing_questions:
        print("⚠️ Exact duplicate rejected")
        return False

    data[question_key][difficulty].append(question)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return True

# ----------------------------
# ✅ Generate Stable ID
# ----------------------------
def generate_id(existing, primary_concept, difficulty, secondary_concepts=None):
    question_key = build_question_key(primary_concept, secondary_concepts)
    count = len(existing.get(question_key, {}).get(difficulty, [])) + 1
    return f"{question_key}_{difficulty}_{count}"

# ----------------------------
# ✅ Reuse Existing Questions
# ----------------------------
def get_existing_question(concept, difficulty, asked_ids, wrong_ids, secondary_concepts=None):
    data = load_existing()
    question_key = build_question_key(concept, secondary_concepts)

    if question_key not in data or difficulty not in data[question_key]:
        return None

    wrong_pool = []
    fresh_pool = []

    for q in data[question_key][difficulty]:
        qid = q.get("id")

        if not qid:
            continue

        # Prefer previously wrong questions
        if qid in wrong_ids:
            wrong_pool.append(q)

        # Prefer unasked questions next
        elif qid not in asked_ids:
            fresh_pool.append(q)

    if wrong_pool:
        return random.choice(wrong_pool)

    if fresh_pool:
        return random.choice(fresh_pool)

    return None

# ----------------------------
# ✅ Recent Questions / Chunks
# ----------------------------
def get_recent_metadata(concept, difficulty, limit=6, secondary_concepts=None):
    data = load_existing()
    question_key = build_question_key(concept, secondary_concepts)

    if question_key not in data or difficulty not in data[question_key]:
        return [], []

    questions = data[question_key][difficulty][-limit:]

    recent_questions = [
        q.get("question", "")
        for q in questions
        if q.get("question")
    ]

    recent_chunks = []
    for q in questions:
        if isinstance(q.get("source_chunks"), list):
            recent_chunks.extend(
                [cid for cid in q["source_chunks"] if isinstance(cid, str) and cid.strip()]
            )

    return recent_questions, recent_chunks

# ----------------------------
# ✅ Existing Question Texts
# ----------------------------
def get_existing_question_texts(concept, difficulty, limit=30, secondary_concepts=None):
    data = load_existing()
    question_key = build_question_key(concept, secondary_concepts)

    if question_key not in data or difficulty not in data[question_key]:
        return []

    questions = data[question_key][difficulty]

    texts = [
        q.get("question", "")
        for q in questions
        if q.get("question")
    ]

    return texts[-limit:]

# ----------------------------
# ✅ Choose Diverse Question Style
# ----------------------------
def choose_question_style(concept, difficulty, secondary_concepts=None):
    existing = load_existing()
    question_key = build_question_key(concept, secondary_concepts)
    count = len(existing.get(question_key, {}).get(difficulty, []))

    styles = QUESTION_STYLES.get(difficulty, QUESTION_STYLES["medium"])

    return styles[count % len(styles)]

# ----------------------------
# ✅ Choose Diverse Chunks
# ----------------------------
def choose_diverse_chunks(all_chunks, recent_chunks, max_chunks=5):
    if not all_chunks:
        return []

    preferred = [cid for cid in all_chunks if cid not in recent_chunks]
    fallback = [cid for cid in all_chunks if cid in recent_chunks]

    random.shuffle(preferred)
    random.shuffle(fallback)

    selected = preferred[:max_chunks]

    if len(selected) < max_chunks:
        selected.extend(fallback[:max_chunks - len(selected)])

    return selected

# ----------------------------
# ✅ Build Context from Selected Chunks
# ----------------------------
def build_context(selected_chunks):
    blocks = []

    for cid in selected_chunks:
        text = chunk_lookup.get(cid, "")

        if text:
            blocks.append(f"[{cid}]\n{text}")

    return "\n\n".join(blocks)

# ----------------------------
# ✅ Choose Best Fallback Source Chunk
# ----------------------------
def choose_fallback_source_chunk(selected_chunks, recent_chunks):
    unused = [cid for cid in selected_chunks if cid not in recent_chunks]

    if unused:
        return random.choice(unused)

    if selected_chunks:
        return random.choice(selected_chunks)

    return "fallback_chunk"

# ============================================================
# ✅ EMBEDDING-BASED SEMANTIC DUPLICATE   
def normalize_vector(vec):
    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)

    if norm == 0:
        return arr

    return arr / norm


def embed_texts(texts):
    """
    Embeds list of texts using internal embedding endpoint.
    Returns normalized numpy matrix.
    """
    if not texts:
        return np.array([], dtype=np.float32)

    if not EMBEDDING_API_KEY:
        raise ValueError("❌ EMBEDDING_API_KEY missing in .env")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EMBEDDING_API_KEY}"
    }

    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts
    }

    response = requests.post(
        EMBEDDING_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Embedding API failed: {response.status_code} | {response.text}"
        )

    data = response.json()

    if "data" not in data:
        raise ValueError(f"Invalid embedding response: {data}")

    # Sort by index to preserve input order
    items = sorted(data["data"], key=lambda x: x.get("index", 0))

    vectors = []

    for item in items:
        vec = item.get("embedding")

        if vec is None:
            raise ValueError(f"Missing embedding in response item: {item}")

        vectors.append(normalize_vector(vec))

    return np.array(vectors, dtype=np.float32)


def is_semantically_duplicate(
    new_question,
    old_questions,
    threshold=SEMANTIC_DUPLICATE_THRESHOLD
):
    """
    Returns:
    - is_duplicate: bool
    - max_similarity: float
    - most_similar_question: str or None
    """

    if not old_questions:
        return False, 0.0, None

    try:
        all_texts = [new_question] + old_questions
        embeddings = embed_texts(all_texts)

        if embeddings.shape[0] < 2:
            return False, 0.0, None

        new_vec = embeddings[0]
        old_vecs = embeddings[1:]

        similarities = old_vecs @ new_vec

        max_idx = int(np.argmax(similarities))
        max_score = float(similarities[max_idx])
        most_similar_question = old_questions[max_idx]

        if max_score >= threshold:
            return True, max_score, most_similar_question

        return False, max_score, most_similar_question

    except Exception as e:
        print("⚠️ Semantic duplicate check failed:", e)

        if FAIL_OPEN_ON_EMBEDDING_ERROR:
            print("⚠️ Continuing without semantic duplicate rejection")
            return False, 0.0, None

        raise

# ----------------------------
# ✅ Generate Question
# ----------------------------
def generate_question(
    concept_name,
    difficulty,
    asked_ids=None,
    wrong_ids=None,
    secondary_concepts=None
):
    asked_ids = set(asked_ids or [])
    wrong_ids = set(wrong_ids or [])
    secondary_concepts = normalize_concept_list(secondary_concepts)
    allowed_concepts = [concept_name] + [
        c for c in secondary_concepts
        if c != concept_name
    ]

    # ✅ 1. Try reuse first
    existing_q = get_existing_question(
        concept_name,
        difficulty,
        asked_ids,
        wrong_ids,
        secondary_concepts=secondary_concepts
    )

    if existing_q:
        return existing_q

    # ✅ 2. Retrieve context
    data = retrieve_context_for_concepts(
        primary_concept=concept_name,
        secondary_concepts=secondary_concepts
    )

    if not data or not data.get("chunks"):
        print("⚠️ Retrieval failed or empty chunks")
        return None

    # ✅ 3. Diversity metadata
    recent_questions, recent_chunks = get_recent_metadata(
        concept_name,
        difficulty,
        limit=6,
        secondary_concepts=secondary_concepts
    )

    question_style = choose_question_style(
        concept_name,
        difficulty,
        secondary_concepts=secondary_concepts
    )

    # ✅ 4. Select diverse chunks
    all_chunks = list(data["chunks"])

    selected_chunks = choose_diverse_chunks(
        all_chunks,
        recent_chunks,
        max_chunks=4
    )

    if not selected_chunks:
        print("⚠️ No selected chunks available")
        return None

    # ✅ 5. Build focused context
    formatted_context = build_context(selected_chunks)

    if not formatted_context.strip():
        print("⚠️ Empty formatted context")
        return None

    recent_questions_text = "\n".join(
        [f"- {q}" for q in recent_questions[-5:]]
    ) if recent_questions else "None"

    prompt = PROMPT.format(
        primary_concept=concept_name,
        allowed_concepts=", ".join(allowed_concepts),
        difficulty=difficulty,
        question_style=question_style,
        recent_questions=recent_questions_text,
        available_chunk_ids=", ".join(selected_chunks),
        context=formatted_context
    )

    response = llm.get_response(prompt)
    content = response.strip()

    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        q = json.loads(content)

        # ----------------------------
        # ✅ Strict Validation
        # ----------------------------
        required_keys = ["question", "options", "answer"]

        for key in required_keys:
            if key not in q:
                raise ValueError(f"Missing key: {key}")

        if not isinstance(q["question"], str) or not q["question"].strip():
            raise ValueError("Question must be a non-empty string")

        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            raise ValueError("Options must be exactly 4")

        q["answer"] = q["answer"].strip().upper()

        if q["answer"] not in ["A", "B", "C", "D"]:
            raise ValueError("Answer must be A/B/C/D")

        # ----------------------------
        # ✅ Semantic Duplicate Check
        # ----------------------------
        existing_question_texts = get_existing_question_texts(
            concept_name,
            difficulty,
            limit=30,
            secondary_concepts=secondary_concepts
        )

        is_dup, sim_score, similar_q = is_semantically_duplicate(
            q["question"],
            existing_question_texts
        )

        if is_dup:
            print("⚠️ Semantic duplicate rejected")
            print("Similarity:", round(sim_score, 4))
            print("Similar to:", similar_q)
            return None

        # ----------------------------
        # ✅ Validate / diversify source chunk
        # ----------------------------
        source_chunks = q.get("source_chunks")
        if not isinstance(source_chunks, list):
            source_chunks = []

        source_chunks = [
            cid for cid in source_chunks
            if isinstance(cid, str) and cid in selected_chunks
        ]

        if not source_chunks:
            source_chunks = [
                choose_fallback_source_chunk(
                    selected_chunks,
                    recent_chunks
                )
            ]

        source_chunks = source_chunks[:3]

        raw_concepts_covered = q.get("concepts_covered")
        if isinstance(raw_concepts_covered, list):
            model_concepts = [
                c for c in normalize_concept_list(raw_concepts_covered)
                if c in allowed_concepts
            ]
        else:
            model_concepts = []

        if concept_name not in model_concepts:
            model_concepts.insert(0, concept_name)

        concepts_for_weights = []
        for concept in model_concepts:
            if concept not in concepts_for_weights:
                concepts_for_weights.append(concept)

        raw_concept_weights = q.get("concept_weights")
        normalized_weights = normalize_concept_weights(
            concept_weights=raw_concept_weights,
            primary_concept=concept_name,
            allowed_concepts=concepts_for_weights,
            fallback_secondary=[c for c in concepts_for_weights if c != concept_name]
        )

        concepts_covered = list(normalized_weights.keys())

        q["primary_concept"] = concept_name
        q["secondary_concepts"] = secondary_concepts
        q["concepts_covered"] = concepts_covered
        q["concept_weights"] = normalized_weights
        q["source_chunks"] = source_chunks

        # ----------------------------
        # ✅ Assign ID
        # ----------------------------
        existing = load_existing()
        q["id"] = generate_id(
            existing,
            concept_name,
            difficulty,
            secondary_concepts=secondary_concepts
        )

        # ----------------------------
        # ✅ Save
        # ----------------------------
        saved = save_mcq(
            concept_name,
            difficulty,
            q,
            secondary_concepts=secondary_concepts
        )

        if not saved:
            return None

        return q

    except Exception as e:
        print("❌ Validation / Parsing Error:", str(e))
        print("RAW OUTPUT:\n", content)
        return None

# ----------------------------
# ✅ CLI
# ----------------------------
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python question_generator.py "Concept" difficulty')
        sys.exit(1)

    concept = sys.argv[1]
    difficulty = sys.argv[2]

    q = generate_question(concept, difficulty)

    if q:
        print("\n✅ QUESTION\n")
        print("ID:", q["id"])
        print(q["question"])

        for opt in q["options"]:
            print(opt)

        print("Answer:", q["answer"])
        print("Sources:", q["source_chunks"])
