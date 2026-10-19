/**
 * Service to load and cache extracted JSON data from backend outputs:
 * - content_chunks.json
 * - mapped_concepts.json
 * - concept_chunk_map.json
 * - concept_chunk_scores.json
 * - cleaned_enriched_concepts.json
 */

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
