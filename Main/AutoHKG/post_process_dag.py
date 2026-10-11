from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

DATA_DIR = MAIN_DIR / "outputs" / "data"
DEFAULT_INPUT = DATA_DIR / "enriched_concepts.json"
DEFAULT_OUTPUT = DATA_DIR / "enriched_concepts_dag.json"


def post_process_dag(
    input_file: Path,
    output_file: Path,
    perform_transitive_reduction: bool = False,
) -> list[dict]:
    """
    Post-processing safety check for LLM-generated relationship graphs.
    Enforces a Directed Acyclic Graph (DAG) by detecting prerequisite cycles
    and removing the edge with the lowest confidence score in each cycle.
    """
    print("=" * 60)
    print("  DAG Cycle Detection & Removal Post-Processor")
    print("=" * 60)
    print(f"[INPUT]  File : {input_file}")
    print(f"[OUTPUT] File : {output_file}")

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        enriched_list = json.load(f)

    if not isinstance(enriched_list, list):
        raise ValueError("Input JSON must be a list of enriched concept objects.")

    try:
        import networkx as nx
    except ImportError as e:
        print(f"❌ networkx is required for DAG post-processing: {e}")
        print("Please install networkx: pip install networkx")
        sys.exit(1)

    G = nx.DiGraph()
    edge_metadata_map = {}

    # Build Directed Graph from prerequisite edges
    for concept_data in enriched_list:
        target = concept_data.get("concept")
        if not target:
            continue

        for edge in concept_data.get("prerequisite_edges", []):
            source = edge.get("prerequisite")
            if not source:
                continue

            conf = edge.get("confidence", 0.6)
            G.add_edge(source, target, weight=conf)
            edge_metadata_map[(source, target)] = edge

    print(f"[INFO] Initial Prerequisite Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # 1. Cycle Detection & Iterative Removal (Lowest Confidence Edge First)
    cycles_removed_count = 0
    removed_edges_log = []

    while not nx.is_directed_acyclic_graph(G):
        try:
            cycle = nx.find_cycle(G, orientation="original")
        except nx.NetworkXNoCycle:
            break

        # Find edge in the cycle with the lowest confidence score
        min_edge = min(cycle, key=lambda e: G[e[0]][e[1]].get("weight", 0.0))
        src, tgt = min_edge[0], min_edge[1]
        removed_conf = G[src][tgt].get("weight", 0.0)

        G.remove_edge(src, tgt)
        cycles_removed_count += 1
        removed_edges_log.append((src, tgt, removed_conf))
        print(f"  [CYCLE RESOLVED #{cycles_removed_count}] Removed edge: '{src}' -> '{tgt}' (Confidence: {removed_conf})")

    if cycles_removed_count == 0:
        print("  [SUCCESS] No prerequisite cycles detected. Graph is already a valid DAG!")
    else:
        print(f"  [SUCCESS] Resolved {cycles_removed_count} cycle(s). Graph is now a strict DAG.")

    # 2. Optional Transitive Reduction
    if perform_transitive_reduction and G.number_of_edges() > 0:
        print("[INFO] Performing Transitive Reduction to prune redundant shortcut edges...")
        TR = nx.transitive_reduction(G)
        edges_before = G.number_of_edges()
        G = TR
        edges_after = G.number_of_edges()
        print(f"  [REDUCTION] Pruned {edges_before - edges_after} redundant transitive shortcut edges.")

    # 3. Update Enriched Concept Data with Cleaned Prerequisite Edges
    node_to_prereq_edges: dict[str, list[dict]] = {}
    for (src, tgt) in G.edges():
        if tgt not in node_to_prereq_edges:
            node_to_prereq_edges[tgt] = []
        if (src, tgt) in edge_metadata_map:
            node_to_prereq_edges[tgt].append(edge_metadata_map[(src, tgt)])

    cleaned_enriched = []
    for concept_data in enriched_list:
        updated = dict(concept_data)
        tgt = updated.get("concept")
        if tgt:
            cleaned_edges = node_to_prereq_edges.get(tgt, [])
            updated["prerequisite_edges"] = cleaned_edges
            updated["prerequisites"] = [e["prerequisite"] for e in cleaned_edges]
        cleaned_enriched.append(updated)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_enriched, f, indent=4, ensure_ascii=False)

    print("=" * 60)
    print(f"[COMPLETED] Clean DAG concepts saved to: {output_file}")
    print("=" * 60)

    return cleaned_enriched


def main():
    parser = argparse.ArgumentParser(
        description="Standalone DAG Cycle Detection & Removal post-processor for prerequisite concept graphs."
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to input enriched concepts JSON file (default: outputs/data/enriched_concepts.json)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to output DAG-cleaned concepts JSON file (default: outputs/data/enriched_concepts_dag.json)"
    )
    parser.add_argument(
        "--transitive-reduction", "-tr",
        action="store_true",
        help="Also perform transitive reduction to remove redundant direct edges (e.g. if A->B and B->C, remove A->C)"
    )

    args = parser.parse_args()

    post_process_dag(
        input_file=args.input,
        output_file=args.output,
        perform_transitive_reduction=args.transitive_reduction,
    )


if __name__ == "__main__":
    main()
