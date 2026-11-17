/**
 * Service to load and cache extracted JSON data from backend outputs:
 * - content_chunks.json
 * - mapped_concepts.json
 * - concept_chunk_map.json
 * - concept_chunk_scores.json
 * - cleaned_enriched_concepts.json
 */
import { teacherApi } from './api';

let cachedData = {
  contentChunks: null,
  mappedConcepts: null,
  conceptChunkMap: null,
  conceptChunkScores: null,
  enrichedConcepts: null,
};

export async function loadContentChunks() {
  if (cachedData.contentChunks) return cachedData.contentChunks;
  try {
    const res = await fetch('/data/content_chunks.json');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    cachedData.contentChunks = data;
    return data;
  } catch (err) {
    console.error('Failed to load content_chunks.json', err);
    return [];
  }
}

export async function loadMappedConcepts() {
  if (cachedData.mappedConcepts) return cachedData.mappedConcepts;
  try {
    const res = await fetch('/data/mapped_concepts.json');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    const conceptsList = data.concepts || (Array.isArray(data) ? data : []);
    cachedData.mappedConcepts = conceptsList;
    return conceptsList;
  } catch (err) {
    console.error('Failed to load mapped_concepts.json', err);
    return [];
  }
}

export async function loadConceptChunkMap() {
  if (cachedData.conceptChunkMap) return cachedData.conceptChunkMap;
  try {
    const res = await fetch('/data/concept_chunk_map.json');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    cachedData.conceptChunkMap = data;
    return data;
  } catch (err) {
    console.error('Failed to load concept_chunk_map.json', err);
    return {};
  }
}

export async function loadConceptChunkScores() {
  if (cachedData.conceptChunkScores) return cachedData.conceptChunkScores;
  try {
    const res = await fetch('/data/concept_chunk_scores.json');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    cachedData.conceptChunkScores = data;
    return data;
  } catch (err) {
    console.error('Failed to load concept_chunk_scores.json', err);
    return {};
  }
}

export async function loadEnrichedConcepts() {
  if (cachedData.enrichedConcepts) return cachedData.enrichedConcepts;
  try {
    const res = await fetch('/data/cleaned_enriched_concepts.json');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    cachedData.enrichedConcepts = data;
    return data;
  } catch (err) {
    console.error('Failed to load cleaned_enriched_concepts.json', err);
    return [];
  }
}

// ==========================================
// API-based course-aware loaders (FE-12)
// ==========================================

/**
 * Fetch content chunks for a specific course.
 * No direct chunks endpoint exists on the API, so falls back to static.
 */
export async function loadContentChunksForCourse(courseId) {
  if (!courseId) return loadContentChunks();
  // No chunks API endpoint: fall back to static
  return loadContentChunks();
}

/**
 * Fetch mapped concepts for a specific course from the knowledge-graph API.
 * Falls back to static loadMappedConcepts() on error or missing courseId.
 */
export async function loadMappedConceptsForCourse(courseId) {
  if (!courseId) return loadMappedConcepts();
  try {
    const graph = await teacherApi.getKnowledgeGraph(courseId);
    const nodes = graph.nodes || [];
    const conceptNodes = nodes.filter((n) => n.type === 'fine_grained_concept');
    if (conceptNodes.length === 0) {
      // Try all nodes if no fine_grained_concept typed nodes exist
      const allNames = nodes.map((n) => n.label || n.id).filter(Boolean);
      if (allNames.length > 0) return allNames;
      return loadMappedConcepts();
    }
    return conceptNodes.map((n) => n.label || n.id).filter(Boolean);
  } catch (err) {
    console.warn(`loadMappedConceptsForCourse(${courseId}) fell back to static:`, err.message);
    return loadMappedConcepts();
  }
}

/**
 * Fetch concept-chunk map for a specific course.
 * No direct API endpoint, falls back to static.
 */
export async function loadConceptChunkMapForCourse(courseId) {
  if (!courseId) return loadConceptChunkMap();
  // No concept-chunk-map endpoint: fall back to static
  return loadConceptChunkMap();
}

/**
 * Helper to build reverse mapping: chunkId -> list of concepts
 */
export function buildChunkToConceptsMap(conceptChunkMap) {
  const chunkMap = {};
  for (const [concept, chunks] of Object.entries(conceptChunkMap || {})) {
    if (Array.isArray(chunks)) {
      chunks.forEach((chunkId) => {
        if (!chunkMap[chunkId]) {
          chunkMap[chunkId] = [];
        }
        chunkMap[chunkId].push(concept);
      });
    }
  }
  return chunkMap;
}
