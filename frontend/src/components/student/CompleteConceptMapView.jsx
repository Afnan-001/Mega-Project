import React, { useEffect, useRef, useState } from 'react';
import { ExternalLink, RefreshCw, Search, Share2 } from 'lucide-react';
import { graphApi, studentApi } from '../../services/api';

/** Shows the complete, course-wide curriculum graph without filtering by mastery. */
export default function CompleteConceptMapView({ courses = [] }) {
  const [selectedCourseId, setSelectedCourseId] = useState(courses[0]?.id || '');
  const [refreshKey, setRefreshKey] = useState(0);
  const [concepts, setConcepts] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMatch, setSelectedMatch] = useState(null);
  const graphFrameRef = useRef(null);

  useEffect(() => {
    if (!selectedCourseId && courses.length) setSelectedCourseId(courses[0].id);
  }, [courses, selectedCourseId]);

  useEffect(() => {
    if (!selectedCourseId) return;
    setSearchQuery('');
    setSelectedMatch(null);
    studentApi.getLearningPath(selectedCourseId)
      .then(result => setConcepts((result?.path || []).map(item => item.concept_name)))
      .catch(() => setConcepts([]));
  }, [selectedCourseId]);

  const graphUrl = selectedCourseId
    ? graphApi.getCourseRawHtmlUrl(selectedCourseId)
    : graphApi.getRawHtmlUrl();
  const graphOrigin = new URL(graphUrl, window.location.origin).origin;

  const matchingConcepts = searchQuery.trim()
    ? concepts.filter(concept => concept.toLowerCase().includes(searchQuery.trim().toLowerCase())).slice(0, 7)
    : [];

  const highlightConcept = (concept) => {
    setSelectedMatch(concept);
    setSearchQuery(concept);
    graphFrameRef.current?.contentWindow?.postMessage({ type: 'edugraph:highlight-concept', concept }, graphOrigin);
  };

  const handleFrameLoad = () => {
    if (selectedMatch) highlightConcept(selectedMatch);
  };

  return (
    <div className="student-concept-map-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: '640px' }}>
      <div className="glass-panel" style={{ padding: '16px 20px', borderRadius: '12px', marginBottom: '16px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', display: 'grid', placeItems: 'center', color: '#fff' }}>
            <Share2 size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', margin: 0 }}>Complete Curriculum Graph</h2>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '2px 0 0' }}>Explore every concept and prerequisite in the course.</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {courses.length > 0 && <select value={selectedCourseId} onChange={(event) => setSelectedCourseId(event.target.value)} className="custom-select" style={{ background: 'rgba(15, 23, 42, 0.85)', color: '#e2e8f0', border: '1px solid rgba(6, 182, 212, 0.35)', borderRadius: '8px', padding: '6px 12px', fontSize: '12px', fontWeight: 600, outline: 'none' }}>
            {courses.map(course => <option key={course.id} value={course.id}>{course.name || course.title}</option>)}
          </select>}
          <button type="button" className="btn-ghost-hero" onClick={() => setRefreshKey(key => key + 1)} title="Reload curriculum graph" style={{ padding: '6px 10px' }}><RefreshCw size={14} /></button>
          <a href={graphUrl} target="_blank" rel="noopener noreferrer" className="btn-ghost-hero" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px', textDecoration: 'none' }}><span>Fullscreen</span><ExternalLink size={13} /></a>
        </div>
      </div>
      <div className="glass-panel" style={{ padding: '14px 16px', borderRadius: '12px', marginBottom: '16px', position: 'relative', zIndex: 2 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '9px', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.22)', borderRadius: '9px', padding: '0 12px', background: 'rgba(15, 23, 42, 0.45)' }}>
          <Search size={16} />
          <input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && matchingConcepts[0]) highlightConcept(matchingConcepts[0]);
            }}
            placeholder="Search a concept and press Enter to locate it in the graph…"
            style={{ width: '100%', background: 'transparent', border: 0, color: '#e2e8f0', padding: '11px 0', outline: 'none', fontSize: '13px' }}
          />
        </div>
        {matchingConcepts.length > 0 && (
          <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '7px' }}>
            {matchingConcepts.map(concept => (
              <button key={concept} type="button" onClick={() => highlightConcept(concept)} style={{ border: '1px solid rgba(56, 189, 248, 0.35)', background: selectedMatch === concept ? 'rgba(56, 189, 248, 0.22)' : 'rgba(15, 23, 42, 0.6)', color: '#bae6fd', borderRadius: '16px', padding: '5px 10px', cursor: 'pointer', fontSize: '12px' }}>{concept}</button>
            ))}
          </div>
        )}
        {searchQuery.trim() && matchingConcepts.length === 0 && <p style={{ margin: '8px 2px 0', color: '#94a3b8', fontSize: '12px' }}>No matching concept in this course graph.</p>}
      </div>
      <div className="glass-panel" style={{ flex: 1, borderRadius: '14px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <iframe ref={graphFrameRef} key={refreshKey} onLoad={handleFrameLoad} src={graphUrl} title="Complete curriculum knowledge graph" style={{ width: '100%', height: '100%', border: 'none', background: '#0a0d14' }} />
      </div>
    </div>
  );
}
