import React, { useState } from 'react';
import { 
  FileText, 
  Share2, 
  BookOpen, 
  Search, 
  HelpCircle, 
  CheckCircle2, 
  ExternalLink,
  Layers,
  ArrowRight
} from 'lucide-react';

export default function StudentMaterialsView({ 
  courses = [], 
  materials = [], 
  onOpenConceptMap,
  onAskTutor 
}) {
  const [selectedCourseFilter, setSelectedCourseFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Enrolled courses map
  const enrolledCourseIds = new Set(courses.map(c => c.id));

  // Filter materials for enrolled courses
  const studentMaterials = materials.filter(m => 
    enrolledCourseIds.has(m.courseId) || courses.length === 0
  );

  const filteredMaterials = studentMaterials.filter((item) => {
    const matchesCourse = selectedCourseFilter === 'all' || item.courseId === selectedCourseFilter;
    const matchesSearch = 
      item.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.fileName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.courseName?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCourse && matchesSearch;
  });

  return (
    <div className="student-materials-view animate-fade-in">
      {/* Header */}
      <div className="materials-header" style={{ marginBottom: '1.5rem' }}>
        <div className="header-titles">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="faculty-badge">
              <FileText size={14} className="text-cyan" />
              <span>Course Materials & Curriculum PDFs</span>
            </span>
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fff', margin: '4px 0' }}>
            Enrolled Course Materials & Textbooks
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Access textbook chapters, lecture slides, and curriculum materials indexed into your knowledge graph.
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {courses.length > 1 && (
            <select
              value={selectedCourseFilter}
              onChange={(e) => setSelectedCourseFilter(e.target.value)}
              className="custom-select"
              style={{
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#e2e8f0',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '12px',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="all">All Enrolled Courses</option>
              {courses.map(c => (
                <option key={c.id} value={c.id}>
                  {c.name || c.title}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Search Bar */}
      <div className="materials-filter-bar" style={{ marginBottom: '1.5rem' }}>
        <div className="search-box" style={{ flex: 1 }}>
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search textbook materials by title or chapter..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Materials Grid / Cards */}
      {filteredMaterials.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '3.5rem 1rem', borderRadius: '14px', color: '#94a3b8' }}>
          <FileText size={40} style={{ color: '#475569', margin: '0 auto 12px' }} />
          <h4 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: '6px' }}>
            No Course Materials Found
          </h4>
          <p style={{ fontSize: '0.85rem', maxWidth: '420px', margin: '0 auto' }}>
            {courses.length === 0 
              ? 'You are not currently enrolled in any courses with uploaded textbooks.'
              : 'Textbook materials uploaded by your instructor will appear here once processed.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.25rem' }}>
          {filteredMaterials.map((mat) => (
            <div 
              key={mat.id} 
              className="glass-panel glow-hover"
              style={{
                borderRadius: '14px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                gap: '14px'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f87171' }}>
                      <FileText size={18} />
                    </div>
                    <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {mat.courseName || 'Course Material'}
                    </span>
                  </div>
                  <span className="status-badge status-indexed" style={{ fontSize: '11px', padding: '3px 8px' }}>
                    <CheckCircle2 size={12} />
                    <span>Indexed</span>
                  </span>
                </div>

                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', margin: '4px 0 6px', lineHeight: 1.4 }}>
                  {mat.title}
                </h3>
                <span style={{ fontSize: '12px', color: '#64748b', display: 'block', marginBottom: '10px' }}>
                  {mat.fileName} • {mat.pages || 45} pages
                </span>

                {/* Concepts Extracted & Triples */}
                <div style={{ display: 'flex', gap: '12px', background: 'rgba(15, 23, 42, 0.4)', padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.04)' }}>
                  <div>
                    <span style={{ fontSize: '10px', color: '#64748b', display: 'block', textTransform: 'uppercase' }}>Concepts</span>
                    <strong style={{ fontSize: '13px', color: '#818cf8' }}>{mat.conceptsExtracted || 124} Nodes</strong>
                  </div>
                  <div style={{ borderLeft: '1px solid rgba(255,255,255,0.06)', paddingLeft: '12px' }}>
                    <span style={{ fontSize: '10px', color: '#64748b', display: 'block', textTransform: 'uppercase' }}>Relations</span>
                    <strong style={{ fontSize: '13px', color: '#10b981' }}>{mat.relationsExtracted || 218} Triples</strong>
                  </div>
                </div>

                {/* Modules Chips */}
                {mat.modules && mat.modules.length > 0 && (
                  <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {mat.modules.map((mod, i) => (
                      <span key={i} style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#94a3b8', borderRadius: '4px', padding: '2px 6px', fontSize: '10px' }}>
                        {mod}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px' }}>
                <button
                  type="button"
                  className="btn-ghost-hero"
                  onClick={() => onOpenConceptMap && onOpenConceptMap(mat.courseId)}
                  style={{ flex: 1, padding: '6px 10px', fontSize: '11px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                >
                  <Share2 size={13} className="text-cyan" />
                  <span>Concept Map</span>
                </button>

                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => onAskTutor && onAskTutor(mat.modules?.[0] || '')}
                  style={{ flex: 1, padding: '6px 10px', fontSize: '11px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                >
                  <HelpCircle size={13} />
                  <span>Ask Tutor</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
