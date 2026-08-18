import json
from pathlib import Path
import networkx as nx

from question_generator import generate_question
from confidence import compute_confidence

# ----------------------------
# ✅ Files
# ----------------------------
MAIN_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = MAIN_DIR / "outputs"
DATA_DIR = OUTPUTS_DIR / "data"

MASTERY_FILE = DATA_DIR / "mastery_scores.json"
GRAPH_FILE = OUTPUTS_DIR / "graph_model" / "knowledge_graph.gml"
NAVIGATION_STATE_FILE = DATA_DIR / "navigation_state.json"

G = nx.read_gml(GRAPH_FILE)

# ----------------------------
# ✅ BKT PARAMETERS
# ----------------------------
P_G = 0.2   # Guess
P_S = 0.1   # Slip
P_T = 0.1   # Learn

# ----------------------------
# ✅ Navigation Settings
# ----------------------------
MASTERY_THRESHOLD = 0.8
WEAK_THRESHOLD = 0.4
RECENT_WINDOW = 5
MAX_PREREQ_CANDIDATES_FOR_LLM = 6

# ----------------------------
# ✅ Learner Confidence Settings
# ----------------------------
RECENT_ANSWERS_WINDOW = 10

CONFIDENCE_HIGH_THRESHOLD = 0.75
CONFIDENCE_LOW_THRESHOLD = 0.25

ATTEMPT_CONFIDENCE_WEIGHT = 0.5
CONSISTENCY_CONFIDENCE_WEIGHT = 0.5
ATTEMPT_SATURATION_RATE = 0.35
MIN_ATTEMPTS_FOR_CONFIDENCE = 8

