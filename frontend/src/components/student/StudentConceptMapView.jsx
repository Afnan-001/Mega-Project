import React, { useMemo, useState, useEffect } from 'react';
import { 
  Share2, 
  Search, 
  HelpCircle, 
  Award, 
  RefreshCw,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { studentApi } from '../../services/api';

export default function StudentConceptMapView({ 
  courses = [], 
  onAskTutor,
  onTakeQuiz,
  masteryRefreshKey = 0,
}) {
  const [selectedCourseId, setSelectedCourseId] = useState(courses[0]?.id || '');
  const [learningPath, setLearningPath] = useState([]);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [studentGraph, setStudentGraph] = useState(null);
  const [isGraphLoading, setIsGraphLoading] = useState(false);
  const [graphRefreshKey, setGraphRefreshKey] = useState(0);

  useEffect(() => {
    if (!selectedCourseId && courses.length > 0) {
      setSelectedCourseId(courses[0].id);
    }
  }, [courses, selectedCourseId]);

  useEffect(() => {
    if (!selectedCourseId) return;
    const fetchPath = async () => {
      try {
        const res = await studentApi.getLearningPath(selectedCourseId);
        if (res && Array.isArray(res.path)) {
          setLearningPath(res.path);
        }
      } catch {
        setLearningPath([]);
      }
    };
    fetchPath();
  }, [selectedCourseId]);

  useEffect(() => {
    if (!selectedCourseId) {
      setStudentGraph(null);
      return;
    }
    const fetchStudentGraph = async () => {
      setIsGraphLoading(true);
      try {
        setStudentGraph(await studentApi.getKnowledgeGraph(selectedCourseId));
      } catch {
        setStudentGraph(null);
      } finally {
        setIsGraphLoading(false);
      }
    };
    fetchStudentGraph();
  }, [selectedCourseId, masteryRefreshKey, graphRefreshKey]);

  const currentCourse = courses.find(c => c.id === selectedCourseId) || courses[0];
  const filteredConcepts = learningPath.filter(item => 
    !searchQuery || item.concept_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const graphLayout = useMemo(() => {
    const nodes = studentGraph?.nodes || [];
    const width = 900;
    const height = 520;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(180, Math.max(80, 42 * nodes.length));
    return nodes.map((node, index) => {
      const angle = nodes.length === 1 ? -Math.PI / 2 : (2 * Math.PI * index / nodes.length) - Math.PI / 2;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });
  }, [studentGraph]);

  const graphNodeMap = useMemo(
    () => new Map(graphLayout.map(node => [node.id, node])),
    [graphLayout],
  );

  return (
    <div className="student-concept-map-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: '640px' }}>
      {/* Top Header */}
      <div className="glass-panel" style={{ padding: '16px 20px', borderRadius: '12px', marginBottom: '16px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
            <Share2 size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', margin: 0 }}>
              My Knowledge Graph
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '2px 0 0' }}>
              Your graph grows when you master a concept (85% BKT mastery or higher)
            </p>
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {courses.length > 0 && (
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              className="custom-select"
              style={{
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#e2e8f0',
                border: '1px solid rgba(6, 182, 212, 0.35)',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              {courses.map(c => (
                <option key={c.id} value={c.id}>
                  {c.name || c.title}
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            className="btn-ghost-hero"
            onClick={() => setGraphRefreshKey(k => k + 1)}
            title="Refresh my knowledge graph"
            style={{ padding: '6px 10px' }}
          >
            <RefreshCw size={14} />
          </button>

        </div>
      </div>

      {/* Main Split Grid: Interactive Graph + Concept Quick Inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '16px', flex: 1, minHeight: 0 }}>
        {/* Personal mastered-concept graph */}
        <div 
          className="glass-panel" 
          style={{ 
            borderRadius: '14px', 
            overflow: 'hidden', 
            position: 'relative',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <div style={{ padding: '16px 20px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
            <div>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '0.95rem' }}>Mastered concepts</h3>
              <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: '0.75rem' }}>
                {studentGraph ? `${studentGraph.mastered_concepts_count} of ${studentGraph.total_concepts_count} concepts unlocked in your graph` : 'Loading your progress…'}
              </p>
            </div>
            <span style={{ color: '#34d399', fontSize: '0.72rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={14} /> Mastered
            </span>
          </div>
          <div style={{ flex: 1, minHeight: 0, padding: '12px' }}>
            {isGraphLoading ? (
              <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: '#94a3b8', gap: '8px' }}>
                <Loader2 size={28} className="animate-spin" />
              </div>
            ) : graphLayout.length === 0 ? (
              <div style={{ height: '100%', display: 'grid', placeItems: 'center', textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                <div>
                  <Award size={34} color="#64748b" style={{ marginBottom: '12px' }} />
                  <div style={{ color: '#e2e8f0', fontWeight: 700, marginBottom: '6px' }}>Your graph is ready to grow</div>
                  <div style={{ fontSize: '0.8rem', lineHeight: 1.5 }}>Pass quizzes to reach 85% mastery. Each mastered concept will appear here with its mastered prerequisites.</div>
                </div>
              </div>
            ) : (
              <svg viewBox="0 0 900 520" role="img" aria-label="Student knowledge graph" style={{ width: '100%', height: '100%', minHeight: '360px', background: 'radial-gradient(circle at center, rgba(16, 185, 129, 0.10), transparent 65%)' }}>
                <defs>
                  <marker id="knowledge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#34d399" />
                  </marker>
                </defs>
                {(studentGraph?.edges || []).map((edge) => {
                  const source = graphNodeMap.get(edge.source);
                  const target = graphNodeMap.get(edge.target);
                  if (!source || !target) return null;
                  return <line key={`${edge.source}-${edge.target}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="rgba(52, 211, 153, 0.55)" strokeWidth="2" markerEnd="url(#knowledge-arrow)" />;
                })}
                {graphLayout.map((node) => (
                  <g key={node.id} onClick={() => setSelectedConcept(learningPath.find(item => item.concept_name === node.id) || { concept_name: node.id, mastery_percentage: node.mastery_percentage, status: 'Mastered' })} style={{ cursor: 'pointer' }}>
                    <circle cx={node.x} cy={node.y} r="29" fill="#065f46" stroke="#34d399" strokeWidth="3" />
                    <text x={node.x} y={node.y + 5} textAnchor="middle" fill="#ecfdf5" fontSize="13" fontWeight="700">{Math.round(node.mastery_percentage)}%</text>
                    <text x={node.x} y={node.y + 47} textAnchor="middle" fill="#e2e8f0" fontSize="12">{node.label.length > 24 ? `${node.label.slice(0, 22)}…` : node.label}</text>
                  </g>
                ))}
              </svg>
            )}
          </div>
        </div>

        {/* Sidebar: Concept Browser & Inspector */}
        <div 
          className="glass-panel" 
          style={{ 
            borderRadius: '14px', 
            padding: '16px', 
            display: 'flex', 
            flexDirection: 'column',
            gap: '12px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            minHeight: 0
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#f8fafc', fontWeight: 600 }}>
              Curriculum Concepts ({learningPath.length})
            </h4>
          </div>

          {/* Search Box */}
          <div className="search-box" style={{ padding: '6px 10px' }}>
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Search concepts in graph..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ fontSize: '12px' }}
            />
          </div>

          {/* Concept List */}
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {filteredConcepts.map((item, idx) => {
              const isSelected = selectedConcept?.concept_name === item.concept_name;
              const isMastered = item.status === 'Mastered';
              const isInProgress = item.status === 'In Progress';
              const isReady = item.status === 'Ready to Learn';

              let statusColor = '#94a3b8';
              if (isMastered) statusColor = '#10b981';
              else if (isInProgress) statusColor = '#38bdf8';
              else if (isReady) statusColor = '#f59e0b';

              return (
                <div
                  key={idx}
                  onClick={() => setSelectedConcept(item)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: isSelected ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                    border: isSelected ? '1px solid #6366f1' : '1px solid rgba(255, 255, 255, 0.05)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: isSelected ? '#fff' : '#e2e8f0' }}>
                      {item.concept_name}
                    </span>
                    <span style={{ fontSize: '11px', color: statusColor, fontWeight: 700 }}>
                      {Math.round(item.mastery_percentage || 10)}%
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#64748b' }}>
                    <span>{item.coarse_grained_category?.[0] || 'Topic'}</span>
                    <span style={{ color: statusColor }}>{item.status}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Concept Actions */}
          {selectedConcept && (
            <div 
              style={{ 
                padding: '12px', 
                borderRadius: '10px', 
                background: 'rgba(99, 102, 241, 0.1)', 
                border: '1px solid rgba(99, 102, 241, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc' }}>
                {selectedConcept.concept_name}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => onAskTutor && onAskTutor(selectedConcept.concept_name)}
                  style={{
                    flex: 1,
                    padding: '6px 10px',
                    borderRadius: '6px',
                    background: 'linear-gradient(135deg, #4f46e5, #06b6d4)',
                    color: '#fff',
                    border: 'none',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px'
                  }}
                >
                  <HelpCircle size={13} />
                  <span>Ask Tutor</span>
                </button>

                <button
                  type="button"
                  onClick={() => onTakeQuiz && onTakeQuiz(selectedConcept.concept_name, selectedCourseId)}
                  style={{
                    flex: 1,
                    padding: '6px 10px',
                    borderRadius: '6px',
                    background: 'rgba(16, 185, 129, 0.2)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.35)',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px'
                  }}
                >
                  <Award size={13} />
                  <span>Quiz Concept</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
