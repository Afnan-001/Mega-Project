import React, { useState } from 'react';
import { 
  BookOpen, 
  Share2, 
  CheckCircle, 
  FileText, 
  Sparkles, 
  HelpCircle, 
  ExternalLink,
  Search,
  ArrowRight
} from 'lucide-react';

export default function StudentOverview({ materials, courses, onSwitchToTeacher }) {
  const [activeCourseTab, setActiveCourseTab] = useState(courses[0]?.id || 'ai402');
  const [selectedTopic, setSelectedTopic] = useState('Knowledge Representation');

  const selectedCourseMaterials = materials.filter(m => m.courseId === activeCourseTab);
  const currentCourse = courses.find(c => c.id === activeCourseTab) || courses[0];

  return (
    <div className="student-dashboard-content animate-fade-in">
      {/* Student Welcome Banner */}
      <div className="student-hero-banner glass-panel">
        <div className="hero-text-side">
          <div className="banner-badge">
            <Sparkles size={14} className="text-accent" />
            <span>Student Learning Portal</span>
          </div>
          <h2>Welcome back, Alex!</h2>
          <p>
            Explore AI-extracted knowledge graphs and course content uploaded by your professors. 
            All concepts are mapped directly from official course textbooks and lecture PDFs.
          </p>

          <div className="banner-stats-row">
            <div className="mini-stat">
              <span className="stat-num">{courses.length}</span>
              <span className="stat-label">Enrolled Courses</span>
            </div>
            <div className="mini-stat">
              <span className="stat-num">{materials.length}</span>
              <span className="stat-label">Available PDF Units</span>
            </div>
            <div className="mini-stat">
              <span className="stat-num">353</span>
              <span className="stat-label">Concepts Mastered</span>
            </div>
          </div>
        </div>

        <div className="hero-action-side">
          <div className="switch-role-prompt glass-panel">
            <h4>Are you a faculty member?</h4>
            <p>Upload syllabi and course PDFs from the Teacher Portal.</p>
            <button 
              type="button" 
              className="btn-accent"
              onClick={onSwitchToTeacher}
            >
              <span>Switch to Teacher Portal</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Course Navigation Pills */}
      <div className="course-tabs-selector">
        {courses.map((course) => (
          <button
            key={course.id}
            type="button"
            className={`course-tab-pill ${activeCourseTab === course.id ? 'active' : ''}`}
            onClick={() => setActiveCourseTab(course.id)}
          >
            <BookOpen size={16} />
            <span>{course.code}: {course.name}</span>
          </button>
        ))}
      </div>

      {/* Main Student Study Grid */}
      <div className="student-grid">
        {/* Left column: Available Course PDFs from Teacher */}
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
                    <button type="button" className="read-btn">
                      <span>View PDF Material</span>
                    </button>
                    <button 
                      type="button" 
                      className="explore-graph-btn"
                      onClick={() => setSelectedTopic(doc.modules?.[0] || 'Graph Concepts')}
                    >
                      <Share2 size={14} />
                      <span>Study Graph</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right column: Interactive Knowledge Concept Preview */}
        <div className="student-graph-panel glass-panel">
          <div className="panel-title-bar">
            <div>
              <h3>Hierarchical Concept Explorer</h3>
              <p>Interactive tree generated automatically from uploaded PDFs</p>
            </div>
            <span className="status-indicator-live">
              <span className="pulse-dot"></span> Live KG
            </span>
          </div>

          <div className="graph-preview-box">
            <div className="graph-active-node">
              <span className="node-type">Focus Concept</span>
              <h4>{selectedTopic}</h4>
              <p>Derived from Course Syllabus & Lecture Slides</p>
            </div>

            <div className="graph-nodes-visual">
              <div className="concept-tree">
                <div className="tree-node root">
                  <span className="node-dot"></span>
                  <span className="node-label">{currentCourse.name}</span>
                </div>
                <div className="tree-branch">
                  <div className="tree-node parent">
                    <span className="node-dot indigo"></span>
                    <span className="node-label">{selectedTopic}</span>
                  </div>
                  <div className="tree-children">
                    <div className="tree-node child">
                      <span className="node-dot cyan"></span>
                      <span>Entity Triples & Relations</span>
                    </div>
                    <div className="tree-node child">
                      <span className="node-dot purple"></span>
                      <span>Semantic Embeddings</span>
                    </div>
                    <div className="tree-node child">
                      <span className="node-dot emerald"></span>
                      <span>Prerequisites & Mastery</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="study-ai-prompt">
              <div className="ai-prompt-header">
                <Sparkles size={16} className="text-accent" />
                <span>Ask AI Tutor about this concept</span>
              </div>
              <div className="ai-quick-input">
                <input 
                  type="text" 
                  placeholder={`"Explain ${selectedTopic} with an example from the PDF..."`}
                  readOnly 
                />
                <button type="button" className="ask-submit-btn">Ask</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