# ----------------------------
# ✅ Load / Save Mastery
# ----------------------------
def load_mastery():
    if not MASTERY_FILE.exists():
        return {}
    with open(MASTERY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def save_mastery(data):
    MASTERY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MASTERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def normalize_recent_answers(recent_answers):
    if not isinstance(recent_answers, list):
        return []

    cleaned = []
    for item in recent_answers:
        if isinstance(item, bool):
            cleaned.append(int(item))
        elif item in (0, 1):
            cleaned.append(int(item))
        elif isinstance(item, (int, float)):
            cleaned.append(1 if item >= 0.5 else 0)

    return cleaned[-RECENT_ANSWERS_WINDOW:]


def ensure_mastery_entry(entry):
    base = {
        "p_know": 0.2,
        "confidence": 0.0,
        "questions_attempted": 0,
        "correct_answers": 0,
        "recent_answers": [],
        "asked_question_ids": [],
        "wrong_question_ids": []
    }

    if not isinstance(entry, dict):
        entry = {}

    merged = {
        **base,
        **entry,
    }

    try:
        merged["p_know"] = float(merged.get("p_know", 0.2))
    except Exception:
        merged["p_know"] = 0.2

    try:
        merged["questions_attempted"] = max(0, int(merged.get("questions_attempted", 0)))
    except Exception:
        merged["questions_attempted"] = 0

    try:
        merged["correct_answers"] = max(0, int(merged.get("correct_answers", 0)))
    except Exception:
        merged["correct_answers"] = 0

    if merged["correct_answers"] > merged["questions_attempted"]:
        merged["correct_answers"] = merged["questions_attempted"]

    merged["asked_question_ids"] = [
        qid for qid in merged.get("asked_question_ids", [])
        if isinstance(qid, str) and qid
    ]

    merged["wrong_question_ids"] = [
        qid for qid in merged.get("wrong_question_ids", [])
        if isinstance(qid, str) and qid
    ]

    merged["recent_answers"] = normalize_recent_answers(
        merged.get("recent_answers", [])
    )

    merged["confidence"] = compute_confidence(
        questions_attempted=merged["questions_attempted"],
        recent_answers=merged["recent_answers"],
        attempt_weight=ATTEMPT_CONFIDENCE_WEIGHT,
        consistency_weight=CONSISTENCY_CONFIDENCE_WEIGHT,
        saturation_rate=ATTEMPT_SATURATION_RATE,
        min_attempts_for_reliability=MIN_ATTEMPTS_FOR_CONFIDENCE
    )

    return merged


def get_confidence_level(confidence):
    if confidence >= CONFIDENCE_HIGH_THRESHOLD:
        return "high"

    if confidence <= CONFIDENCE_LOW_THRESHOLD:
        return "low"

    return "moderate"


# ----------------------------
# ✅ Navigation State Tracking
# ----------------------------
def load_navigation_state():
    if NAVIGATION_STATE_FILE.exists():
        with open(NAVIGATION_STATE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
    else:
        data = {}

    if not isinstance(data, dict):
        data = {}

    current_concept = data.get("current_concept")
    return_target = data.get("return_target")
    recent_concepts = data.get("recent_concepts", [])

    if not isinstance(current_concept, str) or not current_concept.strip():
        current_concept = None
    else:
        current_concept = current_concept.strip()

    if not isinstance(return_target, str) or not return_target.strip():
        return_target = None
    else:
        return_target = return_target.strip()

    if not isinstance(recent_concepts, list):
        recent_concepts = []

    cleaned_recent = []
    for concept in recent_concepts:
        if isinstance(concept, str) and concept.strip():
            cleaned_recent.append(concept.strip())

    return {
        "current_concept": current_concept,
        "return_target": return_target,
        "recent_concepts": cleaned_recent[-RECENT_WINDOW:]
    }


def save_navigation_state(state):
    NAVIGATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    state = state if isinstance(state, dict) else {}

    current_concept = state.get("current_concept")
    return_target = state.get("return_target")
    recent_concepts = state.get("recent_concepts", [])

    if not isinstance(current_concept, str) or not current_concept.strip():
        current_concept = None
    else:
        current_concept = current_concept.strip()

    if not isinstance(return_target, str) or not return_target.strip():
        return_target = None
    else:
        return_target = return_target.strip()

    if not isinstance(recent_concepts, list):
        recent_concepts = []

    cleaned_recent = []
    for concept in recent_concepts:
        if isinstance(concept, str) and concept.strip():
            cleaned_recent.append(concept.strip())

    payload = {
        "current_concept": current_concept,
        "return_target": return_target,
        "recent_concepts": cleaned_recent[-RECENT_WINDOW:]
    }

    with open(NAVIGATION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def get_current_concept():
    return load_navigation_state().get("current_concept")


def set_current_concept(concept):
    state = load_navigation_state()
    state["current_concept"] = concept
    save_navigation_state(state)


def get_return_target():
    return load_navigation_state().get("return_target")


def set_return_target(concept):
    state = load_navigation_state()
    state["return_target"] = concept
    save_navigation_state(state)


def clear_return_target():
    state = load_navigation_state()
    state["return_target"] = None
    save_navigation_state(state)


# ----------------------------
def get_recent_history():
    return load_navigation_state().get("recent_concepts", [])


def push_recent_concept(concept):
    state = load_navigation_state()
    history = state.get("recent_concepts", [])
    history.append(concept)
    state["recent_concepts"] = history
    save_navigation_state(state)


# ----------------------------
# ✅ Get / Init Concept (BKT)
# ----------------------------
def get_mastery(concept):
    data = load_mastery()

    data[concept] = ensure_mastery_entry(data.get(concept, {}))
    save_mastery(data)

    return data[concept]


# ----------------------------
# ✅ Root Concepts (NO prerequisites)
# ----------------------------
def get_root_concepts():
    roots = []

    for node in G.nodes:
        incoming = [
            src for src, _, d in G.in_edges(node, data=True)
            if d.get("relation") == "PREREQUISITE_FOR"
        ]
        if len(incoming) == 0:
            roots.append(node)

    return roots


# ----------------------------
# ✅ Graph Helpers
# ----------------------------
def get_prerequisite_nodes(concept):
    return [
        src for src, _, d in G.in_edges(concept, data=True)
        if d.get("relation") == "PREREQUISITE_FOR"
    ]


def get_successor_nodes(concept):
    return [
        dst for _, dst, d in G.edges(concept, data=True)
        if d.get("relation") == "PREREQUISITE_FOR"
    ]


def parse_edge_confidence(raw_value):
    try:
        return float(raw_value)
    except Exception:
        return 0.0


def get_successor_candidates(concept):
    candidates = []

    for _, dst, edge_data in G.edges(concept, data=True):
        if edge_data.get("relation") != "PREREQUISITE_FOR":
            continue

        confidence = parse_edge_confidence(
            edge_data.get("confidence", edge_data.get("relationship_confidence", 0.0))
        )

        candidates.append({
            "concept": dst,
            "edge_confidence": confidence,
        })

    return candidates


def select_preferred_successor(successor_candidates, data, exclude_recent=True):
    if not successor_candidates:
        return None

    recent = set(get_recent_history()) if exclude_recent else set()

    valid_candidates = [
        item for item in successor_candidates
        if item["concept"] in data
    ]

    # Requested preference: unmastered successors first.
    unmastered = [
        item for item in valid_candidates
        if data[item["concept"]]["p_know"] < MASTERY_THRESHOLD
    ]

    if not unmastered:
        return None

    # Requested preference among successors: highest edge confidence first.
    # Tie-breakers: avoid very recent concepts, then lower p_know, then name.
    ranked = sorted(
        unmastered,
        key=lambda item: (
            1 if item["concept"] in recent else 0,
            -item["edge_confidence"],
            data[item["concept"]]["p_know"],
            item["concept"].lower(),
        ),
    )

    return ranked[0]["concept"]


# ----------------------------
# ✅ Difficulty Selection
# ----------------------------
def get_difficulty(concept):
    p = get_mastery(concept)["p_know"]

    if p < WEAK_THRESHOLD:
        return "easy"
    elif p < MASTERY_THRESHOLD:
        return "medium"
    return "hard"


# ----------------------------
# ✅ Candidate Ranking
# ----------------------------
def weakest_concept(concepts, data, exclude_recent=True):
    recent = set(get_recent_history()) if exclude_recent else set()

    candidates = [
        c for c in concepts
        if c in data and c not in recent
    ]

    if not candidates:
        candidates = [c for c in concepts if c in data]

    if not candidates:
        return None

    return min(candidates, key=lambda c: data[c]["p_know"])


def weakest_unmastered(concepts, data, exclude_recent=True):
    recent = set(get_recent_history()) if exclude_recent else set()

    candidates = [
        c for c in concepts
        if c in data and data[c]["p_know"] < MASTERY_THRESHOLD and c not in recent
    ]

    if not candidates:
        candidates = [
            c for c in concepts
            if c in data and data[c]["p_know"] < MASTERY_THRESHOLD
        ]

    if not candidates:
        return None

    return min(candidates, key=lambda c: data[c]["p_know"])


def global_fallback_concept(data):
    """
    Pick another concept when the current branch is exhausted.
    Priority:
    1. weakest unmastered root
    2. weakest unmastered concept globally
    3. weakest concept globally
    """
    roots = get_root_concepts()

    root_choice = weakest_unmastered(roots, data, exclude_recent=True)
    if root_choice:
        return root_choice

    global_unmastered = weakest_unmastered(list(data.keys()), data, exclude_recent=True)
    if global_unmastered:
        return global_unmastered

    return weakest_concept(list(data.keys()), data, exclude_recent=False)


def select_secondary_concepts(primary_concept, difficulty, data):
    # Mentor-requested selection: only direct UNMASTERED prerequisites.
    unmastered_prereqs = [
        concept for concept in get_prerequisite_nodes(primary_concept)
        if concept in data and concept != primary_concept and data[concept]["p_know"] < MASTERY_THRESHOLD
    ]

    if not unmastered_prereqs:
        return []

    ranked = sorted(unmastered_prereqs, key=lambda c: (data[c]["p_know"], c.lower()))
    return ranked[:MAX_PREREQ_CANDIDATES_FOR_LLM]


# ----------------------------
# ✅ GRAPH-AWARE CONCEPT SELECTION (FIXED)
# ----------------------------
def select_next_concept():
    data = load_mastery()
    if not data:
        raise ValueError("mastery_scores.json is empty")

    data = {
        concept: ensure_mastery_entry(entry)
        for concept, entry in data.items()
        if isinstance(concept, str) and concept
    }
    save_mastery(data)

    current = get_current_concept()
    return_target = get_return_target()

    # ----------------------------
    # ✅ FIRST RUN → start from weakest root
    # ----------------------------
    if not current or current not in data:
        start = global_fallback_concept(data)
        set_current_concept(start)
        clear_return_target()
        push_recent_concept(start)
        return start

    # ----------------------------
    # ✅ RETURN-TARGET MODE (prerequisite remediation)
    # ----------------------------
    if return_target and return_target in data:
        target_prereqs = get_prerequisite_nodes(return_target)
        unmastered_target_prereqs = [
            c for c in target_prereqs
            if c in data and data[c]["p_know"] < MASTERY_THRESHOLD
        ]

        if not unmastered_target_prereqs:
            clear_return_target()
            set_current_concept(return_target)
            push_recent_concept(return_target)
            return return_target

        if current in unmastered_target_prereqs:
            set_current_concept(current)
            push_recent_concept(current)
            return current

        next_prereq = weakest_unmastered(
            unmastered_target_prereqs,
            data,
            exclude_recent=True
        )

        if next_prereq:
            set_current_concept(next_prereq)
            push_recent_concept(next_prereq)
            return next_prereq

        set_current_concept(current)
        push_recent_concept(current)
        return current

    if return_target and return_target not in data:
        clear_return_target()

    current_entry = data[current]
    current_p = current_entry["p_know"]
    current_conf = current_entry["confidence"]
    conf_level = get_confidence_level(current_conf)

    # ----------------------------
    # ✅ WEAK → go to weaker prerequisite if possible
    # otherwise keep practicing current
    # ----------------------------
    if current_p <= WEAK_THRESHOLD:
        if conf_level == "low":
            # Low mastery + low confidence -> gather more evidence first.
            set_current_concept(current)
            push_recent_concept(current)
            return current

        candidate_preds = [
            c for c in get_prerequisite_nodes(current)
            if c in data and data[c]["p_know"] < MASTERY_THRESHOLD
        ]

        next_concept = weakest_unmastered(candidate_preds, data, exclude_recent=True)

        if next_concept:
            set_return_target(current)
            set_current_concept(next_concept)
            push_recent_concept(next_concept)
            return next_concept

        # If no useful prerequisite, continue practicing current
        set_current_concept(current)
        push_recent_concept(current)
        return current

    # ----------------------------
    # ✅ MASTERED → move to weakest unmastered successor
    # if none exists, leave the branch
    # ----------------------------
    if current_p >= MASTERY_THRESHOLD:
        if conf_level == "low":
            # High mastery + low confidence -> validate on same concept.
            set_current_concept(current)
            push_recent_concept(current)
            return current

        unmastered_prereqs = [
            c for c in get_prerequisite_nodes(current)
            if c in data and data[c]["p_know"] < MASTERY_THRESHOLD
        ]

        if unmastered_prereqs:
            next_prereq = weakest_unmastered(
                unmastered_prereqs,
                data,
                exclude_recent=True
            )

            if next_prereq:
                set_return_target(current)
                set_current_concept(next_prereq)
                push_recent_concept(next_prereq)
                return next_prereq

        succ_candidates = get_successor_candidates(current)

        # Prefer: unmastered successors first, then highest-confidence successor edge.
        next_concept = select_preferred_successor(
            succ_candidates,
            data,
            exclude_recent=True,
        )

        if next_concept:
            set_current_concept(next_concept)
            push_recent_concept(next_concept)
            return next_concept

        # Branch exhausted → jump to another weak root/global concept
        fallback = global_fallback_concept(data)
        set_current_concept(fallback)
        clear_return_target()
        push_recent_concept(fallback)
        return fallback

    # ----------------------------
    # ✅ MODERATE → continue current concept
    # ----------------------------
    set_current_concept(current)
    push_recent_concept(current)
    return current


# ----------------------------
# ✅ Adaptive Question
# ----------------------------
def get_adaptive_question():
    concept = select_next_concept()
    difficulty = get_difficulty(concept)

    mastery_snapshot = {
        concept: ensure_mastery_entry(entry)
        for concept, entry in load_mastery().items()
        if isinstance(concept, str) and concept
    }
    secondary_concepts = select_secondary_concepts(
        primary_concept=concept,
        difficulty=difficulty,
        data=mastery_snapshot
    )
    concepts_covered = [concept] + secondary_concepts

    mastery_data = get_mastery(concept)

    asked_ids = set(mastery_data.get("asked_question_ids", []))
    wrong_ids = set(mastery_data.get("wrong_question_ids", []))

    q = None

    for _ in range(7):
        q = generate_question(
            concept,
            difficulty,
            asked_ids,
            wrong_ids,
            secondary_concepts=secondary_concepts
        )

        if not q:
            continue

        qid = q.get("id")
        if not qid:
            continue

        # Ask only if not previously solved correctly
        if qid not in asked_ids or qid in wrong_ids:
            q_concepts = q.get("concepts_covered", concepts_covered)
            q_weights = q.get("concept_weights", {})
            return {
                "concept": concept,
                "difficulty": difficulty,
                "secondary_concepts": secondary_concepts,
                "concepts_covered": q_concepts,
                "concept_weights": q_weights,
                "question": q
            }

    q_concepts = q.get("concepts_covered", concepts_covered) if isinstance(q, dict) else concepts_covered
    q_weights = q.get("concept_weights", {}) if isinstance(q, dict) else {}
    return {
        "concept": concept,
        "difficulty": difficulty,
        "secondary_concepts": secondary_concepts,
        "concepts_covered": q_concepts,
        "concept_weights": q_weights,
        "question": q
    }


# ----------------------------
# ✅ Evaluate Answer
# ----------------------------
def evaluate_answer(question_data, user_answer):
    return question_data.get("answer", "").strip().upper() == user_answer.strip().upper()


# ----------------------------
# ✅ BKT UPDATE
# ----------------------------
def update_mastery(concept, question_id, correct):
    data = load_mastery()
    entry = ensure_mastery_entry(data.get(concept, {}))

    p = entry["p_know"]

    if correct:
        numerator = p * (1 - P_S)
        denominator = numerator + (1 - p) * P_G
    else:
        numerator = p * P_S
        denominator = numerator + (1 - p) * (1 - P_G)

    posterior = p if denominator == 0 else numerator / denominator
    p_new = posterior + (1 - posterior) * P_T

    entry["p_know"] = max(0.0, min(1.0, p_new))

    # stats
    entry["questions_attempted"] += 1
    if correct:
        entry["correct_answers"] += 1

    # tracking
    if question_id and question_id not in entry["asked_question_ids"]:
        entry["asked_question_ids"].append(question_id)

    if question_id:
        if correct:
            if question_id in entry["wrong_question_ids"]:
                entry["wrong_question_ids"].remove(question_id)
        else:
            if question_id not in entry["wrong_question_ids"]:
                entry["wrong_question_ids"].append(question_id)

    entry["recent_answers"].append(1 if correct else 0)
    entry["recent_answers"] = normalize_recent_answers(entry["recent_answers"])

    entry["confidence"] = compute_confidence(
        questions_attempted=entry["questions_attempted"],
        recent_answers=entry["recent_answers"],
        attempt_weight=ATTEMPT_CONFIDENCE_WEIGHT,
        consistency_weight=CONSISTENCY_CONFIDENCE_WEIGHT,
        saturation_rate=ATTEMPT_SATURATION_RATE,
        min_attempts_for_reliability=MIN_ATTEMPTS_FOR_CONFIDENCE
    )

    data[concept] = entry
    save_mastery(data)
    return entry


def update_mastery_multi(concepts, question_id, correct, concept_weights=None):
    data = load_mastery()
    updated = {}

    concept_weights = concept_weights if isinstance(concept_weights, dict) else {}

    for concept in concepts:
        entry = ensure_mastery_entry(data.get(concept, {}))

        raw_weight = concept_weights.get(concept, 1.0)
        try:
            weight = float(raw_weight)
        except Exception:
            weight = 1.0
        weight = max(0.0, min(1.0, weight))

        p = entry["p_know"]

        if correct:
            numerator = p * (1 - P_S)
            denominator = numerator + (1 - p) * P_G
        else:
            numerator = p * P_S
            denominator = numerator + (1 - p) * (1 - P_G)

        posterior = p if denominator == 0 else numerator / denominator
        p_new = posterior + (1 - posterior) * P_T

        # Keep base BKT computation unchanged, but scale update magnitude by concept weight.
        weighted_p = p + weight * (p_new - p)
        entry["p_know"] = max(0.0, min(1.0, weighted_p))

        entry["questions_attempted"] += 1
        if correct:
            entry["correct_answers"] += 1

        if question_id and question_id not in entry["asked_question_ids"]:
            entry["asked_question_ids"].append(question_id)

        if question_id:
            if correct:
                if question_id in entry["wrong_question_ids"]:
                    entry["wrong_question_ids"].remove(question_id)
            else:
                if question_id not in entry["wrong_question_ids"]:
                    entry["wrong_question_ids"].append(question_id)

        entry["recent_answers"].append(1 if correct else 0)
        entry["recent_answers"] = normalize_recent_answers(entry["recent_answers"])

        entry["confidence"] = compute_confidence(
            questions_attempted=entry["questions_attempted"],
            recent_answers=entry["recent_answers"],
            attempt_weight=ATTEMPT_CONFIDENCE_WEIGHT,
            consistency_weight=CONSISTENCY_CONFIDENCE_WEIGHT,
            saturation_rate=ATTEMPT_SATURATION_RATE,
            min_attempts_for_reliability=MIN_ATTEMPTS_FOR_CONFIDENCE
        )

        data[concept] = entry
        updated[concept] = {
            **entry,
            "update_weight": round(weight, 4)
        }

    save_mastery(data)
    return updated

# ----------------------------
# ✅ Process Answer
# ----------------------------
def process_answer(concept, question_data, user_answer):
    correct = evaluate_answer(question_data, user_answer)

    raw_concepts = question_data.get("concepts_covered")

    if isinstance(raw_concepts, list):
        concepts_covered = []
        for value in raw_concepts:
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned and cleaned not in concepts_covered:
                    concepts_covered.append(cleaned)
    else:
        concepts_covered = []

    if not concepts_covered:
        primary = question_data.get("primary_concept") or concept
        if isinstance(primary, str) and primary.strip():
            concepts_covered = [primary.strip()]

    if not concepts_covered:
        concepts_covered = [concept]

    raw_weights = question_data.get("concept_weights")
    if isinstance(raw_weights, dict):
        concept_weights = {}
        for key, value in raw_weights.items():
            if not isinstance(key, str):
                continue
            cleaned_key = key.strip()
            if not cleaned_key or cleaned_key not in concepts_covered:
                continue

            try:
                weight = float(value)
            except Exception:
                continue

            concept_weights[cleaned_key] = max(0.0, min(1.0, weight))
    else:
        concept_weights = {}

    if not concept_weights:
        concept_weights = {c: 1.0 for c in concepts_covered}

    updates = update_mastery_multi(
        concepts_covered,
        question_data.get("id"),
        correct,
        concept_weights=concept_weights
    )

    primary_concept = question_data.get("primary_concept") or concept
    updated = updates.get(primary_concept) or next(iter(updates.values()))

    # recommendation = recommend_next_concept(concept)

    return {
        "correct": correct,
        "mastery": updated,
        "mastery_updates": updates,
        "concepts_covered": concepts_covered,
        "concept_weights": concept_weights,
    }


# ----------------------------
# ✅ Dashboard Helpers
# ----------------------------
def get_mastered_concepts():
    return [c for c, v in load_mastery().items() if v["p_know"] >= MASTERY_THRESHOLD]


def get_weak_concepts():
    return [c for c, v in load_mastery().items() if v["p_know"] <= WEAK_THRESHOLD]


def get_overall_progress():
    data = load_mastery()
    if not data:
        return 0.0

    avg = sum(v["p_know"] for v in data.values()) / len(data)
    return round(avg * 100, 2)
