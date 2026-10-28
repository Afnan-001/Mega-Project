import argparse
import json
import sys
from pathlib import Path
import networkx as nx
from pyvis.network import Network

# Force UTF-8 stdout encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ----------------------------
# Path Configuration
# ----------------------------
MAIN_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = MAIN_DIR / "outputs"
DATA_DIR = OUTPUTS_DIR / "data"

# Candidate inputs in priority order (DAG-cleaned output first, then fallback to enriched)
CANDIDATE_INPUTS = [
    DATA_DIR / "enriched_concepts_dag.json",
    DATA_DIR / "cleaned_enriched_concepts.json",
    DATA_DIR / "enriched_concepts.json",
]

DEFAULT_GML_OUTPUT = OUTPUTS_DIR / "graph_model" / "knowledge_graph.gml"
DEFAULT_HTML_OUTPUT = OUTPUTS_DIR / "graph_model" / "knowledge_graph.html"
DATA_HTML_OUTPUT = OUTPUTS_DIR / "data" / "knowledge_graph.html"


def resolve_input_file(custom_path: Path = None) -> Path:
    if custom_path:
        p = Path(custom_path)
        if not p.is_absolute():
            p = MAIN_DIR / p
        return p

    for candidate in CANDIDATE_INPUTS:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    return CANDIDATE_INPUTS[-1]


# ----------------------------
# Helpers
# ----------------------------
def ensure_list(value):
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def add_or_update_node(graph, node_name, node_type):
    """
    Adds node with type.
    If node already exists, preserve coarse category type as higher-level priority.
    """
    if not node_name:
        return

    if node_name not in graph:
        graph.add_node(node_name, label=node_name, type=node_type)
        return

    existing_type = graph.nodes[node_name].get("type")

    # Coarse category takes priority if a node appears both as category and concept
    if existing_type != "coarse_grained_category" and node_type == "coarse_grained_category":
        graph.nodes[node_name]["type"] = "coarse_grained_category"


# ----------------------------
# Graph Query Helpers
# ----------------------------
def get_coarse_category(graph, concept):
    return [
        src for src, dst, data in graph.in_edges(concept, data=True)
        if data.get("relation") == "CONTAINS"
    ]


def get_prerequisites(graph, concept):
    return [
        src for src, dst, data in graph.in_edges(concept, data=True)
        if data.get("relation") == "PREREQUISITE_FOR"
    ]


def get_dependents(graph, concept):
    return [
        dst for src, dst, data in graph.out_edges(concept, data=True)
        if data.get("relation") == "PREREQUISITE_FOR"
    ]


