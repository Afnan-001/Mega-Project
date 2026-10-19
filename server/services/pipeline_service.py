"""
server/services/pipeline_service.py — Orchestrates the AutoHKG pipeline non-destructively.
Calls existing modules in Main/ without modifying any original code.
Persists intermediate and final artifacts to both MongoDB (via Beanie) and per-course filesystem folders.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
from bson import ObjectId
from langchain_text_splitters import RecursiveCharacterTextSplitter

from server.config import settings
from server.models.course import CourseDocument, PipelineTaskDocument
from server.models.knowledge import (
    ConceptChunkMappingDocument,
    ConceptDocument,
    ContentChunkDocument,
    EnrichedConceptDocument,
    KnowledgeGraphDocument,
)

logger = logging.getLogger("server.services.pipeline")

# Ensure Main and Main/AutoHKG are discoverable in sys.path
MAIN_DIR = Path(settings.MAIN_DIR).resolve()
AUTOHKG_DIR = MAIN_DIR / "AutoHKG"

for p in [str(MAIN_DIR), str(AUTOHKG_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


class PipelineService:
    """Non-destructive orchestrator executing the 7-stage AutoHKG knowledge graph pipeline."""

    async def _append_log(self, task: PipelineTaskDocument, message: str) -> None:
        """Helper to append timestamped log and persist."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        task.logs.append(entry)
        logger.info("[Task %s] %s", str(task.id), message)
        await task.save()

    async def _update_stage(
        self,
        task: PipelineTaskDocument,
        stage: str,
        progress: int,
        detail_key: str | None = None,
        detail_val: Any | None = None,
    ) -> None:
        """Update stage and progress percentage in task document."""
        task.current_stage = stage
        task.progress_percentage = progress
        if detail_key and detail_val is not None:
            task.stage_details[detail_key] = str(detail_val)
        await task.save()

    async def run_full_pipeline(self, course_id_str: str, task_id_str: str) -> None:
        """
        Main background entrypoint for running the 7 pipeline stages.
        """
        course = await CourseDocument.get(ObjectId(course_id_str))
        task = await PipelineTaskDocument.get(ObjectId(task_id_str))

        if not course or not task:
            logger.error("Course or Task not found for ID: course=%s, task=%s", course_id_str, task_id_str)
            return

        # Prepare course output workspace directory
        course_out_dir = settings.COURSE_OUTPUTS_DIR / course_id_str
        course_out_dir.mkdir(parents=True, exist_ok=True)

        task.status = "running"
        await self._append_log(task, f"Started AutoHKG pipeline for course '{course.title}'")

        try:
            pdf_path = Path(course.pdf_storage_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF source file does not exist: {pdf_path}")

            # ─────────────────────────────────────────────────────────────
            # STAGE 1: Text Extraction & Recursive Chunking
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "CHUNKING", 10)
            await self._append_log(task, f"Stage 1/7: Extracting text from PDF: {pdf_path.name}")

            from AutoHKG.extract_and_chunk import extract_text_from_pdf

            pages_data = await asyncio.to_thread(extract_text_from_pdf, pdf_path)
            if not pages_data:
                raise ValueError("PDF extraction produced 0 text pages.")

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            all_chunks = []
            chunk_records = []

            for page in pages_data:
                splits = splitter.split_text(page["text"])
                for idx, text in enumerate(splits):
                    cid = f"{pdf_path.stem}_p{page['page_number']}_c{idx}"
                    rec = {
                        "chunk_id": cid,
                        "book_name": pdf_path.name,
                        "page_number": page["page_number"],
                        "text": text,
                    }
                    all_chunks.append(rec)
                    chunk_records.append(
                        ContentChunkDocument(
                            course_id=course_id_str,
                            chunk_id=cid,
                            page_number=page["page_number"],
                            book_name=pdf_path.name,
                            text=text,
                        )
                    )

            # Persist chunks to course folder and MongoDB
            chunks_json_path = course_out_dir / "content_chunks.json"
            with open(chunks_json_path, "w", encoding="utf-8") as f:
                json.dump(all_chunks, f, indent=2, ensure_ascii=False)

            # Delete any existing chunks for this course to avoid duplicates
            await ContentChunkDocument.find(ContentChunkDocument.course_id == course_id_str).delete()
            if chunk_records:
                await ContentChunkDocument.insert_many(chunk_records)

            elapsed_1 = time.time() - t0
            await self._update_stage(task, "CHUNKING", 15, "stage_1_chunks", len(all_chunks))
            await self._append_log(
                task, f"Stage 1 Completed: Generated {len(all_chunks)} chunks across {len(pages_data)} pages ({elapsed_1:.1f}s)"
            )

            # ─────────────────────────────────────────────────────────────
            # STAGE 2: Multi-Signal Statistical NLP Concept Extraction
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "NLP_CONCEPTS", 25)
            await self._append_log(task, "Stage 2/7: Extracting candidate concepts via NLP pipeline...")

            from AutoHKG.extract_concepts import extract_concepts_nlp

            raw_concepts_path = course_out_dir / "concepts.json"
            raw_concept_names = await asyncio.to_thread(
                extract_concepts_nlp,
                input_file=chunks_json_path,
                output_file=raw_concepts_path,
                top_k=800,
                min_score=2.5,
            )

            # Save to MongoDB
            await ConceptDocument.find(
                ConceptDocument.course_id == course_id_str,
                ConceptDocument.node_type == "raw_candidate",
            ).delete()

            raw_concept_docs = [
                ConceptDocument(
                    course_id=course_id_str,
                    concept_name=name,
                    canonical_name=None,
                    node_type="raw_candidate",
                    is_grounded=False,
                )
                for name in raw_concept_names
            ]
            if raw_concept_docs:
                await ConceptDocument.insert_many(raw_concept_docs)

            elapsed_2 = time.time() - t0
            await self._update_stage(task, "NLP_CONCEPTS", 35, "stage_2_raw_concepts", len(raw_concept_names))
            await self._append_log(
                task, f"Stage 2 Completed: Extracted {len(raw_concept_names)} raw candidate concepts ({elapsed_2:.1f}s)"
            )

            # ─────────────────────────────────────────────────────────────
            # STAGE 3: LLM Concept Cleaning & Canonicalization
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "LLM_CLEANING", 45)
            await self._append_log(task, "Stage 3/7: Canonicalizing and cleaning concepts with LLM...")

            from AutoHKG.clean_concepts import clean_concepts_batch
            from llm import LLM

            clean_concepts_path = course_out_dir / "clean_concepts.json"
            cleaned_concept_names: list[str] = []

            try:
                llm = LLM(
                    sys_msg="You are an expert AI editor specialized in technical terminology refinement.",
                    temperature=0.0,
                )
                # Clean in batches
                batch_size = 50
                cleaned_set = set()
                for i in range(0, min(len(raw_concept_names), 300), batch_size):
                    batch = raw_concept_names[i : i + batch_size]
                    batch_cleaned = await asyncio.to_thread(clean_concepts_batch, llm, batch)
                    for term in batch_cleaned:
                        cleaned_set.add(term)
                cleaned_concept_names = sorted(list(cleaned_set), key=lambda s: s.lower())
            except Exception as llm_err:
                logger.warning("LLM cleaning encountered error (%s); falling back to heuristic title-casing", llm_err)
                await self._append_log(task, f"Notice: Using heuristic canonicalization: {llm_err}")
                # Fallback heuristic cleaning
                cleaned_set = set()
                for r in raw_concept_names:
                    cleaned_term = " ".join(w.capitalize() for w in r.strip().split())
                    if len(cleaned_term) > 2:
                        cleaned_set.add(cleaned_term)
                cleaned_concept_names = sorted(list(cleaned_set), key=lambda s: s.lower())

            with open(clean_concepts_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_concept_names, f, indent=2, ensure_ascii=False)

            # Persist clean concepts to MongoDB
            clean_concept_docs = [
                ConceptDocument(
                    course_id=course_id_str,
                    concept_name=name,
                    canonical_name=name,
                    node_type="fine_grained_concept",
                    is_grounded=False,
                )
                for name in cleaned_concept_names
            ]
            if clean_concept_docs:
                await ConceptDocument.insert_many(clean_concept_docs)

            elapsed_3 = time.time() - t0
            await self._update_stage(task, "LLM_CLEANING", 50, "stage_3_clean_concepts", len(cleaned_concept_names))
            await self._append_log(
                task, f"Stage 3 Completed: Standardized {len(cleaned_concept_names)} clean canonical concepts ({elapsed_3:.1f}s)"
            )

            # ─────────────────────────────────────────────────────────────
            # STAGE 4: Dense Vector Chunk Embeddings
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "EMBEDDING", 60)
            await self._append_log(task, f"Stage 4/7: Generating dense embeddings for {len(all_chunks)} chunks...")

            from AutoHKG.embed_chunks import get_embeddings_local

            chunk_texts = [c["text"] for c in all_chunks]
            embeddings_npy_path = course_out_dir / "chunk_embeddings.npy"

            chunk_embeddings = await asyncio.to_thread(get_embeddings_local, chunk_texts)
            np.save(embeddings_npy_path, chunk_embeddings)

            # Update MongoDB documents with embedding vectors (optional or chunk-indexed)
            for i, chunk_doc in enumerate(chunk_records):
                if i < len(chunk_embeddings):
                    chunk_doc.embedding_vector = chunk_embeddings[i].tolist()
                    await chunk_doc.save()

            elapsed_4 = time.time() - t0
            await self._update_stage(task, "EMBEDDING", 70, "stage_4_embeddings_shape", str(chunk_embeddings.shape))
            await self._append_log(
                task, f"Stage 4 Completed: Embedded {len(all_chunks)} chunks, shape: {chunk_embeddings.shape} ({elapsed_4:.1f}s)"
            )

            # ─────────────────────────────────────────────────────────────
            # STAGE 5: Adaptive Knee/Elbow Cosine Mapping & Pruning
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "MAPPING", 75)
            await self._append_log(task, "Stage 5/7: Mapping concepts to chunks using adaptive knee/elbow thresholding...")

            from AutoHKG.map_concepts import map_and_prune_concepts

            mapping_res = await asyncio.to_thread(
                map_and_prune_concepts,
                concepts_file=clean_concepts_path,
                chunks_file=chunks_json_path,
                embeddings_file=embeddings_npy_path,
                min_rejection_similarity=0.55,
                max_chunks_cap=20,
            )
            concept_chunk_map, concept_chunk_scores, grounded_concepts = mapping_res

            # Save to course output directory
            with open(course_out_dir / "concept_chunk_map.json", "w", encoding="utf-8") as f:
                json.dump(concept_chunk_map, f, indent=2, ensure_ascii=False)
            with open(course_out_dir / "mapped_concepts.json", "w", encoding="utf-8") as f:
                json.dump({"concepts": grounded_concepts}, f, indent=2, ensure_ascii=False)

            # Save mappings in MongoDB
            await ConceptChunkMappingDocument.find(ConceptChunkMappingDocument.course_id == course_id_str).delete()
            mapping_docs = []
            for c_name, qualifying_cids in concept_chunk_map.items():
                scores = concept_chunk_scores.get(c_name, [])
                qualifying_chunks = [
                    {"chunk_id": cid, "similarity": float(scores[k]) if k < len(scores) else 0.6}
                    for k, cid in enumerate(qualifying_cids)
                ]
                mapping_docs.append(
                    ConceptChunkMappingDocument(
                        course_id=course_id_str,
                        concept_name=c_name,
                        qualifying_chunks=qualifying_chunks,
                        elbow_threshold=float(scores[-1]) if scores else 0.55,
                    )
                )

            if mapping_docs:
                await ConceptChunkMappingDocument.insert_many(mapping_docs)

            # Update grounded status in ConceptDocument
            for g_name in grounded_concepts:
                await ConceptDocument.find(
                    ConceptDocument.course_id == course_id_str,
                    ConceptDocument.concept_name == g_name,
                ).update({"$set": {"is_grounded": True}})

            elapsed_5 = time.time() - t0
            await self._update_stage(task, "MAPPING", 85, "stage_5_grounded_concepts", len(grounded_concepts))
            await self._append_log(
                task, f"Stage 5 Completed: Grounded {len(grounded_concepts)} concepts with verified evidence ({elapsed_5:.1f}s)"
            )

            # ─────────────────────────────────────────────────────────────
            # STAGE 6: Source-Grounded Hierarchy & Prerequisite Enrichment
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "ENRICHMENT", 88)
            await self._append_log(task, f"Stage 6/7: Enriching {len(grounded_concepts)} grounded concepts via LLM...")

            from AutoHKG.enrich_concepts import (
                build_chunk_lookup,
                enrich_concept,
            )

            chunk_lookup = build_chunk_lookup(all_chunks)
            all_concepts_set = set(grounded_concepts)
            enriched_records = []

            enrich_llm = None
            try:
                enrich_llm = LLM(
                    sys_msg=(
                        "You are a domain-agnostic educational Knowledge Graph expert. "
                        "You build source-grounded educational concept hierarchies using only the provided textbook chunks."
                    ),
                    temperature=0.0,
                )
            except Exception as e:
                logger.warning("Could not initialize LLM for enrichment: %s. Using heuristic enrichment.", e)

            for idx, c_name in enumerate(grounded_concepts):
                concept_obj = {"concept": c_name}
                if enrich_llm is not None:
                    try:
                        record = await asyncio.to_thread(
                            enrich_concept,
                            concept_obj=concept_obj,
                            all_concepts=grounded_concepts,
                            all_concepts_set=all_concepts_set,
                            concept_chunk_map=concept_chunk_map,
                            chunk_lookup=chunk_lookup,
                            llm=enrich_llm,
                        )
                    except Exception as e:
                        logger.warning("Enrichment failed for %s: %s", c_name, e)
                        record = None
                else:
                    record = None

                if not record:
                    # Heuristic fallback: create clean default entry
                    record = {
                        "concept": c_name,
                        "node_type": "fine_grained_concept",
                        "coarse_grained_category": [],
                        "parent_concept": [],
                        "category_edge": None,
                        "prerequisites": [],
                        "prerequisite_edges": [],
                    }
                enriched_records.append(record)

            enriched_json_path = course_out_dir / "enriched_concepts.json"
            with open(enriched_json_path, "w", encoding="utf-8") as f:
                json.dump(enriched_records, f, indent=2, ensure_ascii=False)

            # Store in MongoDB
            await EnrichedConceptDocument.find(EnrichedConceptDocument.course_id == course_id_str).delete()
            enriched_docs = [
                EnrichedConceptDocument(
                    course_id=course_id_str,
                    concept=r["concept"],
                    node_type=r.get("node_type", "fine_grained_concept"),
                    coarse_grained_category=r.get("coarse_grained_category", []),
                    parent_concept=r.get("parent_concept", []),
                    prerequisites=r.get("prerequisites", []),
                    category_edge=r.get("category_edge"),
                    prerequisite_edges=r.get("prerequisite_edges", []),
                )
                for r in enriched_records
            ]
            if enriched_docs:
                await EnrichedConceptDocument.insert_many(enriched_docs)

            elapsed_6 = time.time() - t0
            await self._update_stage(task, "ENRICHMENT", 93, "stage_6_enriched", len(enriched_records))
            await self._append_log(task, f"Stage 6 Completed: Enriched {len(enriched_records)} concepts ({elapsed_6:.1f}s)")

            # ─────────────────────────────────────────────────────────────
            # STAGE 7: DAG Resolution & Knowledge Graph Assembly
            # ─────────────────────────────────────────────────────────────
            t0 = time.time()
            await self._update_stage(task, "DAG_RESOLVE", 95)
            await self._append_log(task, "Stage 7/7: Resolving cycles, validating strict DAG, and assembling Graph...")

            from AutoHKG.post_process_dag import post_process_dag

            dag_json_path = course_out_dir / "enriched_concepts_dag.json"
            cleaned_enriched = await asyncio.to_thread(
                post_process_dag,
                input_file=enriched_json_path,
                output_file=dag_json_path,
                perform_transitive_reduction=True,
            )

            # Assemble NetworkX Graph & Vis.js format
            G = nx.DiGraph()
            vis_nodes: list[dict[str, Any]] = []
            vis_edges: list[dict[str, Any]] = []
            seen_nodes: set[str] = set()

            for item in cleaned_enriched:
                concept = item["concept"]
                if concept not in seen_nodes:
                    seen_nodes.add(concept)
                    vis_nodes.append({
                        "id": concept,
                        "label": concept,
                        "type": item.get("node_type", "fine_grained_concept"),
                    })
                    G.add_node(concept, label=concept, type=item.get("node_type", "fine_grained_concept"))

                # Add category contains edges
                for cat in item.get("coarse_grained_category", []):
                    if cat not in seen_nodes:
                        seen_nodes.add(cat)
                        vis_nodes.append({
                            "id": cat,
                            "label": cat,
                            "type": "coarse_grained_category",
                        })
                        G.add_node(cat, label=cat, type="coarse_grained_category")

                    cat_edge = item.get("category_edge") or {}
                    vis_edges.append({
                        "source": cat,
                        "target": concept,
                        "relation": "CONTAINS",
                        "confidence": cat_edge.get("confidence", 1.0),
                        "evidence_chunk": cat_edge.get("evidence_chunk"),
                        "evidence_text": cat_edge.get("evidence_text"),
                    })
                    G.add_edge(cat, concept, relation="CONTAINS", weight=cat_edge.get("confidence", 1.0))

                # Add prerequisite edges
                for edge in item.get("prerequisite_edges", []):
                    prereq = edge.get("prerequisite")
                    if prereq:
                        if prereq not in seen_nodes:
                            seen_nodes.add(prereq)
                            vis_nodes.append({
                                "id": prereq,
                                "label": prereq,
                                "type": "fine_grained_concept",
                            })
                            G.add_node(prereq, label=prereq, type="fine_grained_concept")

                        vis_edges.append({
                            "source": prereq,
                            "target": concept,
                            "relation": "PREREQUISITE_FOR",
                            "confidence": edge.get("confidence", 0.8),
                            "evidence_chunk": edge.get("evidence_chunk"),
                            "evidence_text": edge.get("evidence_text"),
                        })
                        G.add_edge(
                            prereq,
                            concept,
                            relation="PREREQUISITE_FOR",
                            weight=edge.get("confidence", 0.8),
                        )

            # Generate GML string
            gml_lines = list(nx.generate_gml(G))
            gml_str = "\n".join(gml_lines)
            gml_file_path = course_out_dir / "knowledge_graph.gml"
            with open(gml_file_path, "w", encoding="utf-8") as f:
                f.write(gml_str)

            # Persist KnowledgeGraphDocument in MongoDB
            kg_doc = await KnowledgeGraphDocument.find_one(
                KnowledgeGraphDocument.course_id == course_id_str
            )
            if not kg_doc:
                kg_doc = KnowledgeGraphDocument(
                    course_id=course_id_str,
                    nodes=vis_nodes,
                    edges=vis_edges,
                    gml_content=gml_str,
                    total_nodes=len(vis_nodes),
                    total_edges=len(vis_edges),
                    updated_at=datetime.now(timezone.utc),
                )
                await kg_doc.insert()
            else:
                kg_doc.nodes = vis_nodes
                kg_doc.edges = vis_edges
                kg_doc.gml_content = gml_str
                kg_doc.total_nodes = len(vis_nodes)
                kg_doc.total_edges = len(vis_edges)
                kg_doc.updated_at = datetime.now(timezone.utc)
                await kg_doc.save()

            elapsed_7 = time.time() - t0
            await self._update_stage(
                task,
                "COMPLETED",
                100,
                "stage_7_graph",
                f"{len(vis_nodes)} nodes, {len(vis_edges)} edges",
            )
            await self._append_log(
                task,
                f"Stage 7 Completed: Knowledge Graph finalized with {len(vis_nodes)} nodes and {len(vis_edges)} edges ({elapsed_7:.1f}s)",
            )

            # Mark course as ready and task as completed
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            await task.save()

            course.status = "ready"
            course.active_task_id = None
            await course.save()

            await self._append_log(task, "🎉 AutoHKG Pipeline completed successfully!")

        except Exception as err:
            tb = traceback.format_exc()
            logger.error("Pipeline task %s failed: %s\n%s", task_id_str, err, tb)
            task.status = "failed"
            task.error_message = f"{type(err).__name__}: {str(err)}"
            task.completed_at = datetime.now(timezone.utc)
            await self._append_log(task, f"❌ Pipeline failed: {err}")
            await task.save()

            course.status = "error"
            await course.save()


# Singleton pipeline service instance
pipeline_service = PipelineService()
