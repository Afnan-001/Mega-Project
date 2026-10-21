import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  Share2, 
  CheckCircle, 
  FileText, 
  Sparkles, 
  HelpCircle, 
  ExternalLink,
  Search,
  ArrowRight,
  Lock,
  Play,
  Award,
  Layers,
  Activity,
  Flame,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { studentApi } from '../../services/api';
import CognitiveRagQuizModal from './CognitiveRagQuizModal';

export default function StudentOverview({ materials, courses, onSwitchToTeacher }) {
  const [activeCourseTab, setActiveCourseTab] = useState(courses[0]?.id || 'ai402');
  const [learningPath, setLearningPath] = useState([]);
  const [masteryData, setMasteryData] = useState(null);
  const [isLoadingPath, setIsLoadingPath] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState('Knowledge Representation');
  const [activeTab, setActiveTab] = useState('path'); // 'path' | 'materials' | 'heatmap'

  // Quiz Modal State
  const [quizModal, setQuizModal] = useState({
    isOpen: false,
    conceptName: null,
  });

  const selectedCourseMaterials = materials.filter(m => m.courseId === activeCourseTab);
  const currentCourse = courses.find(c => c.id === activeCourseTab) || courses[0];

  // Fetch topological prerequisite learning path and mastery heatmap
  useEffect(() => {
    async function loadStudentData() {
      setIsLoadingPath(true);
      try {
        const pathRes = await studentApi.getLearningPath(activeCourseTab);
        if (pathRes && pathRes.path) {
          setLearningPath(pathRes.path);
        } else {
          throw new Error('No path data');
        }
      } catch (err) {
        // Fallback default learning path with BKT statuses
        setLearningPath([
          {
            concept_name: 'Lexical Analysis',
            node_type: 'fine_grained_concept',
            coarse_grained_category: ['Compiler Front End'],
            prerequisites: [],
            mastery_percentage: 88.5,
            status: 'Mastered'
          },
          {
            concept_name: 'Regular Expressions & Automata',
            node_type: 'fine_grained_concept',
            coarse_grained_category: ['Compiler Front End'],
            prerequisites: ['Lexical Analysis'],
            mastery_percentage: 72.0,
            status: 'In Progress'
          },
          {
            concept_name: 'Syntax Analysis & Parsing',
            node_type: 'fine_grained_concept',
            coarse_grained_category: ['Compiler Front End'],
            prerequisites: ['Regular Expressions & Automata'],
            mastery_percentage: 15.0,
            status: 'Ready to Learn'
          },
          {
            concept_name: 'Context-Free Grammars',
            node_type: 'fine_grained_concept',
            coarse_grained_category: ['Grammar Theory'],
            prerequisites: ['Syntax Analysis & Parsing'],
            mastery_percentage: 10.0,
            status: 'Locked'
          },
          {
            concept_name: 'LR Parsing Tables',
            node_type: 'fine_grained_concept',
            coarse_grained_category: ['Parsing Algorithms'],
            prerequisites: ['Context-Free Grammars'],
            mastery_percentage: 10.0,
            status: 'Locked'
          },
          {
            concept_name: 'Semantic Analysis & Type Checking',
            node_type: 'fine_grained_concept',
            coarse_grained_category: ['Compiler Middle End'],
            prerequisites: ['Syntax Analysis & Parsing'],
            mastery_percentage: 10.0,
            status: 'Locked'
          }
        ]);
      }

      // Fetch mastery
      try {
        const heatRes = await studentApi.getMasteryHeatmap(activeCourseTab);
        if (heatRes) {
          setMasteryData(heatRes);
        }
      } catch (err) {
        setMasteryData({
          overall_mastery_percentage: 45.2,
          concepts: [
            { concept_name: 'Lexical Analysis', mastery_percentage: 88.5, status: 'Mastered' },
            { concept_name: 'Regular Expressions & Automata', mastery_percentage: 72.0, status: 'In Progress' },
            { concept_name: 'Syntax Analysis & Parsing', mastery_percentage: 15.0, status: 'Ready to Learn' },
          ]
        });
      } finally {
        setIsLoadingPath(false);
      }
    }

    loadStudentData();
  }, [activeCourseTab]);

  const handleMasteryUpdated = (result) => {
    // Update latent mastery live in learningPath state
    if (result && result.updated_mastery !== undefined) {
      setLearningPath((prev) =>
        prev.map((item) => {
          if (item.concept_name === quizModal.conceptName) {
            const updated = result.updated_mastery;
            let status = 'In Progress';
            if (updated >= 85) status = 'Mastered';
            else if (updated < 15) status = 'Ready to Learn';
            return {
              ...item,
              mastery_percentage: updated,
              status
            };
          }
          return item;
        })
      );
    }
  };

  const masteredCount = learningPath.filter(p => p.status === 'Mastered').length;

  return (
    <div className="student-dashboard-content animate-fade-in">
      {/* Student Welcome Banner */}
      <div className="student-hero-banner glass-panel">
        <div className="hero-text-side">
          <div className="banner-badge">
            <Sparkles size={14} className="text-accent" />
            <span>Cognitive-RAG Adaptive Learning Portal</span>
          </div>
          <h2>Welcome back, Alex!</h2>
          <p>
            Explore AI-extracted knowledge graphs and dynamic prerequisite learning paths.
            Your mastery is continuously updated using Bayesian Knowledge Tracing (BKT) as you practice.
          </p>

          <div className="banner-stats-row">
            <div className="mini-stat">
              <span className="stat-num">{courses.length}</span>
              <span className="stat-label">Enrolled Courses</span>
            </div>
            <div className="mini-stat">
              <span className="stat-num">{learningPath.length}</span>
              <span className="stat-label">DAG Path Concepts</span>
            </div>
            <div className="mini-stat">
              <span className="stat-num" style={{ color: '#10b981' }}>{masteredCount}</span>
              <span className="stat-label">Concepts Mastered</span>
            </div>
          </div>
        </div>

        <div className="hero-action-side">
          <button 
            type="button" 
            className="btn-accent"
            onClick={() => setQuizModal({ isOpen: true, conceptName: null })}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px' }}
          >
            <Sparkles size={16} />
            <span>Start Adaptive Quiz (Cognitive-RAG)</span>
          </button>
        </div>
      </div>

      {/* Course Navigation Pills */}
      <div className="course-tabs-selector" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {courses.map((course) => (
            <button
              key={course.id}
              type="button"
              className={`course-tab-pill ${activeCourseTab === course.id ? 'active' : ''}`}
              onClick={() => setActiveCourseTab(course.id)}
            >
              <BookOpen size={16} />
              <span>{course.code || course.id}: {course.name || course.title}</span>
            </button>
          ))}
        </div>

        {/* View Switcher: Learning Path vs Materials vs Heatmap */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            type="button"
            className={`btn-secondary ${activeTab === 'path' ? 'active-tab-btn' : ''}`}
            onClick={() => setActiveTab('path')}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              background: activeTab === 'path' ? 'rgba(99,102,241,0.2)' : 'transparent',
              border: activeTab === 'path' ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
              color: activeTab === 'path' ? '#818cf8' : '#94a3b8'
            }}
          >
            Topological Learning Path
          </button>
          <button
            type="button"
            className={`btn-secondary ${activeTab === 'materials' ? 'active-tab-btn' : ''}`}
            onClick={() => setActiveTab('materials')}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              background: activeTab === 'materials' ? 'rgba(99,102,241,0.2)' : 'transparent',
              border: activeTab === 'materials' ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
              color: activeTab === 'materials' ? '#818cf8' : '#94a3b8'
            }}
          >
            Course PDFs ({selectedCourseMaterials.length})
          </button>
          <button
            type="button"
            className={`btn-secondary ${activeTab === 'heatmap' ? 'active-tab-btn' : ''}`}
            onClick={() => setActiveTab('heatmap')}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              background: activeTab === 'heatmap' ? 'rgba(99,102,241,0.2)' : 'transparent',
              border: activeTab === 'heatmap' ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
              color: activeTab === 'heatmap' ? '#818cf8' : '#94a3b8'
            }}
          >
            BKT Mastery Heatmap
          </button>
        </div>
      </div>

      {/* View 1: Topological Prerequisite Learning Path */}
      {activeTab === 'path' && (
        <div className="learning-path-section glass-panel animate-fade-in" style={{
          background: 'rgba(15, 23, 42, 0.65)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '24px',
          marginTop: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', color: '#f8fafc' }}>
                Prerequisite Learning Path (DAG Topological Order)
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#94a3b8' }}>
                Nodes unlock as you achieve ≥70% mastery on their prerequisite concepts.
              </p>
            </div>
            <button
              type="button"
              className="btn-accent"
              onClick={() => setQuizModal({ isOpen: true, conceptName: null })}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '6px 14px' }}
            >
              <Sparkles size={14} />
              <span>Practice Next Unlocked Concept</span>
            </button>
          </div>

          <div className="learning-path-timeline" style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            {learningPath.map((node, index) => {
              const isMastered = node.status === 'Mastered';
              const isInProgress = node.status === 'In Progress';
              const isReady = node.status === 'Ready to Learn';
              const isLocked = node.status === 'Locked';

              let badgeBg = 'rgba(255, 255, 255, 0.05)';
              let badgeColor = '#94a3b8';
              let border = '1px solid rgba(255, 255, 255, 0.06)';

              if (isMastered) {
                badgeBg = 'rgba(16, 185, 129, 0.15)';
                badgeColor = '#34d399';
                border = '1px solid rgba(16, 185, 129, 0.3)';
              } else if (isInProgress) {
                badgeBg = 'rgba(56, 189, 248, 0.15)';
                badgeColor = '#38bdf8';
                border = '1px solid rgba(56, 189, 248, 0.3)';
              } else if (isReady) {
                badgeBg = 'rgba(245, 158, 11, 0.15)';
                badgeColor = '#fbbf24';
                border = '1px solid rgba(245, 158, 11, 0.3)';
              }

              return (
                <div 
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    padding: '16px 20px',
                    borderRadius: '12px',
                    background: isLocked ? 'rgba(15, 23, 42, 0.3)' : 'rgba(255, 255, 255, 0.02)',
                    border,
                    opacity: isLocked ? 0.6 : 1,
                    transition: 'all 0.2s'
                  }}
                >
                  {/* Step Bubble */}
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '10px',
                    background: badgeBg,
                    color: badgeColor,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: '13px',
                    flexShrink: 0
                  }}>
                    {isMastered ? <CheckCircle2 size={18} /> : isLocked ? <Lock size={16} /> : index + 1}
                  </div>

                  {/* Concept Meta */}
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc' }}>
                        {node.concept_name}
                      </span>
                      {node.coarse_grained_category?.map((cat, ci) => (
                        <span key={ci} style={{
                          fontSize: '11px',
                          background: 'rgba(99, 102, 241, 0.12)',
                          color: '#818cf8',
                          padding: '1px 8px',
                          borderRadius: '12px'
                        }}>
                          {cat}
                        </span>
                      ))}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '6px', fontSize: '12px', color: '#94a3b8' }}>
                      {node.prerequisites && node.prerequisites.length > 0 ? (
                        <span>Prerequisites: <strong>{node.prerequisites.join(', ')}</strong></span>
                      ) : (
                        <span>Prerequisites: <em>None (Foundational)</em></span>
                      )}
                      <span>•</span>
                      <span>Mastery: <strong style={{ color: badgeColor }}>{node.mastery_percentage?.toFixed(1) || 10}%</strong></span>
                    </div>

                    {/* Linear Mastery Bar */}
                    <div style={{
                      width: '100%',
                      maxWidth: '240px',
                      height: '5px',
                      background: 'rgba(255, 255, 255, 0.08)',
                      borderRadius: '99px',
                      marginTop: '6px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${Math.min(100, Math.max(5, node.mastery_percentage || 10))}%`,
                        height: '100%',
                        background: isMastered ? '#10b981' : isInProgress ? '#38bdf8' : '#6366f1',
                        borderRadius: '99px'
                      }} />
                    </div>
                  </div>

                  {/* Status & Practice Button */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: '14px',
                      fontSize: '11px',
                      fontWeight: 600,
                      background: badgeBg,
                      color: badgeColor
                    }}>
                      {node.status}
                    </span>

                    {!isLocked && (
                      <button
                        type="button"
                        className="btn-accent"
                        onClick={() => setQuizModal({ isOpen: true, conceptName: node.concept_name })}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '12px',
                          padding: '6px 12px',
                          borderRadius: '8px'
                        }}
                      >
                        <Play size={12} />
                        <span>Practice</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* View 2: Course Content Materials */}
      {activeTab === 'materials' && (
        <div className="student-grid" style={{ marginTop: '16px' }}>
          <div className="student-materials-panel glass-panel">
            <div className="panel-title-bar">
              <div>
                <h3>Course Content & Lecture PDFs</h3>
                <p>Uploaded by course faculty</p>
              </div>
              <span className="badge-count">{selectedCourseMaterials.length} Documents</span>
            </div>

            <div className="student-docs-list">
              {selectedCourseMaterials.length === 0 ? (
                <div className="empty-sub-state">
                  <FileText size={32} />
                  <p>No materials uploaded for this course yet.</p>
                  <button type="button" className="btn-secondary-sm" onClick={onSwitchToTeacher}>
                    Upload as Teacher
                  </button>
                </div>
              ) : (
                selectedCourseMaterials.map((doc) => (
                  <div key={doc.id} className="student-doc-card">
                    <div className="doc-card-top">
                      <div className="doc-icon-badge">
                        <FileText size={18} />
                      </div>
                      <div className="doc-text-meta">
                        <h5>{doc.title}</h5>
                        <span className="doc-sub">{doc.fileName} • {doc.pages} pages</span>
                      </div>
                    </div>

                    <div className="concept-tags-row">
                      {doc.modules?.map((mod, i) => (
                        <span key={i} className="concept-chip">
                          {mod}
                        </span>
                      ))}
                      <span className="kg-chip">
                        <Share2 size={12} />
                        {doc.conceptsExtracted || 0} Graph Nodes
                      </span>
                    </div>

                    <div className="doc-actions-row">
                      <button 
                        type="button" 
                        className="explore-graph-btn"
                        onClick={() => setQuizModal({ isOpen: true, conceptName: doc.modules?.[0] || 'Lexical Analysis' })}
                      >
                        <Sparkles size={14} />
                        <span>Practice MCQs</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* View 3: BKT Mastery Heatmap */}
      {activeTab === 'heatmap' && (
        <div className="mastery-heatmap-panel glass-panel animate-fade-in" style={{
          background: 'rgba(15, 23, 42, 0.65)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '24px',
          marginTop: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', color: '#f8fafc' }}>
                Bayesian Knowledge Tracing (BKT) Latent Mastery Heatmap
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#94a3b8' }}>
                Mathematical student latent mastery $P(L_t) \in [0.01, 0.99]$ updated per quiz trial.
              </p>
            </div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#34d399' }}>
              Overall Mastery: {masteryData?.overall_mastery_percentage || 45.2}%
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '14px'
          }}>
            {learningPath.map((item, idx) => {
              const mastery = item.mastery_percentage || 10;
              let bg = 'rgba(239, 68, 68, 0.15)';
              let color = '#f87171';
              if (mastery >= 85) {
                bg = 'rgba(16, 185, 129, 0.2)';
                color = '#34d399';
              } else if (mastery >= 60) {
                bg = 'rgba(56, 189, 248, 0.2)';
                color = '#38bdf8';
              } else if (mastery >= 30) {
                bg = 'rgba(245, 158, 11, 0.2)';
                color = '#fbbf24';
              }

              return (
                <div 
                  key={idx}
                  style={{
                    background: bg,
                    border: `1px solid ${color}`,
                    borderRadius: '12px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    cursor: 'pointer'
                  }}
                  onClick={() => setQuizModal({ isOpen: true, conceptName: item.concept_name })}
                >
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
                    {item.concept_name}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>{item.status}</span>
                    <span style={{ fontSize: '15px', fontWeight: 700, color }}>
                      {mastery.toFixed(1)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Cognitive-RAG Adaptive Quiz Modal */}
      <CognitiveRagQuizModal 
        isOpen={quizModal.isOpen}
        onClose={() => setQuizModal({ isOpen: false, conceptName: null })}
        courseId={activeCourseTab}
        courseTitle={currentCourse.name || currentCourse.title}
        conceptName={quizModal.conceptName}
        onMasteryUpdated={handleMasteryUpdated}
      />
    </div>
  );
}
