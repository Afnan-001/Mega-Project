import React from 'react';
import { FileUp, Cpu, Share2, Sparkles, CheckCircle2 } from 'lucide-react';

export default function ExtractionPipelinePreview() {
  const steps = [
    {
      num: '01',
      title: 'Teacher PDF Submission',
      desc: 'Syllabus, textbooks, slide decks, or lecture notes are uploaded through the dashboard.',
      icon: FileUp,
      status: 'Active'
    },
    {
      num: '02',
      title: 'AutoHKG Hierarchy Extraction',
      desc: 'Our model analyzes document semantics, identifying root concepts, subtopics, and prerequisites.',
      icon: Cpu,
      status: 'Integrated'
    },
    {
      num: '03',
      title: 'Concept & Relation Graph',
      desc: 'Entities are linked into a navigable multi-dimensional graph with semantic triples.',
      icon: Share2,
      status: 'Ready'
    },
    {
      num: '04',
      title: 'Student Interactive Learning',
      desc: 'Students interact with concept maps, personalized flashcards, and graph-guided AI explanations.',
      icon: Sparkles,
      status: 'Synchronized'
    }
  ];

  return (
    <div className="pipeline-preview-card glass-panel">
      <div className="pipeline-header">
        <div className="pipeline-title-group">
          <span className="pipeline-badge">AI Knowledge Pipeline Workflow</span>
          <h3>How Teacher Course Content Becomes Interactive Knowledge</h3>
        </div>
        <div className="pipeline-status-tag">
          <span className="dot-green"></span>
          <span>Pipeline Online</span>
        </div>
      </div>

      <div className="pipeline-steps-grid">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          return (
            <div key={idx} className="pipeline-step-item">
              <div className="step-num-bubble">{step.num}</div>
              <div className="step-card-box">
                <div className="step-icon-wrapper">
                  <Icon size={20} />
                </div>
                <div className="step-title">{step.title}</div>
                <div className="step-desc">{step.desc}</div>
                <div className="step-footer">
                  <CheckCircle2 size={12} className="text-emerald" />
                  <span>{step.status}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
