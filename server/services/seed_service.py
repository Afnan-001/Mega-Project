"""
server/services/seed_service.py — Automatic database seeding for precomputed Knowledge Graph data.
Seeds pre-existing Compiler Design graph from Main/outputs/data if the database is unpopulated.
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
import networkx as nx

from server.config import settings
from server.models.course import CourseDocument, CourseEnrollmentDocument
from server.models.knowledge import EnrichedConceptDocument, KnowledgeGraphDocument
from server.models.user import UserDocument

logger = logging.getLogger("server.seed_service")


async def seed_initial_data_if_empty() -> None:
    """Check if MongoDB has an active knowledge graph. If empty, seed from precomputed data."""
    try:
        existing_kg = await KnowledgeGraphDocument.find_one()
        if existing_kg:
            logger.info("Knowledge Graph already exists in database (course_id=%s). Skipping seed.", existing_kg.course_id)
            return

        gml_file = settings.PROJECT_ROOT / "outputs" / "graph_model" / "knowledge_graph.gml"
        dag_file = settings.MAIN_DIR / "outputs" / "data" / "enriched_concepts_dag.json"
        html_file = settings.PROJECT_ROOT / "outputs" / "graph_model" / "knowledge_graph.html"
        data_dir = settings.MAIN_DIR / "outputs" / "data"

        if not gml_file.exists() and not dag_file.exists():
            logger.info("No precomputed knowledge graph files found on disk. Skipping seed.")
            return

        logger.info("Seeding precomputed Knowledge Graph from disk into database...")

        # 1. Find teacher or default
        teacher = await UserDocument.find_one(UserDocument.role == "teacher")
        teacher_id = str(teacher.id) if teacher else "system_seed"

        # 2. Find or create Course
        course = await CourseDocument.find_one(CourseDocument.uploaded_pdf_name == "Compiler_book.pdf")
        if not course:
            course = CourseDocument(
                title="CS-401: Compiler Design & Construction",
                description="Automated Knowledge Graph extracted from Compiler_book.pdf with 147 concepts and prerequisite DAG.",
                teacher_id=teacher_id,
                uploaded_pdf_name="Compiler_book.pdf",
                pdf_storage_path=str(settings.BOOKS_DIR / "Compiler_book.pdf"),
                status="ready",
                created_at=datetime.now(timezone.utc),
            )
            await course.insert()
        else:
            course.status = "ready"
            await course.save()

        course_id_str = str(course.id)

        # 3. Create course output directory and copy files
        course_out_dir = settings.COURSE_OUTPUTS_DIR / course_id_str
        course_out_dir.mkdir(parents=True, exist_ok=True)

        if data_dir.exists():
            for src_file in data_dir.glob("*.json"):
                shutil.copy2(src_file, course_out_dir / src_file.name)
        if html_file.exists():
            shutil.copy2(html_file, course_out_dir / "knowledge_graph.html")
        if gml_file.exists():
            shutil.copy2(gml_file, course_out_dir / "knowledge_graph.gml")

        # 4. Parse nodes and edges from GML
        vis_nodes = []
        vis_edges = []
        gml_text = ""

        if gml_file.exists():
            with open(gml_file, "r", encoding="utf-8") as f:
                gml_text = f.read()
            try:
                G = nx.read_gml(gml_file)
                for node_id, data in G.nodes(data=True):
                    vis_nodes.append({
                        "id": str(data.get("label", node_id)),
                        "label": str(data.get("label", node_id)),
                        "type": str(data.get("type", "fine_grained_concept")),
                    })
                for u, v, data in G.edges(data=True):
                    vis_edges.append({
                        "source": str(G.nodes[u].get("label", u)),
                        "target": str(G.nodes[v].get("label", v)),
                        "relation": str(data.get("relation", "PREREQUISITE_FOR")),
                        "confidence": float(data.get("weight", 0.85)),
                        "evidence_chunk": str(data.get("evidence_chunk", "")),
                        "evidence_text": str(data.get("evidence_text", "")),
                    })
            except Exception as e:
                logger.warning("Failed parsing GML with networkx: %s", e)

        # 5. Insert KnowledgeGraphDocument
        kg_doc = KnowledgeGraphDocument(
            course_id=course_id_str,
            nodes=vis_nodes,
            edges=vis_edges,
            gml_content=gml_text,
            total_nodes=len(vis_nodes),
            total_edges=len(vis_edges),
            updated_at=datetime.now(timezone.utc),
        )
        await kg_doc.insert()

        # 6. Insert EnrichedConceptDocuments if available
        if dag_file.exists():
            with open(dag_file, "r", encoding="utf-8") as f:
                dag_data = json.load(f)
            if isinstance(dag_data, list):
                for item in dag_data:
                    c_doc = EnrichedConceptDocument(
                        course_id=course_id_str,
                        concept=item.get("concept", ""),
                        node_type=item.get("node_type", "fine_grained_concept"),
                        coarse_grained_category=item.get("coarse_grained_category", []),
                        parent_concept=item.get("parent_concept", []),
                        prerequisites=item.get("prerequisites", []),
                        category_edge=item.get("category_edge"),
                        prerequisite_edges=item.get("prerequisite_edges", []),
                    )
                    await c_doc.insert()

        # 7. Auto-enroll existing students in this course
        students = await UserDocument.find(UserDocument.role == "student").to_list()
        for s in students:
            enr = CourseEnrollmentDocument(
                course_id=course_id_str,
                student_id=str(s.id),
                enrolled_at=datetime.now(timezone.utc),
            )
            await enr.insert()

        logger.info(
            "Successfully seeded Course '%s' (ID: %s) with %d nodes, %d edges, and enrolled %d students.",
            course.title,
            course_id_str,
            len(vis_nodes),
            len(vis_edges),
            len(students),
        )
    except Exception as e:
        logger.error("Error during initial knowledge graph seeding: %s", e, exc_info=True)
