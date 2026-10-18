import React from 'react';
import { X, Sparkles, BookOpen } from 'lucide-react';
import PdfDropzone from './PdfDropzone';

export default function CourseUploadModal({ isOpen, onClose, courses, onUploadComplete }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop-overlay" onClick={onClose}>
      <div 
        className="modal-container glass-panel animate-fade-in" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div className="modal-header-title">
            <div className="header-icon-pill">
              <Sparkles size={18} className="text-accent" />
            </div>
            <div>
              <h2>Submit Course Content (PDF)</h2>
              <p>Upload lecture slides, chapters, or syllabus documents to generate knowledge graphs</p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <PdfDropzone 
            courses={courses} 
            onUploadComplete={(newMat) => {
              onUploadComplete(newMat);
            }}
            onClose={onClose}
          />
        </div>
      </div>
    </div>
  );
}
