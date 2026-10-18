import React, { useState, useEffect, useMemo } from 'react';
import { 
  Share2, 
  Search, 
  Filter, 
  Layers, 
  BookOpen, 
  CheckCircle2, 
  ExternalLink, 
  ChevronRight, 
  Sparkles,
  Link2,
  GitBranch,
  Copy,
  LayoutGrid,
  Columns,
  ChevronLeft,
  Info,
  Quote
} from 'lucide-react';
import { 
  loadMappedConcepts, 
  loadConceptChunkMap, 
  loadEnrichedConcepts,
  loadContentChunks
} from '../../services/dataService';

export default function MappedConceptsView({ onSelectConceptForMap }) {
  const [concepts, setConcepts] = useState([]);
  const [conceptMap, setConceptMap] = useState({});
  const [enrichedData, setEnrichedData] = useState([]);
  const [chunksData, setChunksData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters & State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedLetter, setSelectedLetter] = useState('ALL');
  const [selectedConcept, setSelectedConcept] = useState('Abstract Syntax Tree');
  const [viewMode, setViewMode] = useState('split'); // 'split' (zero-scroll split view) | 'grid' (paginated cards)
  const [currentPage, setCurrentPage] = useState(1);
  const [copiedId, setCopiedId] = useState(null);

  const PAGE_SIZE = 12;

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      const [mappedList, mapData, enrichedList, chunks] = await Promise.all([
        loadMappedConcepts(),
        loadConceptChunkMap(),
        loadEnrichedConcepts(),
        loadContentChunks()
      ]);
      setConcepts(mappedList || []);
      setConceptMap(mapData || {});
      setEnrichedData(enrichedList || []);
      setChunksData(chunks || []);

      if (mappedList && mappedList.length > 0) {
        setSelectedConcept(mappedList[0]);
      }
      setLoading(false);
    }
    fetchData();
  }, []);

  // Index chunks by chunk_id for quick preview
  const chunksById = useMemo(() => {
    const map = {};
    (chunksData || []).forEach(c => {
      map[c.chunk_id] = c;
    });
    return map;
  }, [chunksData]);

  // Map enriched concept metadata by concept name
  const enrichedMap = useMemo(() => {
    const map = {};
    (enrichedData || []).forEach(item => {
      if (item.concept) {
        map[item.concept.toLowerCase()] = item;
      }
    });
    return map;
  }, [enrichedData]);

  // Categories list
  const categoriesList = useMemo(() => {
    const catSet = new Set();
    Object.values(enrichedMap).forEach(item => {
      if (item.coarse_grained_category) {
        if (Array.isArray(item.coarse_grained_category)) {
          item.coarse_grained_category.forEach(c => catSet.add(c));
        } else {
          catSet.add(item.coarse_grained_category);
        }
      }
    });
    return ['all', ...Array.from(catSet)];
  }, [enrichedMap]);

  // Available Alphabet letters from concept names
  const alphabetLetters = useMemo(() => {
    const letters = new Set();
    concepts.forEach(c => {
      if (c && c.length > 0) {
        const first = c.charAt(0).toUpperCase();
        if (/[A-Z]/.test(first)) {
          letters.add(first);
        }
      }
    });
    return ['ALL', ...Array.from(letters).sort()];
  }, [concepts]);

  // Filtered concepts
  const filteredConcepts = useMemo(() => {
    let result = concepts;
    if (selectedLetter !== 'ALL') {
      result = result.filter(c => c.toUpperCase().startsWith(selectedLetter));
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(c => c.toLowerCase().includes(q));
    }
    if (selectedCategory !== 'all') {
      result = result.filter(c => {
        const enriched = enrichedMap[c.toLowerCase()];
        if (!enriched) return false;
        const cats = enriched.coarse_grained_category;
        return Array.isArray(cats) ? cats.includes(selectedCategory) : cats === selectedCategory;
      });
    }
    return result;
  }, [concepts, selectedLetter, searchQuery, selectedCategory, enrichedMap]);

  // Ensure an active selected concept exists within filtered list
  useEffect(() => {
    if (filteredConcepts.length > 0 && !filteredConcepts.includes(selectedConcept)) {
      setSelectedConcept(filteredConcepts[0]);
    }
  }, [filteredConcepts, selectedConcept]);

  // Paginated concepts for Grid View
  const totalPages = Math.ceil(filteredConcepts.length / PAGE_SIZE) || 1;
  const paginatedConcepts = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredConcepts.slice(start, start + PAGE_SIZE);
  }, [filteredConcepts, currentPage]);

  const activeEnriched = enrichedMap[selectedConcept?.toLowerCase()];
  const activeChunks = conceptMap[selectedConcept] || [];
  const activeCategories = activeEnriched?.coarse_grained_category || ['Compiler Design & Principles'];
  const activePrerequisites = activeEnriched?.prerequisites || [];

  const handleCopyChunkId = (id) => {
    navigator.clipboard?.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="json-view-container animate-fade-in">
      {/* Section Header */}
      <div className="section-title-bar glass-panel">
        <div className="title-left">
          <div className="title-icon-pill bg-purple-glow">
            <Share2 size={22} className="text-purple" />
          </div>
          <div>
            <h2>Mapped Curriculum Concepts</h2>
            <p>Canonical concepts extracted from course texts (<code className="code-tag">mapped_concepts.json</code> & <code className="code-tag">cleaned_enriched_concepts.json</code>)</p>
          </div>
        </div>

        <div className="title-stats-pills">
          <div className="stat-pill">
            <span className="stat-pill-label">Total Concepts</span>
            <strong className="stat-pill-val">{concepts.length}</strong>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-label">Categories</span>
            <strong className="stat-pill-val">{categoriesList.length > 1 ? categoriesList.length - 1 : 12}</strong>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-label">Filtered</span>
            <strong className="stat-pill-val">{filteredConcepts.length}</strong>
          </div>
        </div>
      </div>

      {/* Filter and Mode Bar */}
      <div className="concepts-control-bar glass-panel">
        <div className="control-bar-left">
          <div className="search-box-compact">
            <Search size={16} className="search-icon" />
            <input 
              type="text" 
              placeholder="Search concepts by keyword..." 
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
            />
            {searchQuery && (
              <button type="button" className="clear-search-btn" onClick={() => setSearchQuery('')}>
                ✕
              </button>
            )}
          </div>

          {categoriesList.length > 1 && (
            <div className="category-select-wrap">
              <Filter size={15} className="text-muted" />
              <select 
                value={selectedCategory} 
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setCurrentPage(1);
                }}
                className="custom-dropdown"
              >
                {categoriesList.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat === 'all' ? 'All Categories' : cat}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* View Mode Toggle: Split Inspector (No scrolling) vs Paginated Cards */}
        <div className="view-mode-toggles">
          <button 
            type="button" 
            className={`view-mode-btn ${viewMode === 'split' ? 'active' : ''}`}
            onClick={() => setViewMode('split')}
            title="Split Inspector View: Instant side-by-side inspection with zero page scrolling"
          >
            <Columns size={15} />
            <span>Split Inspector (Fast)</span>
          </button>
          <button 
            type="button" 
            className={`view-mode-btn ${viewMode === 'grid' ? 'active' : ''}`}
            onClick={() => setViewMode('grid')}
            title="Grid Cards View with pagination"
          >
            <LayoutGrid size={15} />
            <span>Cards Grid</span>
          </button>
        </div>
      </div>

      {/* Alphabet Quick-Jump Filter Bar */}
      <div className="alphabet-jump-bar glass-panel">
        <span className="jump-bar-label">Alphabetical Index:</span>
        <div className="alphabet-pills-row">
          {alphabetLetters.map((letter) => (
            <button
              key={letter}
              type="button"
              className={`letter-pill ${selectedLetter === letter ? 'active' : ''}`}
              onClick={() => {
                setSelectedLetter(letter);
                setCurrentPage(1);
              }}
            >
              {letter}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="loading-state-box glass-panel">
          <div className="spinner-border large-spinner"></div>
          <h4>Loading curriculum concepts...</h4>
          <p>Processing semantic nodes, categories, and chunk mappings</p>
        </div>
      ) : filteredConcepts.length === 0 ? (
        <div className="empty-state-box glass-panel">
          <Share2 size={42} className="text-muted" />
          <h4>No concepts match your filter</h4>
          <p>Try clearing search keywords or selecting another letter.</p>
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={() => { setSearchQuery(''); setSelectedCategory('all'); setSelectedLetter('ALL'); }}
          >
            Reset All Filters
          </button>
        </div>
      ) : viewMode === 'split' ? (
        /* ================= SPLIT INSPECTOR VIEW (ZERO-PAGE-SCROLLING) ================= */
        <div className="concept-split-container">
          {/* Left Concepts Navigation List */}
          <div className="concept-master-list glass-panel">
            <div className="master-list-header">
              <span className="master-count-badge">{filteredConcepts.length} Concepts</span>
              <span className="master-sub-hint">Click any concept to inspect</span>
            </div>

            <div className="master-scroll-list">
              {filteredConcepts.map((conName) => {
                const isSelected = selectedConcept === conName;
                const chunksCount = conceptMap[conName]?.length || 0;
                const enriched = enrichedMap[conName.toLowerCase()];
                const cat = Array.isArray(enriched?.coarse_grained_category) 
                  ? enriched?.coarse_grained_category[0] 
                  : (enriched?.coarse_grained_category || 'Compiler Theory');

                return (
                  <button
                    key={conName}
                    type="button"
                    className={`concept-master-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedConcept(conName)}
                  >
                    <div className="item-text-wrap">
                      <span className="item-concept-name">{conName}</span>
                      <span className="item-concept-cat">{cat}</span>
                    </div>
                    <span className="item-chunks-pill" title={`${chunksCount} content chunks mapped`}>
                      {chunksCount} {chunksCount === 1 ? 'chk' : 'chks'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Instant Concept Detail Inspector (No scrolling the page!) */}
          <div className="concept-detail-inspector glass-panel">
            {selectedConcept ? (
              <div className="inspector-content animate-fade-in">
                {/* Inspector Header */}
                <div className="inspector-top-card">
                  <div className="inspector-title-row">
                    <div>
                      <div className="concept-category-badge">
                        <span className="dot-purple"></span>
                        <span>
                          {Array.isArray(activeCategories) ? activeCategories.join(' • ') : activeCategories}
                        </span>
                      </div>
                      <h2 className="inspector-concept-title">{selectedConcept}</h2>
                    </div>

                    <div className="inspector-quick-actions">
                      {onSelectConceptForMap && (
                        <button 
                          type="button" 
                          className="btn-inspect-map"
                          onClick={() => onSelectConceptForMap(selectedConcept)}
                          title="Open concept and all excerpt passages in Concept Chunk Map"
                        >
                          <Share2 size={14} />
                          <span>View in Chunk Map</span>
                          <ExternalLink size={13} />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="inspector-metrics-bar">
                    <div className="metric-tag">
                      <Link2 size={13} className="text-indigo" />
                      <span><strong>{activeChunks.length}</strong> Mapped Content Chunks</span>
                    </div>
                    <div className="metric-tag">
                      <GitBranch size={13} className="text-purple" />
                      <span><strong>{activePrerequisites.length}</strong> Prerequisites</span>
                    </div>
                  </div>
                </div>

                {/* Prerequisites Row */}
                {activePrerequisites.length > 0 && (
                  <div className="inspector-section-card glass-panel">
                    <div className="card-section-title">
                      <GitBranch size={14} className="text-purple" />
                      <span>Curriculum Prerequisites</span>
                    </div>
                    <div className="inspector-prereq-chips">
                      {activePrerequisites.map((pr, idx) => (
                        <button 
                          key={idx} 
                          type="button" 
                          className="prereq-link-chip"
                          onClick={() => {
                            if (concepts.includes(pr)) {
                              setSelectedConcept(pr);
                            }
                          }}
                          title={`Click to inspect ${pr}`}
                        >
                          <span>{pr}</span>
                          <ChevronRight size={12} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Parent Category & Evidence Text */}
                {activeEnriched?.category_edge && (
                  <div className="inspector-section-card glass-panel">
                    <div className="card-section-title">
                      <Quote size={14} className="text-accent-cyan" />
                      <span>Category Evidence from Course Textbook</span>
                    </div>
                    <p className="inspector-evidence-quote">
                      "{activeEnriched.category_edge.evidence_text}"
                    </p>
                    <div className="inspector-evidence-meta">
                      <span>Source Chunk: <code className="code-tag">{activeEnriched.category_edge.evidence_chunk}</code></span>
                      <span>Confidence: <strong>{activeEnriched.category_edge.confidence * 100}%</strong></span>
                    </div>
                  </div>
                )}

                {/* Compact Mapped Chunks Grid */}
                <div className="inspector-section-card glass-panel">
                  <div className="card-section-title">
                    <BookOpen size={14} className="text-indigo" />
                    <span>Mapped Content Chunks ({activeChunks.length})</span>
                  </div>

                  {activeChunks.length === 0 ? (
                    <p className="text-muted text-sm">No direct chunks linked to this concept.</p>
                  ) : (
                    <div className="inspector-chunks-grid">
                      {activeChunks.map((chunkId) => {
                        const chunkInfo = chunksById[chunkId];
                        return (
                          <div key={chunkId} className="inspector-chunk-box">
                            <div className="chunk-box-top">
                              <code className="chunk-box-id">{chunkId}</code>
                              <button 
                                type="button" 
                                className="copy-icon-btn"
                                onClick={() => handleCopyChunkId(chunkId)}
                                title="Copy chunk ID"
                              >
                                {copiedId === chunkId ? <CheckCircle2 size={13} className="text-emerald" /> : <Copy size={13} />}
                              </button>
                            </div>
                            {chunkInfo && (
                              <div className="chunk-box-meta">
                                <span>Page {chunkInfo.page_number}</span>
                                <span>•</span>
                                <span className="chunk-book-truncate">{chunkInfo.book_name}</span>
                              </div>
                            )}
                            {chunkInfo?.text && (
                              <p className="chunk-mini-excerpt">
                                "{chunkInfo.text.substring(0, 110)}..."
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="empty-inspector-state">
                <Share2 size={36} className="text-muted" />
                <p>Select a concept from the list on the left to inspect its details immediately.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ================= PAGINATED CARDS VIEW ================= */
        <div className="paginated-cards-section">
          <div className="concepts-grid">
            {paginatedConcepts.map((conceptName) => {
              const mappedChunks = conceptMap[conceptName] || [];
              const enriched = enrichedMap[conceptName.toLowerCase()];
              const categories = enriched?.coarse_grained_category || ['Compiler Design & Principles'];
              const categoryLabel = Array.isArray(categories) ? categories[0] : categories;
              const prerequisites = enriched?.prerequisites || [];

              return (
                <div 
                  key={conceptName} 
                  className="concept-card glass-panel glow-hover"
                  onClick={() => {
                    setSelectedConcept(conceptName);
                    setViewMode('split');
                  }}
                >
                  <div className="concept-card-top">
                    <div className="concept-tag-category">
                      <span className="dot-purple"></span>
                      <span>{categoryLabel}</span>
                    </div>
                    <div className="chunks-count-pill" title={`${mappedChunks.length} content chunks linked`}>
                      <Link2 size={12} />
                      <span>{mappedChunks.length} {mappedChunks.length === 1 ? 'Chunk' : 'Chunks'}</span>
                    </div>
                  </div>

                  <h3 className="concept-name">{conceptName}</h3>

                  {prerequisites.length > 0 && (
                    <div className="concept-prerequisites-row">
                      <span className="prereq-label">
                        <GitBranch size={12} />
                        <span>Prerequisites:</span>
                      </span>
                      <div className="prereq-chips">
                        {prerequisites.slice(0, 2).map((pr, idx) => (
                          <span key={idx} className="prereq-chip">{pr}</span>
                        ))}
                        {prerequisites.length > 2 && (
                          <span className="prereq-more">+{prerequisites.length - 2}</span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="concept-card-footer">
                    <span className="view-detail-hint">
                      <span>Inspect Details & Evidence</span>
                      <ChevronRight size={14} />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {filteredConcepts.length > PAGE_SIZE && (
            <div className="pagination-bar glass-panel" style={{ marginTop: '1rem' }}>
              <div className="pagination-info">
                Showing <strong>{(currentPage - 1) * PAGE_SIZE + 1}</strong> to <strong>{Math.min(currentPage * PAGE_SIZE, filteredConcepts.length)}</strong> of <strong>{filteredConcepts.length}</strong> concepts
              </div>

              <div className="pagination-actions">
                <button 
                  type="button" 
                  className="page-nav-btn" 
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                >
                  <ChevronLeft size={16} />
                  <span>Previous</span>
                </button>

                <span className="page-indicator">
                  Page {currentPage} of {totalPages}
                </span>

                <button 
                  type="button" 
                  className="page-nav-btn" 
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                >
                  <span>Next</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
