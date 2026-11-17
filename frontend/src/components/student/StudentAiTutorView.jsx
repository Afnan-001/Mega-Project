import React, { useState, useEffect, useRef } from 'react';
import { 
  HelpCircle, 
  Send, 
  Sparkles, 
  BookOpen, 
  FileText, 
  Loader2, 
  CheckCircle2, 
  MessageSquare, 
  ExternalLink,
  ChevronRight,
  Bot,
  User,
  Quote
} from 'lucide-react';
import { studentApi } from '../../services/api';

const QUICK_PROMPTS = [
  "Explain the difference between a Parse Tree and an Abstract Syntax Tree",
  "Why is Lexical Analysis separated from Syntax Analysis?",
  "What is the role of Intermediate Code Generation in a compiler?",
  "How does Bayesian Knowledge Tracing calculate my concept mastery?",
  "Give me an intuitive real-world example of Register Allocation"
];

export default function StudentAiTutorView({ 
  courses = [], 
  initialConcept = null,
  onClearConcept
}) {
  const [selectedCourseId, setSelectedCourseId] = useState(courses[0]?.id || '');
  const [selectedConcept, setSelectedConcept] = useState(initialConcept || '');
  const [learningPathConcepts, setLearningPathConcepts] = useState([]);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'tutor',
      text: "Hello! I am your AI Cognitive Tutor. Ask me any doubt about your textbook materials, concepts, compiler phases, or learning prerequisites. I'll provide answers grounded directly in your course material with citations!",
      citations: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Sync with prop changes
  useEffect(() => {
    if (initialConcept) {
      setSelectedConcept(initialConcept);
      setInputQuestion(`Can you explain '${initialConcept}' and its prerequisites in this course?`);
    }
  }, [initialConcept]);

  useEffect(() => {
    if (!selectedCourseId && courses.length > 0) {
      setSelectedCourseId(courses[0].id);
    }
  }, [courses, selectedCourseId]);

  // Load course concepts for the filter dropdown
  useEffect(() => {
    if (!selectedCourseId) return;
    const fetchPath = async () => {
      try {
        const res = await studentApi.getLearningPath(selectedCourseId);
        if (res && Array.isArray(res.path)) {
          setLearningPathConcepts(res.path.map(p => p.concept_name));
        }
      } catch {
        setLearningPathConcepts([]);
      }
    };
    fetchPath();
  }, [selectedCourseId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (customText = null) => {
    const qText = (customText || inputQuestion).trim();
    if (!qText || isLoading) return;

    if (!selectedCourseId) {
      alert('Please select an active course first.');
      return;
    }

    const userMsgId = `user_${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      sender: 'user',
      text: qText,
      concept: selectedConcept || null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuestion('');
    setIsLoading(true);

    try {
      const res = await studentApi.askAiTutor({
        course_id: selectedCourseId,
        question: qText,
        concept_name: selectedConcept || null,
      });

      const tutorMsg = {
        id: `tutor_${Date.now()}`,
        sender: 'tutor',
        text: res.answer,
        concept: res.concept_name,
        citations: res.citations || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, tutorMsg]);
    } catch (err) {
      const errorMsg = {
        id: `err_${Date.now()}`,
        sender: 'tutor',
        text: `I encountered an issue connecting to the learning knowledge base: ${err.message || 'Server error'}. Please try asking again.`,
        citations: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const currentCourse = courses.find(c => c.id === selectedCourseId) || courses[0];

  return (
    <div className="student-ai-tutor-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: '620px' }}>
      {/* Top Header */}
      <div className="glass-panel" style={{ padding: '16px 20px', borderRadius: '12px', marginBottom: '16px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
            <HelpCircle size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', margin: 0 }}>
              AI Cognitive Tutor & Doubts Desk
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '2px 0 0' }}>
              Ask questions grounded directly in course textbook chunks with textbook citations
            </p>
          </div>
        </div>

        {/* Course & Concept Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {courses.length > 0 && (
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              className="custom-select"
              style={{
                background: 'rgba(15, 23, 42, 0.8)',
                color: '#e2e8f0',
                border: '1px solid rgba(99, 102, 241, 0.3)',
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

          {learningPathConcepts.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <select
                value={selectedConcept}
                onChange={(e) => setSelectedConcept(e.target.value)}
                className="custom-select"
                style={{
                  background: 'rgba(15, 23, 42, 0.8)',
                  color: selectedConcept ? '#818cf8' : '#94a3b8',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  outline: 'none',
                  maxWidth: '200px',
                  cursor: 'pointer'
                }}
              >
                <option value="">Target: All Concepts</option>
                {learningPathConcepts.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              {selectedConcept && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedConcept('');
                    if (onClearConcept) onClearConcept();
                  }}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '13px' }}
                  title="Clear concept filter"
                >
                  ✕
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Box */}
      <div 
        className="glass-panel" 
        style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          borderRadius: '14px', 
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.08)' 
        }}
      >
        {/* Messages Feed */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div 
                key={msg.id} 
                style={{
                  display: 'flex',
                  gap: '12px',
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: isUser ? '80%' : '88%',
                }}
              >
                {!isUser && (
                  <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, #4f46e5, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                    <Bot size={18} color="#fff" />
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
                  <div 
                    style={{
                      background: isUser ? 'linear-gradient(135deg, #4f46e5, #6366f1)' : 'rgba(30, 41, 59, 0.85)',
                      color: '#f8fafc',
                      padding: '12px 16px',
                      borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                      border: isUser ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
                      fontSize: '14px',
                      lineHeight: '1.6',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                      whiteSpace: 'pre-wrap'
                    }}
                  >
                    {msg.text}
                  </div>

                  {/* Textbook Citations if any */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '100%' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Quote size={11} className="text-cyan" />
                        <span>Textbook Evidence Citations:</span>
                      </span>
                      {msg.citations.map((c, idx) => (
                        <div 
                          key={idx}
                          style={{
                            background: 'rgba(6, 182, 212, 0.08)',
                            border: '1px solid rgba(6, 182, 212, 0.25)',
                            borderRadius: '8px',
                            padding: '6px 10px',
                            fontSize: '12px',
                            color: '#e2e8f0',
                            lineHeight: 1.4
                          }}
                        >
                          <strong style={{ color: '#38bdf8' }}>[{c.chunk_id}]</strong>: {c.snippet}
                        </div>
                      ))}
                    </div>
                  )}

                  <span style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
                    {msg.timestamp}
                  </span>
                </div>

                {isUser && (
                  <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, #10b981, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                    <User size={18} color="#fff" />
                  </div>
                )}
              </div>
            );
          })}

          {isLoading && (
            <div style={{ display: 'flex', gap: '12px', alignSelf: 'flex-start', alignItems: 'center' }}>
              <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, #4f46e5, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Bot size={18} color="#fff" />
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.85)', padding: '10px 16px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '13px' }}>
                <Loader2 size={16} className="spin-icon text-cyan" />
                <span>Searching course textbook chunks & synthesizing explanation...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Prompts Bar */}
        <div style={{ padding: '8px 16px', background: 'rgba(15, 23, 42, 0.5)', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: '8px', overflowX: 'auto', whiteSpace: 'nowrap' }}>
          <span style={{ fontSize: '11px', color: '#64748b', alignSelf: 'center', marginRight: '4px' }}>
            Quick Prompts:
          </span>
          {QUICK_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSendMessage(prompt)}
              disabled={isLoading}
              style={{
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                color: '#c7d2fe',
                borderRadius: '12px',
                padding: '4px 10px',
                fontSize: '11px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(99, 102, 241, 0.25)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(99, 102, 241, 0.1)'; }}
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div style={{ padding: '12px 16px', background: 'rgba(15, 23, 42, 0.75)', borderTop: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <input
            type="text"
            placeholder={selectedConcept ? `Ask a doubt about ${selectedConcept}...` : "Ask a doubt about any course concept or compiler topic..."}
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSendMessage();
              }
            }}
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'rgba(30, 41, 59, 0.85)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              padding: '10px 14px',
              color: '#fff',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <button
            type="button"
            className="btn-primary"
            onClick={() => handleSendMessage()}
            disabled={isLoading || !inputQuestion.trim()}
            style={{
              padding: '10px 18px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: (isLoading || !inputQuestion.trim()) ? 'not-allowed' : 'pointer',
              opacity: (isLoading || !inputQuestion.trim()) ? 0.6 : 1
            }}
          >
            {isLoading ? <Loader2 size={16} className="spin-icon" /> : <Send size={16} />}
            <span>Ask Tutor</span>
          </button>
        </div>
      </div>
    </div>
  );
}