# ----------------------------
# Main Pipeline Function
# ----------------------------
def build_knowledge_graph(
    input_file: Path,
    gml_output: Path = DEFAULT_GML_OUTPUT,
    html_output: Path = DEFAULT_HTML_OUTPUT,
    test_concept: str = None,
):
    print("=" * 60)
    print("  AutoHKG: Knowledge Graph Builder & Visualizer")
    print("=" * 60)
    print(f"[INPUT]  Concepts File: {input_file}")
    print(f"[OUTPUT] GML Graph    : {gml_output}")
    print(f"[OUTPUT] HTML Vis     : {html_output}")

    if not input_file.exists():
        print(f"\n❌ Input file not found: {input_file}")
        sys.exit(1)

    if input_file.stat().st_size == 0:
        print(f"\n❌ Input file is empty: {input_file}")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        concepts = json.load(f)

    if not isinstance(concepts, list):
        print(f"\n❌ Expected a JSON array of concepts, got: {type(concepts)}")
        sys.exit(1)

    # ----------------------------
    # Build NetworkX DiGraph
    # ----------------------------
    G = nx.DiGraph()

    for c in concepts:
        if not isinstance(c, dict):
            continue

        concept_name = c.get("concept")
        if not concept_name:
            continue

        # 1. Fine-Grained Concept Node
        concept_node_type = c.get("node_type", "fine_grained_concept")
        add_or_update_node(G, concept_name, concept_node_type)

        # 2. Coarse-Grained Category Nodes (CONTAINS relation: category -> concept)
        coarse_categories = []
        coarse_categories.extend(ensure_list(c.get("coarse_grained_category")))
        coarse_categories.extend(ensure_list(c.get("parent_concept")))
        coarse_categories = list(dict.fromkeys(coarse_categories))  # preserve order & unique

        cat_edge_meta = c.get("category_edge") or {}
        cat_conf = float(cat_edge_meta.get("confidence", 1.0)) if isinstance(cat_edge_meta, dict) else 1.0
        cat_evidence = cat_edge_meta.get("evidence_chunk", "") if isinstance(cat_edge_meta, dict) else ""

        for category in coarse_categories:
            if category and category != concept_name:
                add_or_update_node(G, category, "coarse_grained_category")
                G.add_edge(
                    category,
                    concept_name,
                    relation="CONTAINS",
                    weight=cat_conf,
                    evidence_chunk=cat_evidence,
                )

        # 3. Prerequisite Relationships (PREREQUISITE_FOR relation: prereq -> concept)
        # Check structured prerequisite_edges first for confidence & evidence
        prereq_edges_list = c.get("prerequisite_edges", [])
        prereq_meta_map = {}
        if isinstance(prereq_edges_list, list):
            for edge_obj in prereq_edges_list:
                if isinstance(edge_obj, dict) and edge_obj.get("prerequisite"):
                    prereq_meta_map[edge_obj["prerequisite"]] = edge_obj

        prerequisites = ensure_list(c.get("prerequisites"))
        for prereq in prerequisites:
            if prereq and prereq != concept_name:
                add_or_update_node(G, prereq, "fine_grained_concept")

                edge_meta = prereq_meta_map.get(prereq, {})
                conf = float(edge_meta.get("confidence", 0.8)) if edge_meta else 0.8
                evidence = edge_meta.get("evidence_chunk", "") if edge_meta else ""

                G.add_edge(
                    prereq,
                    concept_name,
                    relation="PREREQUISITE_FOR",
                    weight=conf,
                    evidence_chunk=evidence,
                )

    # ----------------------------
    # Graph Statistics & DAG Check
    # ----------------------------
    node_type_counts = {}
    for _, attrs in G.nodes(data=True):
        node_type = attrs.get("type", "unknown")
        node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

    edge_type_counts = {}
    for _, _, attrs in G.edges(data=True):
        relation = attrs.get("relation", "unknown")
        edge_type_counts[relation] = edge_type_counts.get(relation, 0) + 1

    # Check if prerequisite relationships form a valid DAG (Acyclic)
    prereq_subgraph = nx.DiGraph([
        (u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "PREREQUISITE_FOR"
    ])
    is_dag = nx.is_directed_acyclic_graph(prereq_subgraph)

    print("\n--- GRAPH STATS ---")
    print(f"✅ Total Nodes: {G.number_of_nodes()}")
    print(f"✅ Total Edges: {G.number_of_edges()}")

    print("\n--- NODE TYPE COUNTS ---")
    for node_type, count in node_type_counts.items():
        print(f"✅ {node_type}: {count}")

    print("\n--- EDGE TYPE COUNTS ---")
    for relation, count in edge_type_counts.items():
        print(f"✅ {relation}: {count}")

    print("\n--- PREREQUISITE DAG STATUS ---")
    if is_dag:
        print("✅ Prerequisite Graph is a strictly Acyclic DAG (Pedagogically Valid).")
    else:
        print("⚠️ Prerequisite Graph contains cycles! Run post_process_dag.py to resolve cycles.")

    # ----------------------------
    # Save Graph in GML Format
    # ----------------------------
    gml_output.parent.mkdir(parents=True, exist_ok=True)
    nx.write_gml(G, gml_output)
    print(f"\n✅ Graph saved at: {gml_output}")



    # ----------------------------
    # Interactive Pyvis Visualization
    # ----------------------------
    net = Network(
        height="800px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#222222",
    )

    NODE_COLORS = {
        "coarse_grained_category": "#FF6B6B",   # Coral / red
        "fine_grained_concept": "#4ECDC4",      # Teal
        "unknown": "#97C2FC",
    }

    NODE_SIZES = {
        "coarse_grained_category": 28,
        "fine_grained_concept": 16,
        "unknown": 16,
    }

    for node, attrs in G.nodes(data=True):
        node_type = attrs.get("type", "unknown")
        net.add_node(
            node,
            label=node,
            title=f"<strong>{node}</strong><br>Type: {node_type}<br>In-degree: {G.in_degree(node)}<br>Out-degree: {G.out_degree(node)}",
            color=NODE_COLORS.get(node_type, "#97C2FC"),
            size=NODE_SIZES.get(node_type, 16),
        )

    EDGE_COLORS = {
        "CONTAINS": "#6c757d",
        "PREREQUISITE_FOR": "#2B6CB0",
    }

    for source, target, attrs in G.edges(data=True):
        relation = attrs.get("relation", "")
        weight = attrs.get("weight", 1.0)
        evidence = attrs.get("evidence_chunk", "")

        tooltip = f"<strong>{relation}</strong><br>From: {source}<br>To: {target}<br>Confidence: {weight:.2f}"
        if evidence:
            tooltip += f"<br>Evidence Chunk: {evidence}"

        net.add_edge(
            source,
            target,
            title=tooltip,
            color=EDGE_COLORS.get(relation, "#999999"),
            arrows="to",
        )

    html_output.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(html_output))
    print(f"✅ HTML visualization saved at: {html_output}")

    # Also mirror HTML inside outputs/data/ for convenience if paths differ
    if DATA_HTML_OUTPUT.resolve() != html_output.resolve():
        try:
            DATA_HTML_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            net.write_html(str(DATA_HTML_OUTPUT))
            print(f"✅ HTML visualization mirrored at: {DATA_HTML_OUTPUT}")
        except Exception:
            pass

    # ----------------------------
    # Concept Query Demonstration
    # ----------------------------
    # Select test concept: passed via argument, or "Abstract Syntax Tree", or node with most edges
    sample_candidate = test_concept
    if not sample_candidate or sample_candidate not in G:
        for preferred in ["Abstract Syntax Tree", "Intermediate Code", "Syntax Tree", "Parse Tree"]:
            if preferred in G:
                sample_candidate = preferred
                break

    if not sample_candidate or sample_candidate not in G:
        # Pick node with highest degree
        nodes_by_degree = sorted(G.degree(), key=lambda x: x[1], reverse=True)
        if nodes_by_degree:
            sample_candidate = nodes_by_degree[0][0]

    if sample_candidate and sample_candidate in G:
        print(f"\n📌 Concept Query Inspection: '{sample_candidate}'")
        categories = get_coarse_category(G, sample_candidate)
        prereqs = get_prerequisites(G, sample_candidate)
        dependents = get_dependents(G, sample_candidate)

        print(f"   Coarse Categories       : {categories if categories else 'None'}")
        print(f"   Prerequisites (Requires): {prereqs if prereqs else 'None'}")
        print(f"   Dependents (Leads To)   : {dependents if dependents else 'None'}")
    else:
        print("\n⚠️ No concept found to query.")

    print("\n" + "=" * 60)
    print("  KNOWLEDGE GRAPH GENERATION COMPLETE")
    print("=" * 60)
    return G


def main():
    parser = argparse.ArgumentParser(
        description="AutoHKG Knowledge Graph Builder: builds NetworkX DiGraph, GML export, and PyVis HTML visualization."
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=None,
        help="Path to enriched concepts JSON file (default: auto-detect enriched_concepts_dag.json or enriched_concepts.json)",
    )
    parser.add_argument(
        "--gml-output", "-g",
        type=Path,
        default=DEFAULT_GML_OUTPUT,
        help="Path to save output GML file (default: outputs/graph_model/knowledge_graph.gml)",
    )
    parser.add_argument(
        "--html-output", "-ht",
        type=Path,
        default=DEFAULT_HTML_OUTPUT,
        help="Path to save output PyVis HTML file (default: outputs/data/knowledge_graph.html)",
    )
    parser.add_argument(
        "--concept", "-c",
        type=str,
        default=None,
        help="Concept name to test inspection queries for (default: auto-detected)",
    )

    args = parser.parse_args()
    input_file = resolve_input_file(args.input)

    build_knowledge_graph(
        input_file=input_file,
        gml_output=args.gml_output,
        html_output=args.html_output,
        test_concept=args.concept,
    )


if __name__ == "__main__":
    main()

