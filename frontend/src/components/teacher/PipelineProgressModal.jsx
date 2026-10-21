import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  Cpu, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  Share2, 
  Sparkles, 
  Loader2, 
  Terminal, 
  ArrowRight,
  Database,
  GitMerge,
  Filter
} from 'lucide-react';
import { teacherApi } from '../../services/api';

export const PIPELINE_STAGES = [
  {
    key: 'CHUNKING',
    num: '01',
    label: 'Document Chunking',
    desc: 'Extracting text and generating page-grounded text chunks',
    icon: FileText,
  },
  {
    key: 'NLP_CONCEPTS',
    num: '02',
    label: 'NLP Concept Extraction',
    desc: 'Noun-chunk & noun phrase heuristic extraction',
    icon: Filter,
  },
  {
    key: 'LLM_CLEANING',
    num: '03',
    label: 'LLM Concept Cleaning',
    desc: 'Deduplicating and canonicalizing academic concepts',
    icon: Sparkles,
  },
  {
    key: 'EMBEDDING',
    num: '04',
    label: 'Dense Embeddings',
    desc: 'Encoding chunks into dense vector representations',
    icon: Database,
  },
  {
    key: 'MAPPING',
    num: '05',
    label: 'Semantic Chunk Mapping',
    desc: 'Calculating cosine similarity and evidence grounding',
    icon: GitMerge,
  },
  {
    key: 'ENRICHMENT',
    num: '06',
    label: 'Prerequisite Enrichment',
    desc: 'Discovering coarse categories & citation-backed dependencies',
    icon: Layers,
  },
  {
    key: 'DAG_RESOLVE',
    num: '07',
    label: 'Cycle-Free DAG Resolution',
    desc: 'Removing feedback loops to produce topological learning paths',
    icon: Share2,
  },
];

