import json
from pathlib import Path
import sys

import streamlit as st

"""
Test app that simulates the adaptive learning flow end-to-end 
(question generation, answer processing, and concept navigation) using isolated runtime files 
in test_scripts/data.

"""

ROOT_DIR = Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT_DIR / "Main"
COGRAG_DIR = MAIN_DIR / "CogRAG"

if str(COGRAG_DIR) not in sys.path:
    sys.path.insert(0, str(COGRAG_DIR))
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

import adaptive_engine as ae
import question_generator as qg

# ----------------------------
# ✅ Test Data Paths (isolated)
# ----------------------------
TEST_DATA_DIR = ROOT_DIR / "test_scripts" / "data"
TEST_MASTERY_FILE = TEST_DATA_DIR / "mastery_scores.json"
TEST_NAV_STATE_FILE = TEST_DATA_DIR / "navigation_state.json"
TEST_GENERATED_FILE = TEST_DATA_DIR / "generated_mcqs.json"

CONCEPT_FILES = [
    MAIN_DIR / "outputs" / "data" / "cleaned_enriched_concepts.json",
    MAIN_DIR / "outputs" / "data" / "enriched_concepts.json",
    ROOT_DIR / "data" / "cleaned_enriched_concepts.json",
    ROOT_DIR / "data" / "enriched_concepts.json",
]


