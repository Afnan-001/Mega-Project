"""
server/routers/graph.py — Graph export and concept ego-network neighborhood query endpoints.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse

from server.core.dependencies import get_current_user
from server.models.knowledge import (
    ConceptChunkMappingDocument,
    ContentChunkDocument,
    KnowledgeGraphDocument,
)
from server.models.schemas import ConceptNeighborhoodResponse
from server.models.user import UserDocument

router = APIRouter(prefix="/api/v1/graph", tags=["Knowledge Graph"])

SERVER_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = SERVER_DIR.parent

CANDIDATE_HTML_PATHS = [
    ROOT_DIR / "outputs" / "graph_model" / "knowledge_graph.html",
    ROOT_DIR / "Main" / "outputs" / "graph_model" / "knowledge_graph.html",
    ROOT_DIR / "Main" / "outputs" / "data" / "knowledge_graph.html",
]

CANDIDATE_UTILS_PATHS = [
    ROOT_DIR / "lib" / "bindings" / "utils.js",
    ROOT_DIR / "Main" / "lib" / "bindings" / "utils.js",
]

# Added to the generated PyVis page at response time.  This keeps generated
# graph artifacts immutable while allowing the React dashboard to select and
# focus a concept in its iframe.
IFRAME_HIGHLIGHT_SCRIPT = """
<script>
window.addEventListener('message', function (event) {
  var message = event.data || {};
  if (message.type !== 'edugraph:highlight-concept' || !network || !data || !data.nodes) return;
  var query = String(message.concept || '').trim().toLowerCase();
  if (!query) { network.unselectAll(); return; }
  var matchingId = data.nodes.getIds().find(function (id) {
    var node = data.nodes.get(id) || {};
    return String(id).toLowerCase() === query || String(node.label || '').toLowerCase() === query;
  });
  if (matchingId === undefined) return;
  network.selectNodes([matchingId], false);
  network.focus(matchingId, { scale: 1.45, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
});
</script>
"""


@router.get(
    "/raw-html",
    response_class=HTMLResponse,
    summary="Serve rendered interactive PyVis Knowledge Graph HTML from outputs/graph_model",
)
@router.get(
    "/{course_id}/raw-html",
    response_class=HTMLResponse,
    summary="Serve rendered interactive PyVis Knowledge Graph HTML for a course or default outputs/graph_model",
)
async def get_raw_graph_html(course_id: str | None = None):
    """
    Returns the generated interactive Vis.js Knowledge Graph HTML from outputs/graph_model or per-course workspace.
    Inlines utils.js so the graph is completely standalone and functional inside iframes.
    """
    candidate_paths = []
    if course_id:
        from server.config import settings
        candidate_paths.append(settings.COURSE_OUTPUTS_DIR / course_id / "knowledge_graph.html")
    candidate_paths.extend(CANDIDATE_HTML_PATHS)

    html_file = None
    for p in candidate_paths:
        if p.exists() and p.stat().st_size > 0:
            html_file = p
            break

    if not html_file:
        raise HTTPException(
            status_code=404,
            detail="Interactive Knowledge Graph HTML not found inside outputs/graph_model.",
        )

    content = html_file.read_text(encoding="utf-8", errors="replace")

    # Inline utils.js if present so iframe has no broken relative script dependencies
    utils_content = ""
    for up in CANDIDATE_UTILS_PATHS:
        if up.exists() and up.stat().st_size > 0:
            utils_content = up.read_text(encoding="utf-8", errors="replace")
            break

    if utils_content and 'src="lib/bindings/utils.js"' in content:
        content = content.replace(
            '<script src="lib/bindings/utils.js"></script>',
            f'<script>\n/* Inlined lib/bindings/utils.js */\n{utils_content}\n</script>',
        )

    # The dashboard uses postMessage to request a highlighted, focused node.
    # Insert only once in case a stored artifact already contains this helper.
    if "edugraph:highlight-concept" not in content:
        content = content.replace("</body>", f"{IFRAME_HIGHLIGHT_SCRIPT}</body>")

    return HTMLResponse(content=content)


@router.get(
    "/{course_id}/gml",
    summary="Download or view raw GML (Graph Modeling Language) graph representation",
)
async def get_raw_gml(
    course_id: str,
    user: UserDocument = Depends(get_current_user),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc or not kg_doc.gml_content:
        raise HTTPException(
            status_code=404,
            detail="GML graph content not found for this course.",
        )

    return Response(
        content=kg_doc.gml_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="knowledge_graph_{course_id}.gml"'},
    )


@router.get(
    "/{course_id}/concept-neighborhood/{concept_name}",
    response_model=ConceptNeighborhoodResponse,
    summary="Get ego-network neighborhood (parents, prerequisites, dependents, evidence chunks) for a concept",
)
async def get_concept_neighborhood(
    course_id: str,
    concept_name: str,
    user: UserDocument = Depends(get_current_user),
):
    kg_doc = await KnowledgeGraphDocument.find_one(
        KnowledgeGraphDocument.course_id == course_id
    )
    if not kg_doc:
        raise HTTPException(status_code=404, detail="Knowledge graph not found.")

    node_type = "fine_grained_concept"
    for n in kg_doc.nodes:
        if n.get("id") == concept_name:
            node_type = n.get("type", "fine_grained_concept")
            break

    parents = []
    prerequisites = []
    dependents = []

    for edge in kg_doc.edges:
        src = edge.get("source")
        tgt = edge.get("target")
        rel = edge.get("relation")

        if rel == "CONTAINS" and tgt == concept_name:
            parents.append(src)
        elif rel == "PREREQUISITE_FOR":
            if tgt == concept_name:
                prerequisites.append(src)
            elif src == concept_name:
                dependents.append(tgt)

    # Fetch evidence chunks
    evidence_chunks = []
    mapping_doc = await ConceptChunkMappingDocument.find_one(
        ConceptChunkMappingDocument.course_id == course_id,
        ConceptChunkMappingDocument.concept_name == concept_name,
    )

    if mapping_doc and mapping_doc.qualifying_chunks:
        chunk_ids = [q["chunk_id"] for q in mapping_doc.qualifying_chunks[:5]]
        chunks = await ContentChunkDocument.find(
            ContentChunkDocument.course_id == course_id,
            {"chunk_id": {"$in": chunk_ids}},
        ).to_list()
        chunk_map = {c.chunk_id: c.text for c in chunks}

        for q in mapping_doc.qualifying_chunks[:5]:
            cid = q["chunk_id"]
            evidence_chunks.append({
                "chunk_id": cid,
                "similarity": q.get("similarity", 0.6),
                "text": chunk_map.get(cid, "")[:500],
            })

    return ConceptNeighborhoodResponse(
        concept=concept_name,
        node_type=node_type,
        parents=parents,
        prerequisites=prerequisites,
        dependents=dependents,
        evidence_chunks=evidence_chunks,
    )
