import json
from pathlib import Path
import sys

import streamlit as st

'''
Test UI for generating DBMS MCQs from a selected graph-backed concept using 
isolated test data files (mastery, navigation state, and generated output) under test_scripts/data.
'''

ROOT_DIR = Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT_DIR / "Main"
COGRAG_DIR = MAIN_DIR / "CogRAG"

if str(COGRAG_DIR) not in sys.path:
    sys.path.insert(0, str(COGRAG_DIR))


if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

import question_generator
import adaptive_engine as ae

TEST_DATA_DIR = ROOT_DIR / "test_scripts" / "data"
TEST_OUTPUT_FILE = TEST_DATA_DIR / "generated_mcqs.json"
TEST_MASTERY_FILE = TEST_DATA_DIR / "mastery_scores.json"
TEST_NAV_FILE = TEST_DATA_DIR / "navigation_state.json"
CONCEPT_FILES = [
    MAIN_DIR / "outputs" / "data" / "cleaned_enriched_concepts.json",
    MAIN_DIR / "outputs" / "data" / "enriched_concepts.json",
    ROOT_DIR / "data" / "cleaned_enriched_concepts.json",
    ROOT_DIR / "data" / "enriched_concepts.json",
]


def load_concept_map():
    concept_file = next((p for p in CONCEPT_FILES if p.exists()), None)
    if not concept_file:
        return {}, None

    try:
        data = json.loads(concept_file.read_text(encoding="utf-8"))
    except Exception:
        return {}, concept_file

    concept_map = {}
    for item in data:
        concept = item.get("concept")
        if not isinstance(concept, str) or not concept.strip():
            continue

        prereqs = item.get("prerequisites", [])
        if isinstance(prereqs, str):
            prereqs = [prereqs] if prereqs.strip() else []
        if not isinstance(prereqs, list):
            prereqs = []

        cleaned_prereqs = [
            p.strip() for p in prereqs
            if isinstance(p, str) and p.strip()
        ]

        concept_map[concept.strip()] = cleaned_prereqs

    return concept_map, concept_file


def initialize_test_mastery(concept_map):
    mastery = {}

    for concept in concept_map.keys():
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

st.set_page_config(page_title="MCQ Generation Test UI", layout="centered")
st.title("🧪 Question Generation Test")

st.markdown("Choose a primary concept and run the test question generation.")

concept_map, concept_file = load_concept_map()

if not concept_map:
    st.error("Could not load concept list from data/enriched concept files.")
    st.stop()

# Use isolated mastery path for this test app.
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
ae.MASTERY_FILE = TEST_MASTERY_FILE
ae.NAVIGATION_STATE_FILE = TEST_NAV_FILE
question_generator.OUTPUT_FILE = TEST_OUTPUT_FILE

# Fresh mastery initialization once when this app process/session starts.
if "test_mastery_initialized" not in st.session_state:
    initialize_test_mastery(concept_map)
    st.session_state.test_mastery_initialized = True

# Restrict to concepts that are actually present in the loaded graph
graph_nodes = {
    node for node in ae.G.nodes
    if isinstance(node, str) and node.strip()
}

concept_options = sorted(
    [concept for concept in concept_map.keys() if concept in graph_nodes],
    key=str.lower,
)

if not concept_options:
    st.error(
        "No overlap found between concept file and graph nodes. "
        "Please verify Main/outputs/data and Main/outputs/graph_model are from the same build."
    )
    st.stop()

primary_concept = st.selectbox("Primary Concept", concept_options)
difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=2)

primary_clean = primary_concept.strip()

if primary_clean and primary_clean in concept_map:
    prereq_list = concept_map[primary_clean]
    st.write(f"Loaded concept list from: `{concept_file}`")
    # st.write(f"Graph-backed options available: {len(concept_options)}")
    st.write("Prerequisites:", prereq_list if prereq_list else "None")
else:
    st.error("No concept as such exists in the concept list.")

if st.button("🎯 Generate Test MCQ"):
    if not primary_clean:
        st.warning("Please select a primary concept")
    elif primary_clean not in concept_map:
        st.error("No concept as such exists in the concept list.")
    else:
        TEST_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Overwrite existing test output for each run
        if TEST_OUTPUT_FILE.exists():
            TEST_OUTPUT_FILE.unlink()

        mastery_data = ae.load_mastery()

        secondary_concepts = ae.select_secondary_concepts(
            primary_concept=primary_clean,
            difficulty=difficulty,
            data=mastery_data,
        )

        st.write("Secondary candidates (unmastered prerequisites):", secondary_concepts)

        q = question_generator.generate_question(
            concept_name=primary_clean,
            difficulty=difficulty,
            asked_ids=[],
            wrong_ids=[],
            secondary_concepts=secondary_concepts,
        )

        if not q:
            st.error("Question generation failed.")
        else:
            st.success("Question generated and saved to test_scripts/data/generated_mcqs.json")
            st.subheader("Question")
            st.write(q.get("question", ""))
            st.write("Options:")
            for opt in q.get("options", []):
                st.write(f"- {opt}")

            st.write("Answer:", q.get("answer"))
            st.write("Concepts Covered:", q.get("concepts_covered"))
            st.write("Concept Weights:", q.get("concept_weights"))
            st.write("Source Chunks:", q.get("source_chunks"))

            if TEST_OUTPUT_FILE.exists():
                payload = json.loads(TEST_OUTPUT_FILE.read_text(encoding="utf-8"))
                st.subheader("Saved JSON Preview")
                st.json(payload)
            else:
                st.warning("Expected output file not found after generation.")
