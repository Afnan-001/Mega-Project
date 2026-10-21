import React from 'react';
import { 
  FileText, 
  Cpu, 
  Sparkles, 
  Database, 
  GitMerge, 
  Layers, 
  Share2, 
  CheckCircle2, 
  Play, 
  Activity 
} from 'lucide-react';
import { PIPELINE_STAGES } from './PipelineProgressModal';

export default function ExtractionPipelinePreview({ onLaunchPipeline, activeTaskId }) {
  return (
    <div className="pipeline-preview-card glass-panel" style={{
      background: 'rgba(15, 23, 42, 0.7)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      padding: '24px',
      borderRadius: '16px',
      marginBottom: '24px'
    }}>
      <div className="pipeline-header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
        marginBottom: '20px'
      }}>
        <div className="pipeline-title-group">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="pipeline-badge" style={{
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#818cf8',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              padding: '2px 10px',
              borderRadius: '20px',
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase'
            }}>
              7-Stage AutoHKG Architecture
            </span>
            <span style={{ fontSize: '12px', color: '#64748b' }}>FastAPI Background Task Engine</span>
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            Automated Knowledge Graph Extraction Pipeline
          </h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="pipeline-status-tag" style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            color: '#10b981'
          }}>
            <span className="dot-green" style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#10b981',
              boxShadow: '0 0 8px #10b981'
            }}></span>
            <span>FastAPI Runner Ready</span>
          </div>

          {onLaunchPipeline && (
            <button
              type="button"
              className="btn-accent"
              onClick={onLaunchPipeline}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '7px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <Activity size={15} />
              <span>{activeTaskId ? 'View Live Pipeline Progress' : 'Start AutoHKG Pipeline'}</span>
            </button>
          )}
        </div>
      </div>

      {/* 7 Horizontal Pipeline Step Chips */}
      <div className="pipeline-steps-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '12px'
      }}>
        {PIPELINE_STAGES.map((step, idx) => {
          const Icon = step.icon;
          return (
            <div 
              key={step.key} 
              className="pipeline-step-item"
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '12px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'transform 0.2s, border-color 0.2s',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '7px',
                    background: 'rgba(99, 102, 241, 0.15)',
                    color: '#818cf8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Icon size={15} />
                  </div>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#475569' }}>
                    {step.num}
                  </span>
                </div>

                <div style={{ fontSize: '13px', fontWeight: 600, color: '#e2e8f0', marginBottom: '4px' }}>
                  {step.label}
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', lineHeight: 1.4 }}>
                  {step.desc}
                </div>
              </div>

              <div style={{
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: '1px solid rgba(255, 255, 255, 0.04)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: '#10b981'
              }}>
                <CheckCircle2 size={12} />
                <span>Stage Verified</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