export default function PipelineProgressModal({ 
  isOpen, 
  onClose, 
  taskId, 
  courseId, 
  courseTitle = 'Course Textbook',
  onPipelineComplete 
}) {
  const [pipelineState, setPipelineState] = useState({
    status: 'running', // queued | running | completed | failed
    currentStage: 'CHUNKING',
    progressPercentage: 5,
    stageDetails: {},
    logs: ['[System] Initiating AutoHKG knowledge graph pipeline...'],
    errorMessage: null,
  });

  const [activeTab, setActiveTab] = useState('stages'); // 'stages' | 'logs'
  const logTerminalRef = useRef(null);
  const pollIntervalRef = useRef(null);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logTerminalRef.current) {
      logTerminalRef.current.scrollTop = logTerminalRef.current.scrollHeight;
    }
  }, [pipelineState.logs]);

  // Real-time polling
  useEffect(() => {
    if (!isOpen || !taskId) return;

    let isSubscribed = true;

    async function pollStatus() {
      try {
        const data = await teacherApi.getPipelineStatus(taskId);
        if (!isSubscribed) return;

        const currentStage = data.current_stage || 'CHUNKING';
        const progress = Math.min(100, Math.max(0, data.progress_percentage || 0));

        setPipelineState({
          status: data.status,
          currentStage,
          progressPercentage: progress,
          stageDetails: data.stage_details || {},
          logs: data.logs && data.logs.length > 0 ? data.logs : ['[AutoHKG] Processing pipeline stages...'],
          errorMessage: data.error_message,
        });

        if (data.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          if (onPipelineComplete) {
            onPipelineComplete({ courseId, taskId, data });
          }
        } else if (data.status === 'failed') {
          clearInterval(pollIntervalRef.current);
        }
      } catch (err) {
        console.warn('Pipeline status polling error:', err.message);
        setPipelineState((prev) => ({
          ...prev,
          status: 'failed',
          errorMessage: err.message || 'Lost connection to backend pipeline server.',
          logs: [
            ...prev.logs,
            `[Server Error] Failed to poll status from backend: ${err.message}`,
          ],
        }));
        clearInterval(pollIntervalRef.current);
      }
    }

    // Initial poll
    pollStatus();

    // Poll every 1800ms
    pollIntervalRef.current = setInterval(pollStatus, 1800);

    return () => {
      isSubscribed = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [isOpen, taskId, courseId, onPipelineComplete]);

  if (!isOpen) return null;

  const currentStageIndex = PIPELINE_STAGES.findIndex(s => s.key === pipelineState.currentStage);
  const isCompleted = pipelineState.status === 'completed' || pipelineState.currentStage === 'COMPLETED' || pipelineState.progressPercentage >= 100;
  const isFailed = pipelineState.status === 'failed';

  return (
    <div className="modal-backdrop-overlay" onClick={onClose}>
      <div 
        className="modal-container glass-panel animate-fade-in" 
        style={{ maxWidth: '850px', width: '90%' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-title">
            <div className="header-icon-pill">
              {isCompleted ? (
                <CheckCircle2 size={20} className="text-emerald" />
              ) : isFailed ? (
                <AlertCircle size={20} className="text-rose" />
              ) : (
                <Loader2 size={20} className="text-accent animate-spin" />
              )}
            </div>
            <div>
              <h2>AutoHKG Knowledge Graph Pipeline</h2>
              <p>Textbook Ingestion for: <strong>{courseTitle}</strong></p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ padding: '24px' }}>
          
          {/* Main Progress Bar Container */}
          <div className="pipeline-overall-progress-card glass-panel" style={{
            background: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '20px',
            borderRadius: '14px',
            marginBottom: '20px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className={`status-pill ${isCompleted ? 'badge-completed' : isFailed ? 'badge-failed' : 'badge-running'}`} style={{
                  padding: '4px 10px',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  background: isCompleted ? 'rgba(16, 185, 129, 0.15)' : isFailed ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                  color: isCompleted ? '#10b981' : isFailed ? '#ef4444' : '#818cf8',
                  border: isCompleted ? '1px solid #10b981' : isFailed ? '1px solid #ef4444' : '1px solid #6366f1'
                }}>
                  {isCompleted ? '✓ Completed' : isFailed ? '✗ Failed' : `Processing: ${pipelineState.currentStage}`}
                </span>
                <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                  Task ID: <code style={{ color: '#e2e8f0' }}>{taskId ? taskId.slice(0, 14) + '...' : 'active'}</code>
                </span>
              </div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#38bdf8' }}>
                {pipelineState.progressPercentage}%
              </div>
            </div>

            {/* Glowing Linear Progress Track */}
            <div style={{
              width: '100%',
              height: '10px',
              background: 'rgba(255, 255, 255, 0.06)',
              borderRadius: '999px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                width: `${pipelineState.progressPercentage}%`,
                height: '100%',
                background: isCompleted 
                  ? 'linear-gradient(90deg, #10b981, #34d399)'
                  : isFailed
                  ? '#ef4444'
                  : 'linear-gradient(90deg, #6366f1, #38bdf8, #a855f7)',
                borderRadius: '999px',
                transition: 'width 0.4s ease-out',
                boxShadow: isCompleted ? '0 0 12px rgba(16, 185, 129, 0.5)' : '0 0 12px rgba(56, 189, 248, 0.5)'
              }} />
            </div>

            {/* Stage Metrics Chips */}
            {pipelineState.stageDetails && Object.keys(pipelineState.stageDetails).length > 0 && (
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px', flexWrap: 'wrap' }}>
                {pipelineState.stageDetails.stage_1_chunks && (
                  <div className="mini-metric-chip" style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: '6px' }}>
                    📄 <strong>{pipelineState.stageDetails.stage_1_chunks}</strong> Chunks
                  </div>
                )}
                {pipelineState.stageDetails.stage_2_raw_concepts && (
                  <div className="mini-metric-chip" style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: '6px' }}>
                    🔍 <strong>{pipelineState.stageDetails.stage_2_raw_concepts}</strong> Raw Concepts
                  </div>
                )}
                {pipelineState.stageDetails.stage_3_clean_concepts && (
                  <div className="mini-metric-chip" style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: '6px' }}>
                    ✨ <strong>{pipelineState.stageDetails.stage_3_clean_concepts}</strong> Clean Concepts
                  </div>
                )}
                {pipelineState.stageDetails.stage_5_grounded_concepts && (
                  <div className="mini-metric-chip" style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: '6px' }}>
                    🔗 <strong>{pipelineState.stageDetails.stage_5_grounded_concepts}</strong> Grounded Mappings
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Toggle View: Stage Visualizer vs Live Logs */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
            <button
              type="button"
              className={`btn-secondary ${activeTab === 'stages' ? 'active-tab-btn' : ''}`}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: activeTab === 'stages' ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                background: activeTab === 'stages' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeTab === 'stages' ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
              onClick={() => setActiveTab('stages')}
            >
              <Layers size={14} />
              7-Stage Progression Flow
            </button>
            <button
              type="button"
              className={`btn-secondary ${activeTab === 'logs' ? 'active-tab-btn' : ''}`}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: activeTab === 'logs' ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                background: activeTab === 'logs' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeTab === 'logs' ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
              onClick={() => setActiveTab('logs')}
            >
              <Terminal size={14} />
              Live Console Logs ({pipelineState.logs.length})
            </button>
          </div>

          {/* Tab 1: 7-Stage Progression Flow */}
          {activeTab === 'stages' && (
            <div className="pipeline-stages-list" style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              maxHeight: '340px',
              overflowY: 'auto',
              paddingRight: '4px'
            }}>
              {PIPELINE_STAGES.map((stage, idx) => {
                const Icon = stage.icon;
                const isStageComplete = isCompleted || idx < currentStageIndex;
                const isStageActive = !isCompleted && idx === currentStageIndex;
                const isStageQueued = !isCompleted && idx > currentStageIndex;

                return (
                  <div 
                    key={stage.key}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      padding: '12px 16px',
                      borderRadius: '10px',
                      background: isStageActive 
                        ? 'rgba(56, 189, 248, 0.1)' 
                        : isStageComplete 
                        ? 'rgba(16, 185, 129, 0.05)'
                        : 'rgba(255, 255, 255, 0.02)',
                      border: isStageActive 
                        ? '1px solid #38bdf8' 
                        : isStageComplete 
                        ? '1px solid rgba(16, 185, 129, 0.3)'
                        : '1px solid rgba(255, 255, 255, 0.05)',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: isStageComplete 
                        ? 'rgba(16, 185, 129, 0.2)' 
                        : isStageActive 
                        ? 'rgba(56, 189, 248, 0.2)' 
                        : 'rgba(255, 255, 255, 0.05)',
                      color: isStageComplete ? '#10b981' : isStageActive ? '#38bdf8' : '#64748b'
                    }}>
                      {isStageComplete ? (
                        <CheckCircle2 size={18} />
                      ) : isStageActive ? (
                        <Loader2 size={18} className="animate-spin" />
                      ) : (
                        <span style={{ fontSize: '11px', fontWeight: 700 }}>{stage.num}</span>
                      )}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          fontWeight: 600,
                          fontSize: '14px',
                          color: isStageActive ? '#38bdf8' : isStageComplete ? '#f1f5f9' : '#64748b'
                        }}>
                          {stage.label}
                        </span>
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                          (Stage {stage.num})
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                        {stage.desc}
                      </div>
                    </div>

                    <div>
                      {isStageComplete ? (
                        <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 600 }}>Done</span>
                      ) : isStageActive ? (
                        <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 600 }}>In Progress...</span>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#475569' }}>Queued</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Tab 2: Live Console Terminal */}
          {activeTab === 'logs' && (
            <div 
              ref={logTerminalRef}
              style={{
                background: '#090d16',
                borderRadius: '10px',
                padding: '16px',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: '12px',
                color: '#38bdf8',
                maxHeight: '340px',
                overflowY: 'auto',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                lineHeight: 1.6
              }}
            >
              {pipelineState.logs.map((logLine, idx) => (
                <div key={idx} style={{ color: logLine.includes('Error') ? '#ef4444' : logLine.includes('Completed') ? '#34d399' : '#93c5fd' }}>
                  {logLine}
                </div>
              ))}
            </div>
          )}

          {/* Action Footer */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={onClose}
              style={{ padding: '8px 18px', borderRadius: '8px' }}
            >
              {isCompleted ? 'Close' : 'Run in Background'}
            </button>

            {isCompleted && (
              <button 
                type="button" 
                className="btn-accent" 
                onClick={() => {
                  onClose();
                  if (onPipelineComplete) {
                    onPipelineComplete({ courseId, taskId });
                  }
                }}
                style={{ padding: '8px 20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <span>View Generated Knowledge Graph</span>
                <ArrowRight size={16} />
              </button>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
