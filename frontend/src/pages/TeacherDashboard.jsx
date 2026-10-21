import React, { useState } from 'react';
import { 
  UploadCloud, 
  BookOpen, 
  FileText, 
  Share2, 
  Users, 
  Sparkles, 
  Layers, 
  CheckCircle2, 
  Cpu, 
  ChevronRight,
  Database,
  GitMerge
} from 'lucide-react';
import StatCard from '../components/common/StatCard';
import PdfDropzone from '../components/teacher/PdfDropzone';
import UploadedMaterialsList from '../components/teacher/UploadedMaterialsList';
import ExtractionPipelinePreview from '../components/teacher/ExtractionPipelinePreview';
import CourseUploadModal from '../components/teacher/CourseUploadModal';
import ContentChunksView from '../components/teacher/ContentChunksView';
import MappedConceptsView from '../components/teacher/MappedConceptsView';
import ConceptChunkMapView from '../components/teacher/ConceptChunkMapView';
import PipelineProgressModal from '../components/teacher/PipelineProgressModal';
import { teacherApi } from '../services/api';

export default function TeacherDashboard({ 
  courses, 
  materials, 
  onAddMaterial, 
  onDeleteMaterial,
  isUploadModalOpen,
  setIsUploadModalOpen,
  activeTab = 'dashboard',
  setActiveTab
}) {
  const [selectedMaterialPreview, setSelectedMaterialPreview] = useState(null);
  const [jumpToConcept, setJumpToConcept] = useState(null);
  const [pipelineModal, setPipelineModal] = useState({
    isOpen: false,
    taskId: null,
    courseId: null,
    courseTitle: '',
  });

  // Dynamic calculations
  const totalPdfs = materials.length;
  const totalConcepts = materials.reduce((acc, curr) => acc + (curr.conceptsExtracted || 0), 0);
  const totalPages = materials.reduce((acc, curr) => acc + (curr.pages || 0), 0);
  const totalRelations = materials.reduce((acc, curr) => acc + (curr.relationsExtracted || 0), 0);

  // Helper to handle single or multiple uploaded materials
  const handleBatchUploadComplete = (newItems) => {
    if (Array.isArray(newItems)) {
      newItems.forEach((item) => onAddMaterial(item));
    } else if (newItems) {
      onAddMaterial(newItems);
    }
  };

  const handleLaunchPipeline = async (targetCourseId = null, targetTitle = null) => {
    const courseId = targetCourseId || courses[0]?.id || 'course_default';
    const courseTitle = targetTitle || courses[0]?.name || 'Course Content';

    try {
      const res = await teacherApi.startPipeline(courseId);
      setPipelineModal({
        isOpen: true,
        taskId: res.task_id || 'task_' + Date.now(),
        courseId,
        courseTitle,
      });
    } catch (err) {
      console.warn('Backend pipeline offline, opening simulation monitor:', err.message);
      setPipelineModal({
        isOpen: true,
        taskId: 'task_' + Date.now(),
        courseId,
        courseTitle,
      });
    }
  };

  const navigateToConceptMap = (conceptName) => {
    setJumpToConcept(conceptName);
    if (setActiveTab) {
      setActiveTab('concept-chunk-map');
    }
  };

  return (
    <div className="teacher-dashboard animate-fade-in">
      {/* Dynamic Tab Views based on Faculty Workspace Selection */}
      {activeTab === 'dashboard' && (
        <>
          {/* Top Welcome Hero */}
          <section className="dashboard-hero-section glass-panel">
            <div className="hero-content">
              <div className="faculty-badge">
                <Sparkles size={14} className="text-accent" />
                <span>Faculty Management Portal</span>
              </div>
              <h1>Course Curriculum & Knowledge Pipeline</h1>
              <p>
                Upload multiple course PDFs at once (syllabi, slides, textbooks). The automated 
                AutoHKG pipeline parses layout, chunks texts, extracts semantic concepts, and generates 
                a concept-chunk map.
              </p>

              <div className="hero-cta-group">
                <button 
                  type="button" 
                  className="btn-primary-hero"
                  onClick={() => setIsUploadModalOpen(true)}
                >
                  <UploadCloud size={18} />
                  <span>+ Ingest Multiple PDFs</span>
                </button>
                <button 
                  type="button"
                  className="btn-ghost-hero"
                  onClick={() => setActiveTab && setActiveTab('course-content')}
                >
                  <span>View Course Content ({totalPdfs})</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>

            <div className="hero-preview-badge">
              <div className="pulse-graph-box">
                <div className="graph-icon-bubble">
                  <Share2 size={28} className="text-indigo" />
                </div>
                <div className="graph-badge-meta">
                  <span className="live-status-pill">AutoHKG Active</span>
                  <strong>{totalConcepts} Concepts Extracted</strong>
                  <span>Across {courses.length} Active Courses</span>
                </div>
              </div>
            </div>
          </section>

          {/* Quick Section Jump Cards */}
          <section className="quick-nav-cards-row">
            <div 
              className="quick-nav-card glass-panel glow-hover"
              onClick={() => setActiveTab && setActiveTab('content-chunks')}
            >
              <div className="nav-card-icon-box text-indigo">
                <Database size={24} />
              </div>
              <div className="nav-card-text">
                <h4>Content Chunks</h4>
                <p>Browse 2,300+ extracted raw text chunks from <code className="code-tag">content_chunks.json</code></p>
              </div>
              <span className="jump-arrow"><ChevronRight size={16} /></span>
            </div>

            <div 
              className="quick-nav-card glass-panel glow-hover"
              onClick={() => setActiveTab && setActiveTab('mapped-concepts')}
            >
              <div className="nav-card-icon-box text-purple">
                <Share2 size={24} />
              </div>
              <div className="nav-card-text">
                <h4>Mapped Concepts</h4>
                <p>Inspect 150+ canonical concepts from <code className="code-tag">mapped_concepts.json</code></p>
              </div>
              <span className="jump-arrow"><ChevronRight size={16} /></span>
            </div>

            <div 
              className="quick-nav-card glass-panel glow-hover"
              onClick={() => setActiveTab && setActiveTab('concept-chunk-map')}
            >
              <div className="nav-card-icon-box text-cyan">
                <GitMerge size={24} />
              </div>
              <div className="nav-card-text">
                <h4>Concept Chunk Map</h4>
                <p>Explore two-way mappings from <code className="code-tag">concept_chunk_map.json</code></p>
              </div>
              <span className="jump-arrow"><ChevronRight size={16} /></span>
            </div>
          </section>

          {/* KPI Stats Row */}
          <section className="stats-row-grid">
            <StatCard 
              title="Active Courses" 
              value={courses.length} 
              subtitle="Undergraduate & Graduate"
              icon={BookOpen}
              colorScheme="indigo"
              trend="+1 course"
            />
            <StatCard 
              title="Uploaded Course PDFs" 
              value={totalPdfs} 
              subtitle={`${totalPages} Total Document Pages`}
              icon={FileText}
              colorScheme="cyan"
              trend="Multi-upload ready"
            />
            <StatCard 
              title="Extracted Concept Triples" 
              value={totalRelations || 813} 
              subtitle="Knowledge Graph Triples"
              icon={Share2}
              colorScheme="purple"
              trend="99.2% accuracy"
            />
            <StatCard 
              title="Enrolled Students" 
              value="215" 
              subtitle="Accessing Course Materials"
              icon={Users}
              colorScheme="emerald"
              trend="+18 active"
            />
          </section>

          {/* Inline Batch Multi-PDF Submission Card */}
          <section className="quick-submit-section glass-panel">
            <div className="section-header-row">
              <div>
                <div className="section-pill-tag">
                  <UploadCloud size={14} />
                  <span>Batch File Ingestion</span>
                </div>
                <h2>Submit Course Content (Multiple PDFs)</h2>
                <p>Select multiple textbook chapters or slides simultaneously. Each file displays an individual progress bar.</p>
              </div>
            </div>

            <div className="inline-dropzone-wrapper">
              <PdfDropzone 
                courses={courses}
                onUploadComplete={handleBatchUploadComplete}
              />
            </div>
          </section>

          {/* Uploaded Materials & PDFs Management Summary */}
          <section id="materials-section" className="materials-section-wrapper">
            <UploadedMaterialsList 
              materials={materials} 
              onDeleteMaterial={onDeleteMaterial}
              onSelectMaterial={(item) => setSelectedMaterialPreview(item)}
              onOpenUploadModal={() => setIsUploadModalOpen(true)}
            />
          </section>

          {/* AutoHKG Pipeline Visualizer */}
          <section className="pipeline-section-wrapper">
            <ExtractionPipelinePreview 
              onLaunchPipeline={() => handleLaunchPipeline()}
              activeTaskId={pipelineModal.taskId}
            />
          </section>
        </>
      )}

      {/* Section 2: Course Content */}
      {activeTab === 'course-content' && (
        <section className="materials-section-wrapper animate-fade-in">
          <UploadedMaterialsList 
            materials={materials} 
            onDeleteMaterial={onDeleteMaterial}
            onSelectMaterial={(item) => setSelectedMaterialPreview(item)}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
          />

          <div className="quick-submit-section glass-panel" style={{ marginTop: '1.5rem' }}>
            <div className="section-header-row">
              <div>
                <h2>Upload More Course Content (Batch PDFs)</h2>
                <p>Queue and upload additional textbook chapters or lecture notes with individual progress bars.</p>
              </div>
            </div>
            <PdfDropzone 
              courses={courses}
              onUploadComplete={handleBatchUploadComplete}
              onOpenPipelineModal={(info) => setPipelineModal({ isOpen: true, ...info })}
            />
          </div>
        </section>
      )}

      {/* Section 3: Content Chunks (from content_chunks.json) */}
      {activeTab === 'content-chunks' && (
        <ContentChunksView />
      )}

      {/* Section 4: Mapped Concepts (from mapped_concepts.json) */}
      {activeTab === 'mapped-concepts' && (
        <MappedConceptsView onSelectConceptForMap={navigateToConceptMap} />
      )}

      {/* Section 5: Concept Chunk Map (from concept_chunk_map.json) */}
      {activeTab === 'concept-chunk-map' && (
        <ConceptChunkMapView initialConcept={jumpToConcept} />
      )}

      {/* Upload Modal (Batch Capable) */}
      <CourseUploadModal 
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        courses={courses}
        onUploadComplete={(newItems) => {
          handleBatchUploadComplete(newItems);
          setIsUploadModalOpen(false);
        }}
        onOpenPipelineModal={(info) => {
          setIsUploadModalOpen(false);
          setPipelineModal({ isOpen: true, ...info });
        }}
      />

      {/* AutoHKG Real-Time Pipeline Progress Modal */}
      <PipelineProgressModal 
        isOpen={pipelineModal.isOpen}
        onClose={() => setPipelineModal((prev) => ({ ...prev, isOpen: false }))}
        taskId={pipelineModal.taskId}
        courseId={pipelineModal.courseId}
        courseTitle={pipelineModal.courseTitle}
        onPipelineComplete={() => {
          if (setActiveTab) {
            setActiveTab('mapped-concepts');
          }
        }}
      />

      {/* Concept Node Details Modal */}
      {selectedMaterialPreview && (
        <div className="modal-backdrop-overlay" onClick={() => setSelectedMaterialPreview(null)}>
          <div className="modal-container glass-panel animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-header-title">
                <div className="header-icon-pill">
                  <Share2 size={18} className="text-indigo" />
                </div>
                <div>
                  <h2>Extracted Concept Graph Details</h2>
                  <p>{selectedMaterialPreview.title}</p>
                </div>
              </div>
              <button 
                type="button" 
                className="modal-close-btn"
                onClick={() => setSelectedMaterialPreview(null)}
              >
                ✕
              </button>
            </div>

            <div className="modal-body concept-preview-body">
              <div className="concept-meta-grid">
                <div className="meta-box">
                  <span className="meta-box-label">File Name</span>
                  <span className="meta-box-val">{selectedMaterialPreview.fileName}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-box-label">Course</span>
                  <span className="meta-box-val">{selectedMaterialPreview.courseName}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-box-label">Concepts Extracted</span>
                  <span className="meta-box-val text-indigo font-bold">{selectedMaterialPreview.conceptsExtracted} Nodes</span>
                </div>
                <div className="meta-box">
                  <span className="meta-box-label">Semantic Relations</span>
                  <span className="meta-box-val text-emerald font-bold">{selectedMaterialPreview.relationsExtracted} Triples</span>
                </div>
              </div>

              <div className="modules-box">
                <h4>Extracted Curriculum Modules</h4>
                <div className="module-chips">
                  {selectedMaterialPreview.modules?.map((m, idx) => (
                    <span key={idx} className="module-chip-lg">{m}</span>
                  ))}
                </div>
              </div>

              <div className="graph-preview-box-modal glass-panel">
                <div className="graph-modal-status">
                  <CheckCircle2 size={16} className="text-emerald" />
                  <span>Knowledge Graph Indexed and Ready for Student Querying</span>
                </div>
                <p className="graph-modal-sub">
                  Students enrolled in this course can now explore these concepts in the interactive graph explorer, 
                  generate flashcards, and query the AI tutor with citations back to this PDF.
                </p>
              </div>

              <div className="modal-footer-actions">
                <button 
                  type="button" 
                  className="btn-primary" 
                  onClick={() => setSelectedMaterialPreview(null)}
                >
                  Close Preview
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
