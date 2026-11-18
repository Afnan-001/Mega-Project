import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  History,
  CheckCircle2,
  XCircle,
  BookOpen,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RefreshCw,
  FileText,
  Layers,
  List,
  Award,
  HelpCircle,
  Loader2,
  Clock,
  ShieldCheck
} from 'lucide-react';
import { studentApi } from '../../services/api';

const STOP_WORDS = new Set([
  'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'what', 'which',
  'when', 'where', 'how', 'does', 'are', 'was', 'were', 'been', 'being', 'have',
  'has', 'had', 'not', 'but', 'can', 'will', 'its', 'their', 'they', 'them',
  'following', 'statement', 'statements', 'concept', 'question', 'regarding',
  'primary', 'during', 'between', 'about', 'under', 'only', 'most', 'used'
]);

function extractKeyTokens(text = '') {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length >= 3 && !STOP_WORDS.has(w));
}

/**
 * Splits a textbook chunk into sentences and highlights the sentence(s)
 * with the highest overlap against the question, concept, and correct answer
 * so users can immediately see which line grounded the MCQ.
 */
function HighlightedChunkText({ text, conceptName, questionText, correctOption }) {
  const sentences = useMemo(() => {
    if (!text) return [];
    const raw = text.match(/[^.!?\n]+[.!?\n]*/g) || [text];
    const queryTokens = new Set([
      ...extractKeyTokens(conceptName),
      ...extractKeyTokens(questionText),
      ...extractKeyTokens(correctOption),
    ]);

    const scored = raw.map((sentence) => {
      const sTokens = extractKeyTokens(sentence);
      let hits = 0;
      sTokens.forEach((tok) => {
        if (queryTokens.has(tok)) hits += 1;
      });
      const conceptExact =
        conceptName && sentence.toLowerCase().includes(conceptName.toLowerCase()) ? 3 : 0;
      return { sentence, score: hits + conceptExact };
    });

    const maxScore = Math.max(...scored.map((s) => s.score), 0);
    return scored.map((s) => ({
      ...s,
      isHighlighted: maxScore >= 2 && s.score >= Math.max(2, maxScore - 1),
    }));
  }, [text, conceptName, questionText, correctOption]);

  if (!sentences.length) return null;

  return (
    <p style={{ margin: 0, fontSize: '12.5px', lineHeight: 1.65, color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
      {sentences.map((item, idx) =>
        item.isHighlighted ? (
          <mark
            key={idx}
            style={{
              background: 'rgba(250, 204, 21, 0.18)',
              color: '#fef08a',
              borderBottom: '1px solid rgba(250, 204, 21, 0.45)',
              borderRadius: '3px',
              padding: '1px 3px',
            }}
            title="Matched grounding line for this question"
          >
            {item.sentence}
          </mark>
        ) : (
          <span key={idx}>{item.sentence}</span>
        )
      )}
    </p>
  );
}

function formatDateTime(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function PastQuestionCard({ item, index }) {
  const [showContext, setShowContext] = useState(true);
  const delta = Number((item.posterior_mastery - item.prior_mastery).toFixed(1));

  return (
    <div
      className="glass-panel"
      style={{
        padding: '18px 20px',
        borderRadius: '14px',
        border: item.is_correct
          ? '1px solid rgba(16, 185, 129, 0.25)'
          : '1px solid rgba(239, 68, 68, 0.28)',
        background: 'rgba(15, 23, 42, 0.65)',
        marginBottom: '14px',
      }}
    >
      {/* Top Meta Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '3px 10px',
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 700,
              background: item.is_correct
                ? 'rgba(16, 185, 129, 0.16)'
                : 'rgba(239, 68, 68, 0.16)',
              color: item.is_correct ? '#34d399' : '#f87171',
              border: item.is_correct
                ? '1px solid rgba(16, 185, 129, 0.35)'
                : '1px solid rgba(239, 68, 68, 0.35)',
            }}
          >
            {item.is_correct ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
            <span>{item.is_correct ? 'Correct' : 'Incorrect'}</span>
          </span>

          <span
            style={{
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#a5b4fc',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              padding: '3px 10px',
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            {item.concept_name}
          </span>

          <span
            style={{
              background: 'rgba(56, 189, 248, 0.12)',
              color: '#7dd3fc',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              padding: '3px 10px',
              borderRadius: '20px',
              fontSize: '11.5px',
              fontWeight: 500,
            }}
          >
            {item.course_title}
          </span>

          {item.difficulty && (
            <span
              style={{
                background:
                  item.difficulty === 'hard'
                    ? 'rgba(239, 68, 68, 0.14)'
                    : item.difficulty === 'easy'
                    ? 'rgba(16, 185, 129, 0.14)'
                    : 'rgba(245, 158, 11, 0.14)',
                color:
                  item.difficulty === 'hard'
                    ? '#f87171'
                    : item.difficulty === 'easy'
                    ? '#34d399'
                    : '#fbbf24',
                padding: '3px 9px',
                borderRadius: '20px',
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'capitalize',
              }}
            >
              {item.difficulty}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px', color: '#94a3b8' }}>
          <span>
            Mastery:{' '}
            <strong style={{ color: '#cbd5e1' }}>{item.prior_mastery?.toFixed(1)}%</strong> ➔{' '}
            <strong style={{ color: item.is_correct ? '#34d399' : '#f87171' }}>
              {item.posterior_mastery?.toFixed(1)}%
            </strong>{' '}
            <span style={{ color: item.is_correct ? '#34d399' : '#f87171', fontWeight: 600 }}>
              ({delta >= 0 ? `+${delta}%` : `${delta}%`})
            </span>
          </span>
          {item.created_at && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#64748b' }}>
              <Clock size={12} />
              {formatDateTime(item.created_at)}
            </span>
          )}
        </div>
      </div>

      {/* Question Text */}
      <div
        style={{
          fontSize: '14.5px',
          lineHeight: 1.55,
          color: '#f8fafc',
          fontWeight: 500,
          marginBottom: '12px',
          whiteSpace: 'pre-wrap',
        }}
      >
        <span style={{ color: '#64748b', marginRight: '8px', fontWeight: 700 }}>Q{index + 1}.</span>
        {item.question_text}
      </div>

      {/* Options Grid */}
      {item.options && item.options.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '8px',
            marginBottom: '12px',
          }}
        >
          {item.options.map((opt, optIdx) => {
            const isCorrectOpt =
              opt.trim().toLowerCase() === (item.correct_option || '').trim().toLowerCase();
            const isSelectedOpt =
              opt.trim().toLowerCase() === (item.selected_option || '').trim().toLowerCase();
            const isWrongSelected = isSelectedOpt && !item.is_correct;

            let bg = 'rgba(255, 255, 255, 0.025)';
            let border = '1px solid rgba(255, 255, 255, 0.08)';
            let color = '#cbd5e1';

            if (isCorrectOpt) {
              bg = 'rgba(16, 185, 129, 0.13)';
              border = '1px solid rgba(16, 185, 129, 0.45)';
              color = '#ecfdf5';
            } else if (isWrongSelected) {
              bg = 'rgba(239, 68, 68, 0.13)';
              border = '1px solid rgba(239, 68, 68, 0.45)';
              color = '#fef2f2';
            }

            return (
              <div
                key={optIdx}
                style={{
                  background: bg,
                  border,
                  color,
                  borderRadius: '9px',
                  padding: '9px 12px',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ fontWeight: 700, color: '#94a3b8', flexShrink: 0 }}>
                    {String.fromCharCode(65 + optIdx)}.
                  </span>
                  <span>{opt}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                  {isSelectedOpt && (
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '10px',
                        background: item.is_correct
                          ? 'rgba(16, 185, 129, 0.25)'
                          : 'rgba(239, 68, 68, 0.25)',
                        color: item.is_correct ? '#6ee7b7' : '#fca5a5',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      Your Answer
                    </span>
                  )}
                  {isCorrectOpt && !isSelectedOpt && (
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '10px',
                        background: 'rgba(16, 185, 129, 0.25)',
                        color: '#6ee7b7',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      Correct
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Explanation */}
      {item.explanation && (
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            borderLeft: `3px solid ${item.is_correct ? '#10b981' : '#f59e0b'}`,
            borderRadius: '0 8px 8px 0',
            padding: '9px 12px',
            fontSize: '12.5px',
            color: '#cbd5e1',
            marginBottom: '12px',
            lineHeight: 1.5,
          }}
        >
          <strong style={{ color: '#e2e8f0' }}>Explanation: </strong>
          {item.explanation}
        </div>
      )}

      {/* Grounded Source Textbook Context Chunks */}
      <div
        style={{
          border: '1px solid rgba(56, 189, 248, 0.22)',
          background: 'rgba(14, 116, 144, 0.08)',
          borderRadius: '10px',
          overflow: 'hidden',
        }}
      >
        <button
          type="button"
          onClick={() => setShowContext((v) => !v)}
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            padding: '9px 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            color: '#7dd3fc',
            fontSize: '12.5px',
            fontWeight: 600,
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px' }}>
            <ShieldCheck size={15} style={{ color: '#38bdf8' }} />
            <span>
              Relevant Textbook Source Context ({item.source_chunks?.length || 0}{' '}
              {(item.source_chunks?.length || 0) === 1 ? 'chunk' : 'chunks'} — Grounding Verification)
            </span>
          </span>
          {showContext ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>

        {showContext && (
          <div style={{ padding: '0 12px 12px 12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {item.source_chunks && item.source_chunks.length > 0 ? (
              item.source_chunks.map((chunk, cIdx) => (
                <div
                  key={`${chunk.chunk_id}_${cIdx}`}
                  style={{
                    background: 'rgba(15, 23, 42, 0.78)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '10px 12px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                      marginBottom: '6px',
                      fontSize: '11.5px',
                    }}
                  >
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        color: '#38bdf8',
                        fontWeight: 700,
                        fontFamily: 'monospace',
                      }}
                    >
                      <FileText size={12} />
                      {chunk.chunk_id}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {chunk.page_number !== null && chunk.page_number !== undefined && (
                        <span
                          style={{
                            background: 'rgba(56, 189, 248, 0.14)',
                            color: '#bae6fd',
                            padding: '1px 7px',
                            borderRadius: '10px',
                            fontWeight: 600,
                          }}
                        >
                          Page {chunk.page_number}
                        </span>
                      )}
                      <span style={{ color: '#facc15', fontSize: '11px' }}>
                        Highlighted = matched source lines
                      </span>
                    </div>
                  </div>

                  <HighlightedChunkText
                    text={chunk.text}
                    conceptName={item.concept_name}
                    questionText={item.question_text}
                    correctOption={item.correct_option}
                  />
                </div>
              ))
            ) : (
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                No textbook source chunk attached to this record.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function StudentQuizHistoryView({
  courses = [],
  refreshTrigger = 0,
  onTakeQuiz,
  onAskTutor,
}) {
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  // Filters
  const [selectedCourse, setSelectedCourse] = useState('all');
  const [selectedConcept, setSelectedConcept] = useState('all');
  const [resultFilter, setResultFilter] = useState('all'); // 'all' | 'correct' | 'incorrect'
  const [viewMode, setViewMode] = useState('concept'); // 'concept' | 'timeline'
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState({});

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await studentApi.getQuizHistory({
        courseId: selectedCourse,
        result: resultFilter,
      });
      setHistoryData(res);
    } catch (err) {
      console.warn('Failed to fetch student quiz history:', err.message);
      setErrorMsg(err.message || 'Unable to load past questions from backend.');
    } finally {
      setLoading(false);
    }
  }, [selectedCourse, resultFilter]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, refreshTrigger]);

  // Reset concept filter if course changes
  useEffect(() => {
    setSelectedConcept('all');
  }, [selectedCourse]);

  // Build merged course dropdown options (enrolled courses + any courses with attempts)
  const courseOptions = useMemo(() => {
    const map = new Map();
    courses.forEach((c) => {
      map.set(c.id, {
        course_id: c.id,
        course_title: c.title || c.name || 'Course',
        attempts: 0,
      });
    });
    (historyData?.courses || []).forEach((hc) => {
      map.set(hc.course_id, {
        course_id: hc.course_id,
        course_title: hc.course_title,
        attempts: hc.attempts,
      });
    });
    return Array.from(map.values());
  }, [courses, historyData]);

  // Concepts available under current course filter
  const conceptOptions = useMemo(() => {
    return historyData?.concept_summary || [];
  }, [historyData]);

  // Client-side concept + search filtering
  const visibleAttempts = useMemo(() => {
    const list = historyData?.attempts || [];
    const q = searchQuery.trim().toLowerCase();
    return list.filter((item) => {
      const matchConcept =
        selectedConcept === 'all' ||
        item.concept_name.toLowerCase() === selectedConcept.toLowerCase();
      if (!matchConcept) return false;
      if (!q) return true;
      const inQuestion = (item.question_text || '').toLowerCase().includes(q);
      const inConcept = (item.concept_name || '').toLowerCase().includes(q);
      const inCourse = (item.course_title || '').toLowerCase().includes(q);
      const inChunks = (item.source_chunks || []).some((c) =>
        (c.text || '').toLowerCase().includes(q)
      );
      return inQuestion || inConcept || inCourse || inChunks;
    });
  }, [historyData, selectedConcept, searchQuery]);

  // Group visible attempts by (course_id + concept_name) for Concept-wise view
  const groupedByConcept = useMemo(() => {
    const summaryMap = new Map();
    (historyData?.concept_summary || []).forEach((s) => {
      summaryMap.set(`${s.course_id}::${s.concept_name}`, s);
    });

    const groups = new Map();
    visibleAttempts.forEach((item) => {
      const key = `${item.course_id}::${item.concept_name}`;
      if (!groups.has(key)) {
        const s = summaryMap.get(key);
        groups.set(key, {
          key,
          course_id: item.course_id,
          course_title: item.course_title,
          concept_name: item.concept_name,
          latest_mastery: s?.latest_mastery_percentage ?? item.posterior_mastery,
          items: [],
        });
      }
      groups.get(key).items.push(item);
    });

    return Array.from(groups.values()).map((g) => {
      const correct = g.items.filter((i) => i.is_correct).length;
      const total = g.items.length;
      return {
        ...g,
        correct,
        incorrect: total - correct,
        accuracy: total ? Math.round((correct / total) * 100) : 0,
      };
    });
  }, [visibleAttempts, historyData]);

  // KPI metrics for currently visible attempts
  const stats = useMemo(() => {
    const total = visibleAttempts.length;
    const correct = visibleAttempts.filter((a) => a.is_correct).length;
    const incorrect = total - correct;
    const accuracy = total ? ((correct / total) * 100).toFixed(1) : '0.0';
    return { total, correct, incorrect, accuracy };
  }, [visibleAttempts]);

  const toggleGroup = (key) => {
    setCollapsedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="student-history-view animate-fade-in">
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="faculty-badge">
              <History size={14} className="text-cyan" />
              <span>Past Questions & Grounding Verification</span>
            </span>
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fff', margin: '4px 0' }}>
            My Past Questions, Results & Source Context
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem', margin: 0 }}>
            Review your answered MCQs concept-wise across courses and inspect the exact textbook chunk each question was generated from.
          </p>
        </div>

        <button
          type="button"
          className="btn-secondary"
          onClick={fetchHistory}
          disabled={loading}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '13px',
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '12px',
          marginBottom: '1.25rem',
        }}
      >
        <div className="glass-panel" style={{ padding: '14px 16px', borderRadius: '12px' }}>
          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Questions Answered</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f8fafc' }}>{stats.total}</div>
        </div>
        <div className="glass-panel" style={{ padding: '14px 16px', borderRadius: '12px' }}>
          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Correct Responses</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#34d399' }}>{stats.correct}</div>
        </div>
        <div className="glass-panel" style={{ padding: '14px 16px', borderRadius: '12px' }}>
          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Incorrect Responses</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f87171' }}>{stats.incorrect}</div>
        </div>
        <div className="glass-panel" style={{ padding: '14px 16px', borderRadius: '12px' }}>
          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Overall Accuracy</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8' }}>{stats.accuracy}%</div>
        </div>
      </div>

      {/* Filters & Controls */}
      <div
        className="glass-panel"
        style={{
          padding: '14px 16px',
          borderRadius: '12px',
          marginBottom: '1.25rem',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '10px',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center', flex: 1 }}>
          {/* Course Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <BookOpen size={14} style={{ color: '#94a3b8' }} />
            <select
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value)}
              className="custom-select"
              style={{
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#f8fafc',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                borderRadius: '8px',
                padding: '7px 10px',
                fontSize: '12.5px',
                minWidth: '175px',
              }}
            >
              <option value="all">All Courses</option>
              {courseOptions.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.course_title} {c.attempts > 0 ? `(${c.attempts})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Concept Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Filter size={14} style={{ color: '#94a3b8' }} />
            <select
              value={selectedConcept}
              onChange={(e) => setSelectedConcept(e.target.value)}
              className="custom-select"
              style={{
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#f8fafc',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                borderRadius: '8px',
                padding: '7px 10px',
                fontSize: '12.5px',
                minWidth: '175px',
              }}
            >
              <option value="all">All Concepts ({conceptOptions.length})</option>
              {conceptOptions.map((c) => (
                <option key={`${c.course_id}_${c.concept_name}`} value={c.concept_name}>
                  {c.concept_name} ({c.correct}/{c.attempts})
                </option>
              ))}
            </select>
          </div>

          {/* Result Filter Pills */}
          <div style={{ display: 'flex', gap: '4px', background: 'rgba(15, 23, 42, 0.7)', padding: '3px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
            {[
              { id: 'all', label: 'All' },
              { id: 'correct', label: 'Correct' },
              { id: 'incorrect', label: 'Wrong' },
            ].map((pill) => (
              <button
                key={pill.id}
                type="button"
                onClick={() => setResultFilter(pill.id)}
                style={{
                  border: 'none',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background:
                    resultFilter === pill.id
                      ? pill.id === 'correct'
                        ? 'rgba(16, 185, 129, 0.25)'
                        : pill.id === 'incorrect'
                        ? 'rgba(239, 68, 68, 0.25)'
                        : 'rgba(99, 102, 241, 0.35)'
                      : 'transparent',
                  color:
                    resultFilter === pill.id
                      ? pill.id === 'correct'
                        ? '#6ee7b7'
                        : pill.id === 'incorrect'
                        ? '#fca5a5'
                        : '#e0e7ff'
                      : '#94a3b8',
                }}
              >
                {pill.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative', flex: '1 1 200px', minWidth: '180px' }}>
            <Search
              size={14}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#64748b',
              }}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search question, concept, or chunk text..."
              style={{
                width: '100%',
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#f8fafc',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                borderRadius: '8px',
                padding: '7px 10px 7px 30px',
                fontSize: '12.5px',
                boxSizing: 'border-box',
              }}
            />
          </div>
        </div>

        {/* View Mode Toggle */}
        <div
          style={{
            display: 'flex',
            gap: '4px',
            background: 'rgba(15, 23, 42, 0.7)',
            padding: '3px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <button
            type="button"
            onClick={() => setViewMode('concept')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              border: 'none',
              borderRadius: '6px',
              padding: '5px 10px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              background: viewMode === 'concept' ? 'rgba(99, 102, 241, 0.35)' : 'transparent',
              color: viewMode === 'concept' ? '#e0e7ff' : '#94a3b8',
            }}
          >
            <Layers size={13} />
            <span>Concept-wise</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('timeline')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              border: 'none',
              borderRadius: '6px',
              padding: '5px 10px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              background: viewMode === 'timeline' ? 'rgba(99, 102, 241, 0.35)' : 'transparent',
              color: viewMode === 'timeline' ? '#e0e7ff' : '#94a3b8',
            }}
          >
            <List size={13} />
            <span>Timeline</span>
          </button>
        </div>
      </div>

      {/* Body Content */}
      {loading ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', borderRadius: '14px' }}>
          <Loader2 size={32} className="text-accent animate-spin" style={{ margin: '0 auto 12px' }} />
          <p style={{ color: '#94a3b8', margin: 0 }}>Loading your past questions and grounded textbook chunks...</p>
        </div>
      ) : errorMsg ? (
        <div className="glass-panel" style={{ padding: '32px', textAlign: 'center', borderRadius: '14px' }}>
          <p style={{ color: '#f87171', marginBottom: '12px' }}>{errorMsg}</p>
          <button type="button" className="btn-secondary" onClick={fetchHistory}>
            Retry
          </button>
        </div>
      ) : visibleAttempts.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px 24px', textAlign: 'center', borderRadius: '14px' }}>
          <History size={40} style={{ color: '#64748b', margin: '0 auto 12px' }} />
          <h3 style={{ color: '#f8fafc', margin: '0 0 6px' }}>No Past Questions Found</h3>
          <p style={{ color: '#94a3b8', fontSize: '13.5px', maxWidth: '460px', margin: '0 auto 18px' }}>
            {historyData?.total_attempts > 0
              ? 'No questions match your current course, concept, or search filters.'
              : 'Answer your first Cognitive-RAG quiz question to see your response history and grounded textbook chunks here.'}
          </p>
          {onTakeQuiz && courses.length > 0 && (
            <button
              type="button"
              className="btn-accent"
              onClick={() => onTakeQuiz(null, selectedCourse !== 'all' ? selectedCourse : courses[0]?.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 18px',
                borderRadius: '8px',
              }}
            >
              <Sparkles size={15} />
              <span>Start Adaptive Quiz</span>
            </button>
          )}
        </div>
      ) : viewMode === 'concept' ? (
        /* Concept-wise Grouped View */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {groupedByConcept.map((group) => {
            const isCollapsed = !!collapsedGroups[group.key];
            return (
              <div
                key={group.key}
                className="glass-panel"
                style={{
                  borderRadius: '14px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  overflow: 'hidden',
                }}
              >
                {/* Concept Group Header */}
                <div
                  style={{
                    padding: '14px 18px',
                    background: 'rgba(30, 41, 59, 0.65)',
                    borderBottom: isCollapsed ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '10px',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.key)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      cursor: 'pointer',
                      padding: 0,
                      textAlign: 'left',
                    }}
                  >
                    {isCollapsed ? (
                      <ChevronDown size={18} style={{ color: '#94a3b8' }} />
                    ) : (
                      <ChevronUp size={18} style={{ color: '#94a3b8' }} />
                    )}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc' }}>
                          {group.concept_name}
                        </span>
                        <span
                          style={{
                            fontSize: '11.5px',
                            background: 'rgba(56, 189, 248, 0.12)',
                            color: '#7dd3fc',
                            padding: '2px 8px',
                            borderRadius: '12px',
                          }}
                        >
                          {group.course_title}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <span>
                          Score:{' '}
                          <strong style={{ color: '#34d399' }}>{group.correct}</strong> / {group.items.length} Correct ({group.accuracy}%)
                        </span>
                        <span>
                          Current BKT Mastery:{' '}
                          <strong style={{ color: group.latest_mastery >= 85 ? '#34d399' : '#fbbf24' }}>
                            {Number(group.latest_mastery).toFixed(1)}%
                          </strong>
                        </span>
                      </div>
                    </div>
                  </button>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {onAskTutor && (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => onAskTutor(group.concept_name)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '6px 11px',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      >
                        <HelpCircle size={13} />
                        <span>Ask Tutor</span>
                      </button>
                    )}
                    {onTakeQuiz && (
                      <button
                        type="button"
                        className="btn-accent"
                        onClick={() => onTakeQuiz(group.concept_name, group.course_id)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      >
                        <Award size={13} />
                        <span>Practice Again</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Group Questions List */}
                {!isCollapsed && (
                  <div style={{ padding: '14px 16px 4px 16px' }}>
                    {group.items.map((item, idx) => (
                      <PastQuestionCard key={item.id} item={item} index={idx} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* Flat Chronological Timeline View */
        <div>
          {visibleAttempts.map((item, idx) => (
            <PastQuestionCard key={item.id} item={item} index={idx} />
          ))}
        </div>
      )}
    </div>
  );
}
