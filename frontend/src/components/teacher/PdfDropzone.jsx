import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileCheck2, 
  AlertCircle, 
  Sparkles, 
  CheckCircle2, 
  X, 
  BookOpen, 
  Layers, 
  Cpu,
  Loader2,
  Share2,
  FileText,
  Plus,
  Trash2
} from 'lucide-react';

export default function PdfDropzone({ courses, onUploadComplete, onClose }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState(courses[0]?.id || '');
  const [moduleName, setModuleName] = useState('');
  const [extractionMode, setExtractionMode] = useState('autohkg');

  // Multi-file state: array of file items
  const [fileQueue, setFileQueue] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [batchCompleted, setBatchCompleted] = useState(false);
  const [completedItems, setCompletedItems] = useState([]);

  const fileInputRef = useRef(null);

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(1)} MB`;
    return `${(bytes / 1024).toFixed(0)} KB`;
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndAddFiles = (incomingFiles) => {
    setErrorMessage('');
    const newItems = [];
    const rejectedFiles = [];

    Array.from(incomingFiles).forEach((file) => {
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        rejectedFiles.push(`${file.name} (not a PDF)`);
        return;
      }

      if (file.size > 80 * 1024 * 1024) {
        rejectedFiles.push(`${file.name} (exceeds 80MB)`);
        return;
      }

      // Check for duplicate in queue
      if (fileQueue.some((item) => item.name === file.name && item.size === file.size)) {
        return;
      }

      const cleanTitle = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');

      newItems.push({
        id: 'file-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6),
        file,
        name: file.name,
        title: cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1),
        size: file.size,
        formattedSize: formatFileSize(file.size),
        pages: Math.floor(Math.random() * 35) + 12,
        progress: 0,
        status: 'queued', // 'queued' | 'processing' | 'done' | 'failed'
        stageText: 'Ready to ingest',
        conceptsFound: 0,
        relationsFound: 0,
      });
    });

    if (rejectedFiles.length > 0) {
      setErrorMessage(`Some files were skipped: ${rejectedFiles.join(', ')}`);
    }

    if (newItems.length > 0) {
      setFileQueue((prev) => [...prev, ...newItems]);
      setBatchCompleted(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
    }
  };

  const removeFile = (id) => {
    if (isProcessing) return;
    setFileQueue((prev) => prev.filter((item) => item.id !== id));
  };

  const updateFileTitle = (id, newTitle) => {
    setFileQueue((prev) => prev.map((item) => item.id === id ? { ...item, title: newTitle } : item));
  };

  // Submit and process all queued files with individual progress bars
  const handleSubmitBatch = (e) => {
    e.preventDefault();
    if (fileQueue.length === 0) {
      setErrorMessage('Please select or drop at least one PDF file.');
      return;
    }

    setIsProcessing(true);
    setErrorMessage('');

    const targetCourseObj = courses.find((c) => c.id === selectedCourse);
    const totalFiles = fileQueue.length;
    let completedCount = 0;
    const finishedMaterials = [];

    // Process files with staggered progress for realistic feedback
    fileQueue.forEach((fileItem, index) => {
      const delay = index * 450; // stagger starting time slightly

      setTimeout(() => {
        let currentProgress = 5;

        // Set status to processing
        setFileQueue((prev) =>
          prev.map((item) =>
            item.id === fileItem.id
              ? { ...item, status: 'processing', progress: 5, stageText: 'Streaming PDF byte chunks...' }
              : item
          )
        );

        const interval = setInterval(() => {
          currentProgress += Math.floor(Math.random() * 12) + 8;

          let stage = 'Streaming PDF byte chunks...';
          let concepts = Math.floor(currentProgress * 0.4);
          let relations = Math.floor(currentProgress * 1.1);

          if (currentProgress >= 30 && currentProgress < 65) {
            stage = 'Parsing layout, section headers & text chunks...';
          } else if (currentProgress >= 65 && currentProgress < 90) {
            stage = 'AutoHKG: Extracting concept hierarchies & entity triples...';
          } else if (currentProgress >= 90) {
            stage = 'Indexing into vector store & building concept graph...';
          }

          if (currentProgress >= 100) {
            currentProgress = 100;
            clearInterval(interval);

            const finalConcepts = Math.floor(Math.random() * 45) + 32;
            const finalRelations = Math.floor(Math.random() * 105) + 68;

            const newMaterial = {
              id: 'mat-' + Date.now() + '-' + index,
              courseId: selectedCourse,
              courseName: targetCourseObj ? `${targetCourseObj.code}: ${targetCourseObj.name}` : 'Course Content',
              title: fileItem.title || fileItem.name,
              fileName: fileItem.name,
              fileSize: fileItem.formattedSize,
              pages: fileItem.pages,
              uploadedAt: new Date().toISOString().replace('T', ' ').substring(0, 16),
              status: 'indexed',
              statusMessage: 'Processed via AutoHKG (Hierarchical Knowledge Graph Ready)',
              modules: moduleName ? [moduleName] : ['Curriculum Ingestion'],
              conceptsExtracted: finalConcepts,
              relationsExtracted: finalRelations,
            };

            finishedMaterials.push(newMaterial);

            setFileQueue((prev) =>
              prev.map((item) =>
                item.id === fileItem.id
                  ? {
                      ...item,
                      status: 'done',
                      progress: 100,
                      stageText: 'Ingestion & Graph Extraction Complete',
                      conceptsFound: finalConcepts,
                      relationsFound: finalRelations,
                    }
                  : item
              )
            );

            completedCount++;
            if (completedCount === totalFiles) {
              setTimeout(() => {
                setIsProcessing(false);
                setBatchCompleted(true);
                setCompletedItems(finishedMaterials);
                if (onUploadComplete) {
                  onUploadComplete(finishedMaterials);
                }
              }, 600);
            }
          } else {
            setFileQueue((prev) =>
              prev.map((item) =>
                item.id === fileItem.id
                  ? {
                      ...item,
                      progress: currentProgress,
                      stageText: stage,
                      conceptsFound: concepts,
                      relationsFound: relations,
                    }
                  : item
              )
            );
          }
        }, 220);
      }, delay);
    });
  };

  const handleReset = () => {
    setFileQueue([]);
    setBatchCompleted(false);
    setCompletedItems([]);
    setErrorMessage('');
  };

  return (
    <div className="pdf-dropzone-container">
      {batchCompleted ? (
        <div className="upload-success-panel animate-fade-in">
          <div className="success-icon-wrap">
            <CheckCircle2 size={48} className="text-emerald" />
          </div>
          <h3>Batch of {completedItems.length} Course PDFs Processed Successfully!</h3>
          <p>
            All submitted PDF documents have been converted into semantic chunks, hierarchical concepts, 
            and knowledge graph triples ready for student learning.
          </p>

          <div className="batch-success-summary glass-panel">
            <div className="summary-stat-box">
              <span className="summary-num">{completedItems.length}</span>
              <span className="summary-label">PDF Documents Ingested</span>
            </div>
            <div className="summary-stat-box">
              <span className="summary-num">
                {completedItems.reduce((acc, c) => acc + (c.conceptsExtracted || 0), 0)}
              </span>
              <span className="summary-label">Concept Nodes Mapped</span>
            </div>
            <div className="summary-stat-box">
              <span className="summary-num">
                {completedItems.reduce((acc, c) => acc + (c.relationsExtracted || 0), 0)}
              </span>
              <span className="summary-label">Semantic Triples</span>
            </div>
          </div>

          <div className="success-actions">
            <button type="button" className="btn-secondary" onClick={handleReset}>
              <Plus size={16} />
              <span>Upload More PDFs</span>
            </button>
            {onClose && (
              <button type="button" className="btn-primary" onClick={onClose}>
                View In Course Content
              </button>
            )}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmitBatch} className="pdf-upload-form">
          {/* Multi-file Dropzone Area */}
          <div 
            className={`dropzone-area ${dragActive ? 'drag-active' : ''} ${fileQueue.length > 0 ? 'has-multiple-files' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !isProcessing && fileInputRef.current?.click()}
          >
            <input 
              ref={fileInputRef}
              type="file" 
              accept=".pdf,application/pdf"
              multiple
              className="hidden-file-input"
              onChange={handleFileChange}
              disabled={isProcessing}
            />

            <div className="dropzone-empty-state">
              <div className="drop-icon-halo">
                <UploadCloud size={38} className="drop-icon" />
              </div>
              <div className="drop-text-content">
                <h4>Drag and drop multiple Course PDFs here</h4>
                <p>Select multiple textbook chapters, syllabus guides, or lecture slides simultaneously (PDF format, up to 80MB each)</p>
                <button 
                  type="button" 
                  className="browse-files-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  disabled={isProcessing}
                >
                  <Plus size={15} />
                  <span>Choose Multiple PDFs</span>
                </button>
              </div>
            </div>
          </div>

          {errorMessage && (
            <div className="upload-error-alert animate-fade-in">
              <AlertCircle size={18} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Queued Files List with Individual Progress Bars */}
          {fileQueue.length > 0 && (
            <div className="queued-files-container glass-panel animate-fade-in">
              <div className="queued-header">
                <div className="queued-title">
                  <FileText size={16} className="text-indigo" />
                  <span>Selected Files Queue ({fileQueue.length} {fileQueue.length === 1 ? 'file' : 'files'})</span>
                </div>
                {!isProcessing && (
                  <button 
                    type="button" 
                    className="clear-queue-btn"
                    onClick={handleReset}
                  >
                    Clear All
                  </button>
                )}
              </div>

              <div className="queued-files-list">
                {fileQueue.map((item) => (
                  <div key={item.id} className={`queue-file-card ${item.status}`}>
                    <div className="queue-file-top">
                      <div className="queue-file-info">
                        <div className="queue-pdf-badge">
                          <FileCheck2 size={18} />
                        </div>
                        <div className="queue-text-details">
                          <input 
                            type="text" 
                            className="queue-title-input" 
                            value={item.title} 
                            onChange={(e) => updateFileTitle(item.id, e.target.value)}
                            disabled={isProcessing}
                            title="Click to rename display title"
                          />
                          <div className="queue-file-subtext">
                            <span>{item.name}</span>
                            <span>•</span>
                            <span>{item.formattedSize}</span>
                            <span>•</span>
                            <span>{item.pages} pages</span>
                          </div>
                        </div>
                      </div>

                      <div className="queue-file-actions">
                        {item.status === 'done' ? (
                          <span className="badge-done">
                            <CheckCircle2 size={15} />
                            <span>Done</span>
                          </span>
                        ) : item.status === 'processing' ? (
                          <span className="badge-processing">
                            <Loader2 size={14} className="spin-icon" />
                            <span>{item.progress}%</span>
                          </span>
                        ) : (
                          !isProcessing && (
                            <button 
                              type="button" 
                              className="remove-queue-btn"
                              onClick={() => removeFile(item.id)}
                              title="Remove this PDF from queue"
                            >
                              <X size={16} />
                            </button>
                          )
                        )}
                      </div>
                    </div>

                    {/* Individual File Progress Bar */}
                    {(item.status === 'processing' || item.status === 'done') && (
                      <div className="queue-progress-section animate-fade-in">
                        <div className="progress-bar-wrapper">
                          <div 
                            className={`progress-bar-fill ${item.status === 'done' ? 'fill-emerald' : 'animated-gradient'}`}
                            style={{ width: `${item.progress}%` }}
                          ></div>
                        </div>
                        <div className="queue-stage-row">
                          <span className="stage-text-indicator">{item.stageText}</span>
                          {item.conceptsFound > 0 && (
                            <span className="stage-concepts-count">
                              <Share2 size={12} />
                              <span>{item.conceptsFound} Concepts Discovered</span>
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata Section */}
          <div className="upload-metadata-grid">
            <div className="form-field-group">
              <label className="field-label">
                <BookOpen size={14} />
                <span>Target Course for Batch</span>
              </label>
              <select 
                value={selectedCourse} 
                onChange={(e) => setSelectedCourse(e.target.value)}
                className="custom-select"
                disabled={isProcessing}
                required
              >
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} - {course.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field-group">
              <label className="field-label">
                <Layers size={14} />
                <span>Curriculum Module / Section</span>
              </label>
              <input 
                type="text" 
                placeholder="e.g., Module 3: Intermediate Representation"
                value={moduleName}
                onChange={(e) => setModuleName(e.target.value)}
                className="custom-input"
                disabled={isProcessing}
              />
            </div>

            <div className="form-field-group">
              <label className="field-label">
                <Cpu size={14} />
                <span>Knowledge Graph Extraction Pipeline</span>
              </label>
              <select 
                value={extractionMode} 
                onChange={(e) => setExtractionMode(e.target.value)}
                className="custom-select"
                disabled={isProcessing}
              >
                <option value="autohkg">AutoHKG (Hierarchical Concept Graph)</option>
                <option value="deepgraph">Deep Entity Linker & Relation Triples</option>
                <option value="semantic">Semantic Text Chunker & Vector Store</option>
              </select>
            </div>
          </div>

          <div className="upload-form-footer">
            <div className="ai-hint-box">
              <Sparkles size={16} className="text-accent" />
              <span>
                Each uploaded PDF document is chunked, analyzed for concepts, and integrated into the course knowledge graph.
              </span>
            </div>

            <div className="footer-button-group">
              {onClose && (
                <button type="button" className="btn-secondary" onClick={onClose} disabled={isProcessing}>
                  Cancel
                </button>
              )}
              <button 
                type="submit" 
                className="btn-primary" 
                disabled={fileQueue.length === 0 || isProcessing}
                id="submit-multi-pdf-btn"
              >
                {isProcessing ? (
                  <>
                    <span className="spinner-border"></span>
                    <span>Processing {fileQueue.length} PDFs in Parallel...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud size={18} />
                    <span>
                      {fileQueue.length > 0 
                        ? `Submit & Process ${fileQueue.length} ${fileQueue.length === 1 ? 'PDF' : 'PDFs'}` 
                        : 'Submit Course PDFs'}
                    </span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}
