import React, { useState, useEffect, useMemo } from 'react';
import { 
  GitMerge, 
  Search, 
  Share2, 
  FileText, 
  BookOpen, 
  ArrowRight, 
  Sparkles, 
  Percent, 
  Layers, 
  ExternalLink,
  Copy,
  CheckCircle2,
  Filter,
  BarChart2
} from 'lucide-react';
import { 
  loadConceptChunkMap, 
  loadConceptChunkScores, 
  loadContentChunks, 
  buildChunkToConceptsMap 
} from '../../services/dataService';

export default function ConceptChunkMapView({ initialConcept }) {
  const [conceptMap, setConceptMap] = useState({});
  const [scoresMap, setScoresMap] = useState({});
  const [chunksData, setChunksData] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selectedConcept, setSelectedConcept] = useState(initialConcept || 'Abstract Syntax Tree');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [viewMode, setViewMode] = useState('concept-to-chunks'); // 'concept-to-chunks' | 'chunk-to-concepts'
  const [selectedChunkId, setSelectedChunkId] = useState('Compiler_book_p117_c0');

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      const [map, scores, chunks] = await Promise.all([
        loadConceptChunkMap(),
        loadConceptChunkScores(),
        loadContentChunks(),
      ]);
      setConceptMap(map || {});
      setScoresMap(scores || {});
      setChunksData(chunks || []);

      const conceptsKeys = Object.keys(map || {});
      if (conceptsKeys.length > 0 && !initialConcept) {
        setSelectedConcept(conceptsKeys[0]);
      }
      setLoading(false);
    }
    fetchData();
  }, [initialConcept]);

  // Index chunks by chunk_id for fast excerpt lookup
  const chunksById = useMemo(() => {
    const map = {};
    (chunksData || []).forEach(c => {
      map[c.chunk_id] = c;
    });
    return map;
  }, [chunksData]);

  // Reverse mapping: chunk_id -> concepts
  const chunkToConcepts = useMemo(() => {
    return buildChunkToConceptsMap(conceptMap);
  }, [conceptMap]);

  // Concepts list with search
  const conceptsList = useMemo(() => {
    const keys = Object.keys(conceptMap);
    if (!searchQuery.trim()) return keys;
    const q = searchQuery.toLowerCase();
    return keys.filter(k => k.toLowerCase().includes(q));
  }, [conceptMap, searchQuery]);

  // Chunks list with search (for reverse lookup mode)
  const chunksList = useMemo(() => {
    const keys = Object.keys(chunkToConcepts);
    if (!searchQuery.trim()) return keys;
    const q = searchQuery.toLowerCase();
    return keys.filter(k => k.toLowerCase().includes(q) || (chunksById[k]?.text && chunksById[k].text.toLowerCase().includes(q)));
  }, [chunkToConcepts, chunksById, searchQuery]);

  // Active concept details
  const activeChunks = useMemo(() => {
    if (!selectedConcept) return [];
    const chunkIds = conceptMap[selectedConcept] || [];
    const scoreItems = scoresMap[selectedConcept] || [];
    
    // Create score dictionary
    const scoreDict = {};
    scoreItems.forEach(item => {
      scoreDict[item.chunk_id] = item.similarity;
    });

    return chunkIds.map(chunkId => {
      const chunkMeta = chunksById[chunkId];
      const similarity = scoreDict[chunkId] !== undefined ? scoreDict[chunkId] : null;
      return {
        chunkId,
        pageNumber: chunkMeta?.page_number,
        bookName: chunkMeta?.book_name,
        text: chunkMeta?.text,
        similarity,
      };
    }).sort((a, b) => (b.similarity || 0) - (a.similarity || 0));
  }, [selectedConcept, conceptMap, scoresMap, chunksById]);

  // Active chunk details (for reverse lookup)
  const activeConceptsForChunk = useMemo(() => {
    if (!selectedChunkId) return [];
    return chunkToConcepts[selectedChunkId] || [];
  }, [selectedChunkId, chunkToConcepts]);

  const handleCopy = (text) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Stats
  const totalConceptsCount = Object.keys(conceptMap).length;
  const totalMappingsCount = Object.values(conceptMap).reduce((acc, curr) => acc + (curr?.length || 0), 0);

  return (
    <div className="json-view-container animate-fade-in">
      {/* Section Header */}
      <div className="section-title-bar glass-panel">
        <div className="title-left">
          <div className="title-icon-pill bg-cyan-glow">
            <GitMerge size={22} className="text-cyan" />
          </div>
          <div>
            <h2>Concept Chunk Map</h2>
            <p>Interactive mapping between canonical concepts and source content chunks (<code className="code-tag">concept_chunk_map.json</code> & <code className="code-tag">concept_chunk_scores.json</code>)</p>
          </div>
        </div>

        <div className="title-stats-pills">
          <div className="stat-pill">
            <span className="stat-pill-label">Total Concepts</span>
            <strong className="stat-pill-val">{totalConceptsCount}</strong>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-label">Total Linkages</span>
            <strong className="stat-pill-val">{totalMappingsCount.toLocaleString()}</strong>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-label">Avg Chunks / Concept</span>
            <strong className="stat-pill-val">
              {totalConceptsCount ? (totalMappingsCount / totalConceptsCount).toFixed(1) : 0}
            </strong>
          </div>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="map-mode-selector-bar">
        <div className="mode-toggle-group">
          <button 
            type="button" 
            className={`mode-btn ${viewMode === 'concept-to-chunks' ? 'active' : ''}`}
            onClick={() => { setViewMode('concept-to-chunks'); setSearchQuery(''); }}
          >
            <Share2 size={16} />
            <span>Concept ➔ Chunks Explorer</span>
          </button>
          <button 
            type="button" 
            className={`mode-btn ${viewMode === 'chunk-to-concepts' ? 'active' : ''}`}
            onClick={() => { setViewMode('chunk-to-concepts'); setSearchQuery(''); }}
          >
            <FileText size={16} />
            <span>Chunk ➔ Concepts (Reverse Lookup)</span>
          </button>
        </div>
      </div>

      {/* Main Two-Panel Layout */}
      {loading ? (
        <div className="loading-state-box glass-panel">
          <div className="spinner-border large-spinner"></div>
          <h4>Loading Concept-Chunk Mapping Matrix...</h4>
          <p>Cross-referencing entity links and semantic similarity scores</p>
        </div>
      ) : (
        <div className="mapping-split-layout">
          {/* Left Panel: Searchable List */}
          <div className="mapping-sidebar-panel glass-panel">
            <div className="sidebar-search-header">
              <div className="search-box-mini">
                <Search size={15} className="text-muted" />
                <input 
                  type="text" 
                  placeholder={viewMode === 'concept-to-chunks' ? "Search 150+ concepts..." : "Search chunk IDs..."}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <span className="items-count-text">
                {viewMode === 'concept-to-chunks' 
                  ? `${conceptsList.length} Concepts` 
                  : `${chunksList.length} Chunks`}
              </span>
            </div>

            <div className="mapping-items-scroll">
              {viewMode === 'concept-to-chunks' ? (
                conceptsList.map((con) => {
                  const chunkCount = conceptMap[con]?.length || 0;
                  const isSelected = selectedConcept === con;
                  return (
                    <button
                      key={con}
                      type="button"
                      className={`concept-list-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => setSelectedConcept(con)}
                    >
                      <span className="item-name">{con}</span>
                      <span className="item-badge">{chunkCount}</span>
                    </button>
                  );
                })
              ) : (
                chunksList.map((chkId) => {
                  const conceptsCount = chunkToConcepts[chkId]?.length || 0;
                  const isSelected = selectedChunkId === chkId;
                  const meta = chunksById[chkId];
                  return (
                    <button
                      key={chkId}
                      type="button"
                      className={`concept-list-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => setSelectedChunkId(chkId)}
                    >
                      <div className="chunk-list-info">
                        <span className="item-name font-mono">{chkId}</span>
                        {meta && <span className="item-sub">Page {meta.page_number}</span>}
                      </div>
                      <span className="item-badge cyan">{conceptsCount}</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Panel: Content Chunks details or reverse concept list */}
          <div className="mapping-detail-panel glass-panel">
            {viewMode === 'concept-to-chunks' ? (
              <div className="concept-mapping-content">
                <div className="detail-header-card">
                  <div className="header-meta-group">
                    <span className="badge-tag-cyan">Active Concept</span>
                    <h2>{selectedConcept}</h2>
                    <p>
                      Mapped to <strong>{activeChunks.length}</strong> content {activeChunks.length === 1 ? 'chunk' : 'chunks'} in the curriculum textbook.
                    </p>
                  </div>
                </div>

                <div className="mapped-chunks-cards-list">
                  {activeChunks.length === 0 ? (
                    <div className="empty-sub-state">
                      <p>No chunks directly linked to this concept.</p>
                    </div>
                  ) : (
                    activeChunks.map((item, idx) => (
                      <div key={item.chunkId} className="mapped-chunk-card glass-panel glow-hover">
                        <div className="chunk-card-topbar">
                          <div className="chunk-id-group">
                            <span className="rank-num">#{idx + 1}</span>
                            <code className="chunk-id-code">{item.chunkId}</code>
                            <button 
                              type="button" 
                              className="copy-mini-btn"
                              onClick={() => handleCopy(item.chunkId)}
                              title="Copy ID"
                            >
                              {copiedId === item.chunkId ? <CheckCircle2 size={13} className="text-emerald" /> : <Copy size={13} />}
                            </button>
                          </div>

                          <div className="similarity-meta-row">
                            {item.similarity !== null && (
                              <div className="score-container" title={`Similarity: ${(item.similarity * 100).toFixed(1)}%`}>
                                <span className="score-label">Similarity:</span>
                                <div className="score-mini-bar">
                                  <div 
                                    className="score-mini-fill" 
                                    style={{ width: `${Math.min(item.similarity * 100, 100)}%` }}
                                  ></div>
                                </div>
                                <span className="score-pct-text">{(item.similarity * 100).toFixed(1)}%</span>
                              </div>
                            )}
                            {item.pageNumber && (
                              <span className="page-meta-badge">Page {item.pageNumber}</span>
                            )}
                          </div>
                        </div>

                        <div className="chunk-card-body">
                          {item.text ? (
                            <p className="chunk-excerpt-text">"{item.text}"</p>
                          ) : (
                            <p className="chunk-missing-text">Chunk text index reference: {item.chunkId}</p>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              /* Reverse Lookup Mode */
              <div className="reverse-lookup-content">
                <div className="detail-header-card">
                  <div className="header-meta-group">
                    <span className="badge-tag-indigo">Content Chunk Reference</span>
                    <h2 className="font-mono">{selectedChunkId}</h2>
                    {chunksById[selectedChunkId] && (
                      <p>
                        Book: <strong>{chunksById[selectedChunkId].book_name}</strong> • Page: <strong>{chunksById[selectedChunkId].page_number}</strong>
                      </p>
                    )}
                  </div>
                </div>

                {chunksById[selectedChunkId]?.text && (
                  <div className="chunk-full-excerpt-box glass-panel">
                    <h4>Chunk Text Content:</h4>
                    <p>"{chunksById[selectedChunkId].text}"</p>
                  </div>
                )}

                <div className="reverse-concepts-section">
                  <h3>
                    <Share2 size={16} className="text-indigo" />
                    <span>Concepts Discussed in this Chunk ({activeConceptsForChunk.length})</span>
                  </h3>

                  <div className="reverse-concepts-grid">
                    {activeConceptsForChunk.length === 0 ? (
                      <p className="text-muted">No canonical concepts linked to this specific chunk.</p>
                    ) : (
                      activeConceptsForChunk.map((cName, i) => (
                        <div 
                          key={i} 
                          className="reverse-concept-card glass-panel"
                          onClick={() => {
                            setSelectedConcept(cName);
                            setViewMode('concept-to-chunks');
                          }}
                        >
                          <span className="c-name">{cName}</span>
                          <span className="jump-hint">
                            <span>Inspect</span>
                            <ArrowRight size={13} />
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
