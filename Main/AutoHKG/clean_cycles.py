
import json
from pathlib import Path
import networkx as nx

# ----------------------------
# Files
# ----------------------------
MAIN_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = MAIN_DIR / "outputs"
INPUT_FILE = OUTPUTS_DIR / "data" / "enriched_concepts.json"
OUTPUT_FILE = OUTPUTS_DIR / "data" / "cleaned_enriched_concepts.json"
REMOVED_EDGES_FILE = OUTPUTS_DIR / "data" / "removed_prerequisite_cycle_edges.json"

# ----------------------------
# Config
# ----------------------------
MAX_ITERATIONS = 10000


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
# Save JSON
# ----------------------------
def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ----------------------------
# Build prerequisite graph
# ----------------------------
def build_prerequisite_graph(concepts):
    """
    Builds prerequisite-only graph:
    prerequisite -> concept

    Edge contains:
    - confidence
    - evidence_chunk
    - evidence_text
    """

    G = nx.DiGraph()

    for item in concepts:
        concept = item.get("concept")

        if not concept:
            continue

        G.add_node(concept)

        prerequisite_edges = item.get("prerequisite_edges", [])

        for edge in prerequisite_edges:
            prereq = edge.get("prerequisite")

            if not prereq:
                continue

            if prereq == concept:
                continue

            confidence = edge.get("confidence", 0.0)

            try:
                confidence = float(confidence)
            except Exception:
                confidence = 0.0

            G.add_node(prereq)

            G.add_edge(
                prereq,
                concept,
                confidence=confidence,
                evidence_chunk=edge.get("evidence_chunk", ""),
                evidence_text=edge.get("evidence_text", "")
            )

    return G


# ----------------------------
# Find lowest confidence edge in cycle
# ----------------------------
def find_lowest_confidence_edge_in_cycle(G, cycle):
    """
    cycle from networkx.simple_cycles looks like:
    [A, B, C]

    It represents:
    A -> B -> C -> A

    Returns the edge with lowest confidence.
    """

    cycle_edges = []

    for i in range(len(cycle)):
        src = cycle[i]
        dst = cycle[(i + 1) % len(cycle)]

        edge_data = G.get_edge_data(src, dst, default={})
        confidence = edge_data.get("confidence", 0.0)

        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        cycle_edges.append({
            "source": src,
            "target": dst,
            "confidence": confidence,
            "evidence_chunk": edge_data.get("evidence_chunk", ""),
            "evidence_text": edge_data.get("evidence_text", "")
        })

    lowest_edge = min(
        cycle_edges,
        key=lambda x: x["confidence"]
    )

    return lowest_edge


# ----------------------------
# Remove edge from enriched concepts JSON
# ----------------------------
def remove_prerequisite_edge_from_data(concepts, source, target):
    """
    Removes prerequisite edge:
    source -> target

    This means:
    source is removed from target's prerequisite_edges and prerequisites.
    """

    for item in concepts:
        concept = item.get("concept")

        if concept != target:
            continue

        # Remove from prerequisite_edges
        old_edges = item.get("prerequisite_edges", [])

        new_edges = [
            edge for edge in old_edges
            if edge.get("prerequisite") != source
        ]

        item["prerequisite_edges"] = new_edges

        # Keep prerequisites list in sync
        item["prerequisites"] = [
            edge.get("prerequisite")
            for edge in new_edges
            if edge.get("prerequisite")
        ]

        return True

    return False


# ----------------------------
# Cycle cleanup
# ----------------------------
def clean_cycles(concepts):
    """
    Iteratively:
    1. Build prerequisite graph
    2. Find one cycle
    3. Remove lowest-confidence edge in that cycle
    4. Repeat until no cycles remain
    """

    removed_edges = []
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1

        G = build_prerequisite_graph(concepts)

        try:
            cycle = next(nx.simple_cycles(G))
        except StopIteration:
            print("✅ No prerequisite cycles remaining")
            break

        lowest_edge = find_lowest_confidence_edge_in_cycle(G, cycle)

        source = lowest_edge["source"]
        target = lowest_edge["target"]

        removed = remove_prerequisite_edge_from_data(
            concepts=concepts,
            source=source,
            target=target
        )

        if not removed:
            print(f"⚠️ Could not remove edge {source} -> {target}")
            break

        removed_record = {
            "iteration": iteration,
            "removed_edge": f"{source} -> {target}",
            "source": source,
            "target": target,
            "confidence": lowest_edge["confidence"],
            "evidence_chunk": lowest_edge.get("evidence_chunk", ""),
            "evidence_text": lowest_edge.get("evidence_text", ""),
            "cycle": cycle
        }

        removed_edges.append(removed_record)

        print(
            f"[{iteration}] Removed lowest-confidence edge: "
            f"{source} -> {target} | confidence={lowest_edge['confidence']}"
        )

    if iteration >= MAX_ITERATIONS:
        print("⚠️ Max iterations reached. Some cycles may still remain.")

    final_graph = build_prerequisite_graph(concepts)
    remaining_cycles = list(nx.simple_cycles(final_graph))

    return concepts, removed_edges, remaining_cycles


# ----------------------------
# Main
# ----------------------------
def main():
    print("📥 Loading enriched concepts...")

    concepts = load_json(INPUT_FILE)

    print(f"✅ Loaded {len(concepts)} concepts")

    original_graph = build_prerequisite_graph(concepts)
    original_cycles = list(nx.simple_cycles(original_graph))

    print("\n--- BEFORE CLEANUP ---")
    print(f"Nodes: {original_graph.number_of_nodes()}")
    print(f"Prerequisite edges: {original_graph.number_of_edges()}")
    print(f"Cycles found: {len(original_cycles)}")

    cleaned_concepts, removed_edges, remaining_cycles = clean_cycles(concepts)

    cleaned_graph = build_prerequisite_graph(cleaned_concepts)

    print("\n--- AFTER CLEANUP ---")
    print(f"Nodes: {cleaned_graph.number_of_nodes()}")
    print(f"Prerequisite edges: {cleaned_graph.number_of_edges()}")
    print(f"Removed edges: {len(removed_edges)}")
    print(f"Remaining cycles: {len(remaining_cycles)}")

    save_json(OUTPUT_FILE, cleaned_concepts)
    save_json(REMOVED_EDGES_FILE, removed_edges)

    print("\n✅ Cleaned enriched concepts saved")
    print(f"📦 Output file: {OUTPUT_FILE}")

    print("\n✅ Removed cyclic edges report saved")
    print(f"📦 Output file: {REMOVED_EDGES_FILE}")


if __name__ == "__main__":
    main()