def load_concept_names():
    concept_file = next((p for p in CONCEPT_FILES if p.exists()), None)
    if not concept_file:
        return []

    try:
        data = json.loads(concept_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    concepts = []
    for item in data:
        concept = item.get("concept")
        if isinstance(concept, str) and concept.strip():
            concepts.append(concept.strip())

    return sorted(set(concepts), key=str.lower)


def initialize_test_mastery(concepts):
    mastery = {}
    for concept in concepts:
        mastery[concept] = {
            "p_know": 0.2,
            "confidence": 0.0,
            "questions_attempted": 0,
            "correct_answers": 0,
            "recent_answers": [],
            "asked_question_ids": [],
            "wrong_question_ids": [],
        }

    TEST_MASTERY_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_MASTERY_FILE.write_text(
        json.dumps(mastery, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


def ensure_test_runtime_files(concepts):
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not TEST_MASTERY_FILE.exists():
        initialize_test_mastery(concepts)

    if not TEST_NAV_STATE_FILE.exists():
        TEST_NAV_STATE_FILE.write_text(
            json.dumps(
                {
                    "current_concept": None,
                    "return_target": None,
                    "recent_concepts": [],
                },
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    if not TEST_GENERATED_FILE.exists():
        TEST_GENERATED_FILE.write_text("{}", encoding="utf-8")


def wire_test_paths():
    # adaptive engine state files
    ae.MASTERY_FILE = TEST_MASTERY_FILE
    ae.NAVIGATION_STATE_FILE = TEST_NAV_STATE_FILE

    # question generation persistence
    qg.OUTPUT_FILE = TEST_GENERATED_FILE


def set_start_concept(concept):
    state = ae.load_navigation_state()
    state["current_concept"] = concept
    state["return_target"] = None

    recent = state.get("recent_concepts", [])
    if not isinstance(recent, list):
        recent = []

    recent.append(concept)
    state["recent_concepts"] = recent
    ae.save_navigation_state(state)


# ----------------------------
# ✅ Bootstrapping
# ----------------------------
concept_names = load_concept_names()
ensure_test_runtime_files(concept_names)
wire_test_paths()

# ----------------------------
# ✅ Page Config
# ----------------------------
st.set_page_config(page_title="Adaptive DBMS Tutor - Test Flow", layout="centered")
st.title("🧪 Adaptive DBMS Tutor - Test Flow")
st.caption("Uses isolated runtime files under test_scripts/data")

# ----------------------------
# ✅ Session State Init
# ----------------------------
if "question_data" not in st.session_state:
    st.session_state.question_data = None

if "concept" not in st.session_state:
    st.session_state.concept = None

if "secondary_concepts" not in st.session_state:
    st.session_state.secondary_concepts = []

if "concepts_covered" not in st.session_state:
    st.session_state.concepts_covered = []

if "concept_weights" not in st.session_state:
    st.session_state.concept_weights = {}

if "difficulty" not in st.session_state:
    st.session_state.difficulty = None

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "result" not in st.session_state:
    st.session_state.result = None

# ----------------------------
# ✅ Sidebar Controls + Dashboard
# ----------------------------
st.sidebar.header("🧭 Test Controls")

if concept_names:
    selected_start = st.sidebar.selectbox("Start From Concept", concept_names)

    if st.sidebar.button("Set Start Concept"):
        set_start_concept(selected_start)
        st.session_state.question_data = None
        st.session_state.submitted = False
        st.session_state.result = None
        st.sidebar.success(f"Start concept set to: {selected_start}")
else:
    st.sidebar.error("No concepts available from enriched concept file.")

st.sidebar.header("📊 Dashboard")
progress = ae.get_overall_progress()
st.sidebar.metric("Overall Knowledge (%)", progress)

st.sidebar.subheader("✅ Mastered Concepts")
st.sidebar.write(ae.get_mastered_concepts())

st.sidebar.subheader("⚠️ Weak Concepts")
st.sidebar.write(ae.get_weak_concepts())

# ----------------------------
# ✅ Generate Question
# ----------------------------
if st.button("🎯 Generate Question"):
    data = ae.get_adaptive_question()

    if data and data["question"]:
        st.session_state.question_data = data["question"]
        st.session_state.concept = data["concept"]
        st.session_state.secondary_concepts = data.get("secondary_concepts", [])
        st.session_state.concepts_covered = data.get("concepts_covered", [data["concept"]])
        st.session_state.concept_weights = data.get("concept_weights", {})
        st.session_state.difficulty = data["difficulty"]
        st.session_state.submitted = False
        st.session_state.result = None

# ----------------------------
# ✅ Display Question
# ----------------------------
if st.session_state.question_data:
    q = st.session_state.question_data

    st.markdown(f"### 📚 Concept: `{st.session_state.concept}`")
    st.markdown(f"### 🧠 Difficulty: `{st.session_state.difficulty.upper()}`")

    secondary_concepts = st.session_state.secondary_concepts or []
    concept_weights = st.session_state.concept_weights or {}

    if secondary_concepts:
        st.markdown(f"### 🔗 Secondary Concepts: `{', '.join(secondary_concepts)}`")

    if concept_weights:
        weight_lines = [f"{c}: {round(float(w), 3)}" for c, w in concept_weights.items()]
        st.markdown(f"### ⚖️ Concept Weights: `{'; '.join(weight_lines)}`")

    st.write(q["question"])

    selected_option = st.radio(
        "Select your answer:",
        q["options"],
        index=None,
        key="options"
    )

    if st.button("✅ Submit Answer"):
        if not selected_option:
            st.warning("Please select an option")
        else:
            user_answer = selected_option.split(".")[0]

            result = ae.process_answer(
                st.session_state.concept,
                st.session_state.question_data,
                user_answer
            )

            st.session_state.result = result
            st.session_state.submitted = True

# ----------------------------
# ✅ Show Result
# ----------------------------
if st.session_state.submitted and st.session_state.result:
    q = st.session_state.question_data
    result = st.session_state.result
    mastery_data = result["mastery"]
    mastery_updates = result.get("mastery_updates", {})
    concepts_covered = result.get("concepts_covered", st.session_state.concepts_covered)
    concept_weights = result.get("concept_weights", st.session_state.concept_weights)

    st.subheader("📌 Result")

    if result["correct"]:
        st.success("✅ Correct!")
    else:
        st.error("❌ Incorrect")

    st.write(f"**Correct Answer:** {q['answer']}")

    st.subheader("📊 Knowledge Update (BKT)")
    st.write(f"📈 Probability of Knowing (p_know): **{round(mastery_data['p_know'], 3)}**")
    st.write(f"📚 Questions Attempted: {mastery_data['questions_attempted']}")
    st.write(f"✅ Correct Answers: {mastery_data['correct_answers']}")

    if concept_weights:
        st.write("⚖️ Applied Weights:")
        for c, w in concept_weights.items():
            st.write(f"- {c}: {round(float(w), 3)}")

    if mastery_updates:
        st.subheader("📈 Per-Concept Mastery Updates")
        concepts_for_display = concepts_covered or list(mastery_updates.keys())

        for concept in concepts_for_display:
            entry = mastery_updates.get(concept)
            if not entry:
                continue

            st.markdown(f"**{concept}**")
            st.write(f"- p_know: {round(entry.get('p_know', 0.0), 3)}")
            st.write(f"- update_weight: {round(entry.get('update_weight', 1.0), 3)}")
            st.write(f"- attempted: {entry.get('questions_attempted', 0)}")
            st.write(f"- correct: {entry.get('correct_answers', 0)}")

    st.subheader("📄 Source Chunks")
    sources = q.get("source_chunks", [])

    if sources:
        st.code("\n".join(sources))
    else:
        st.code("No source chunks available")

    if st.button("➡️ Next Question"):
        st.session_state.question_data = None
        st.session_state.secondary_concepts = []
        st.session_state.concepts_covered = []
        st.session_state.concept_weights = {}
        st.session_state.submitted = False
        st.session_state.result = None
