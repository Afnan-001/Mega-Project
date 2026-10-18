import React, { useState, useEffect, useMemo } from 'react';
import { 
  FileText, 
  Search, 
  BookOpen, 
  Layers, 
  ExternalLink, 
  ChevronLeft, 
  ChevronRight, 
  Share2, 
  Filter,
  CheckCircle2,
  Copy,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { loadContentChunks, loadConceptChunkMap, buildChunkToConceptsMap } from '../../services/dataService';

export default function ContentChunksView() {
  const [chunks, setChunks] = useState([]);
  const [conceptMap, setConceptMap] = useState({});
  const [chunkToConcepts, setChunkToConcepts] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBook, setSelectedBook] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedChunkId, setExpandedChunkId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const PAGE_SIZE = 12;

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      const [chunksData, mapData] = await Promise.all([
        loadContentChunks(),
        loadConceptChunkMap()
      ]);
      setChunks(chunksData || []);
      setConceptMap(mapData || {});
      setChunkToConcepts(buildChunkToConceptsMap(mapData || {}));
      setLoading(false);
    }
    fetchData();
  }, []);

  // Filter books
  const booksList = useMemo(() => {
    const set = new Set(chunks.map(c => c.book_name).filter(Boolean));
    return ['all', ...Array.from(set)];
  }, [chunks]);

  // Filtered chunks
  const filteredChunks = useMemo(() => {
    let result = chunks;
    if (selectedBook !== 'all') {
      result = result.filter(c => c.book_name === selectedBook);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(c => 
        (c.chunk_id && c.chunk_id.toLowerCase().includes(q)) ||
        (c.text && c.text.toLowerCase().includes(q)) ||
        (c.page_number && c.page_number.toString().includes(q)) ||
        (chunkToConcepts[c.chunk_id] && chunkToConcepts[c.chunk_id].some(con => con.toLowerCase().includes(q)))
      );
    }
    return result;
  }, [chunks, selectedBook, searchQuery, chunkToConcepts]);

  const totalPages = Math.ceil(filteredChunks.length / PAGE_SIZE) || 1;
  const paginatedChunks = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredChunks.slice(start, start + PAGE_SIZE);
  }, [filteredChunks, currentPage]);

  const handleCopyId = (id) => {
    navigator.clipboard?.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="json-view-container animate-fade-in">
      {/* Section Header */}
      <div className="section-title-bar glass-panel">
        <div className="title-left">
          <div className="title-icon-pill bg-indigo-glow">
            <FileText size={22} className="text-indigo" />
          </div>
          <div>
            <h2>Extracted Content Chunks</h2>
            <p>Direct view of raw semantic text units extracted from course PDFs (<code className="code-tag">content_chunks.json</code>)</p>
          </div>
        </div>

        <div className="title-stats-pills">
          <div className="stat-pill">
            <span className="stat-pill-label">Total Chunks</span>
            <strong className="stat-pill-val">{chunks.length.toLocaleString()}</strong>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-label">Source Books</span>
            <strong className="stat-pill-val">{booksList.length > 1 ? booksList.length - 1 : 1}</strong>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-label">Filtered</span>
            <strong className="stat-pill-val">{filteredChunks.length.toLocaleString()}</strong>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-controls-row glass-panel">
        <div className="search-box-large">
          <Search size={18} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search chunks by keywords, chunk ID (e.g. p117_c0), or concept..." 
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

        <div className="filter-select-group">
          <Filter size={16} className="text-muted" />
          <select 
            value={selectedBook} 
            onChange={(e) => {
              setSelectedBook(e.target.value);
              setCurrentPage(1);
            }}
            className="custom-dropdown"
          >
            {booksList.map((b) => (
              <option key={b} value={b}>
                {b === 'all' ? 'All Source Books' : b}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Chunks List */}
      {loading ? (
        <div className="loading-state-box glass-panel">
          <div className="spinner-border large-spinner"></div>
          <h4>Loading content chunks from JSON...</h4>
          <p>Parsing 18,000+ lines of extracted curriculum text</p>
        </div>
      ) : filteredChunks.length === 0 ? (
        <div className="empty-state-box glass-panel">
          <FileText size={42} className="text-muted" />
          <h4>No matching content chunks found</h4>
          <p>Try refining your search terms or clearing the filter.</p>
          <button type="button" className="btn-secondary" onClick={() => { setSearchQuery(''); setSelectedBook('all'); }}>
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="chunks-grid">
          {paginatedChunks.map((chunk) => {
            const isExpanded = expandedChunkId === chunk.chunk_id;
            const mappedConcepts = chunkToConcepts[chunk.chunk_id] || [];
            return (
              <div key={chunk.chunk_id} className="chunk-card glass-panel glow-hover">
                <div className="chunk-card-header">
                  <div className="chunk-id-tag">
                    <span className="chunk-id-text">{chunk.chunk_id}</span>
                    <button 
                      type="button" 
                      className="copy-id-btn"
                      onClick={() => handleCopyId(chunk.chunk_id)}
                      title="Copy chunk ID"
                    >
                      {copiedId === chunk.chunk_id ? <CheckCircle2 size={13} className="text-emerald" /> : <Copy size={13} />}
                    </button>
                  </div>
                  <div className="chunk-meta-pills">
                    <span className="book-pill">{chunk.book_name}</span>
                    <span className="page-pill">Page {chunk.page_number}</span>
                  </div>
                </div>

                <div className="chunk-text-content">
                  <p className={isExpanded ? 'text-expanded' : 'text-clamped'}>
                    {chunk.text}
                  </p>
                  {chunk.text && chunk.text.length > 220 && (
                    <button 
                      type="button" 
                      className="toggle-expand-btn"
                      onClick={() => setExpandedChunkId(isExpanded ? null : chunk.chunk_id)}
                    >
                      {isExpanded ? (
                        <><span>Show Less</span> <ChevronUp size={14} /></>
                      ) : (
                        <><span>Show Full Text</span> <ChevronDown size={14} /></>
                      )}
                    </button>
                  )}
                </div>

                {/* Mapped Concepts badges for this chunk */}
                {mappedConcepts.length > 0 && (
                  <div className="chunk-mapped-concepts">
                    <span className="concepts-header-label">
                      <Share2 size={12} className="text-indigo" />
                      <span>Mapped Concepts ({mappedConcepts.length}):</span>
                    </span>
                    <div className="concept-tags-flow">
                      {mappedConcepts.slice(0, 4).map((con, idx) => (
                        <span key={idx} className="concept-badge-tag" title={con}>
                          {con}
                        </span>
                      ))}
                      {mappedConcepts.length > 4 && (
                        <span className="more-concepts-badge">
                          +{mappedConcepts.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && filteredChunks.length > PAGE_SIZE && (
        <div className="pagination-bar glass-panel">
          <div className="pagination-info">
            Showing <strong>{(currentPage - 1) * PAGE_SIZE + 1}</strong> to <strong>{Math.min(currentPage * PAGE_SIZE, filteredChunks.length)}</strong> of <strong>{filteredChunks.length.toLocaleString()}</strong> chunks
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
  );
}
