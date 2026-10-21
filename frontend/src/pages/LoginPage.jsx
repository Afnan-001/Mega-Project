import React, { useState } from 'react';
import { 
  BookOpen, 
  Sparkles, 
  ShieldCheck, 
  GraduationCap, 
  ArrowRight, 
  Lock, 
  Mail, 
  User,
  CheckCircle2, 
  Cpu, 
  FileText, 
  Share2,
  Eye,
  EyeOff,
  Server
} from 'lucide-react';
import { useAuth, demoAccounts } from '../context/AuthContext';
import '../styles/login.css';

export default function LoginPage() {
  const { login, register, serverOnline, isCheckingServer, authError } = useAuth();
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [selectedRole, setSelectedRole] = useState('teacher'); // 'teacher' | 'student'
  const [fullName, setFullName] = useState('Dr. Sarah Connor');
  const [email, setEmail] = useState('teacher@university.edu');
  const [password, setPassword] = useState('StrongPassword123!');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState('');

  const handleRoleChange = (role) => {
    setSelectedRole(role);
    setLocalError('');
    if (role === 'teacher') {
      setFullName('Dr. Sarah Connor');
      setEmail('teacher@university.edu');
      setPassword('StrongPassword123!');
    } else {
      setFullName('Sarah Chen');
      setEmail('student@university.edu');
      setPassword('StrongPassword123!');
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');

    if (!email.trim()) {
      setLocalError('Please enter an academic email address.');
      return;
    }
    if (!password.trim()) {
      setLocalError('Please enter a password.');
      return;
    }

    setIsLoading(true);
    try {
      if (authMode === 'register') {
        if (!fullName.trim()) {
          setLocalError('Please provide your full name.');
          setIsLoading(false);
          return;
        }
        await register({
          email: email.trim(),
          password: password,
          full_name: fullName.trim(),
          role: selectedRole,
        });
      } else {
        await login(selectedRole, { 
          email: email.trim(),
          password: password 
        });
      }
    } catch (err) {
      setLocalError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLogin = async (role) => {
    setSelectedRole(role);
    setLocalError('');
    setIsLoading(true);
    try {
      const demo = demoAccounts[role];
      await login(role, { 
        email: demo.email,
        password: demo.password,
        name: demo.name 
      });
    } catch (err) {
      setLocalError(err.message || 'Demo login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card-wrapper glass-panel animate-fade-in">
        {/* Left Side: Brand & Visual AI Highlights */}
        <div className="login-brand-panel">
          <div className="brand-header">
            <div className="logo-badge">
              <Sparkles size={18} className="logo-sparkle" />
              <BookOpen size={24} className="logo-main-icon" />
            </div>
            <div>
              <h2 className="brand-title">EduGraph<span className="cyan-dot">.AI</span></h2>
              <span className="brand-tag">Intelligent Academic Knowledge Platform</span>
            </div>
          </div>

          <div className="brand-hero-content">
            <h3>Knowledge Graph Engineering for Higher Education</h3>
            <p>
              Transform course textbooks, lecture PDFs, and curriculum syllabi into interactive 
              semantic graphs powered by AutoHKG and Cognitive-RAG.
            </p>

            <div className="features-list">
              <div className="feature-item">
                <div className="feature-icon-box">
                  <ShieldCheck size={18} className="text-indigo" />
                </div>
                <div>
                  <strong>Role-Based Access Control</strong>
                  <span>FastAPI JWT security with dedicated workspaces for faculty & students.</span>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon-box">
                  <FileText size={18} className="text-cyan" />
                </div>
                <div>
                  <strong>Teacher PDF Ingestion Engine</strong>
                  <span>7-stage AutoHKG pipeline with live progress tracking & chunk mapping.</span>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon-box">
                  <Share2 size={18} className="text-purple" />
                </div>
                <div>
                  <strong>Cognitive-RAG Adaptive Learning</strong>
                  <span>Dynamic MCQs, Bayesian Knowledge Tracing (BKT), and prerequisite mastery.</span>
                </div>
              </div>
            </div>
          </div>

          <div className="brand-footer-stat">
            <div className={`status-live-pill ${serverOnline ? 'online' : 'offline'}`}>
              <span className={`live-dot ${serverOnline ? 'dot-green' : 'dot-amber'}`}></span>
              <Server size={14} />
              <span>
                {isCheckingServer 
                  ? 'Connecting to backend...' 
                  : serverOnline 
                  ? 'FastAPI Server Connected (:8000)' 
                  : 'Backend Offline (Demo Fallback Ready)'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Side: Auth Form */}
        <div className="login-form-panel">
          <div className="form-header">
            <span className="auth-subtitle">Portal Authentication</span>
            <h2>{authMode === 'login' ? 'Sign in to your account' : 'Create a new account'}</h2>
            <p>Select your university academic role to access your dashboard</p>
          </div>

          {/* Mode Switcher: Sign In vs Register */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button
              type="button"
              className={`btn-secondary ${authMode === 'login' ? 'active-tab-btn' : ''}`}
              style={{
                flex: 1,
                padding: '8px 14px',
                borderRadius: '8px',
                border: authMode === 'login' ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
                background: authMode === 'login' ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: authMode === 'login' ? '#fff' : '#94a3b8',
                cursor: 'pointer',
                fontWeight: 600,
              }}
              onClick={() => {
                setAuthMode('login');
                setLocalError('');
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`btn-secondary ${authMode === 'register' ? 'active-tab-btn' : ''}`}
              style={{
                flex: 1,
                padding: '8px 14px',
                borderRadius: '8px',
                border: authMode === 'register' ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
                background: authMode === 'register' ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: authMode === 'register' ? '#fff' : '#94a3b8',
                cursor: 'pointer',
                fontWeight: 600,
              }}
              onClick={() => {
                setAuthMode('register');
                setLocalError('');
              }}
            >
              Register New Account
            </button>
          </div>

          {/* Role Selection Tabs */}
          <div className="role-selection-tabs">
            <button
              type="button"
              className={`role-select-btn ${selectedRole === 'teacher' ? 'active teacher-active' : ''}`}
              onClick={() => handleRoleChange('teacher')}
            >
              <ShieldCheck size={18} />
              <div className="role-btn-text">
                <span className="role-name">Faculty / Teacher</span>
                <span className="role-desc">Upload course PDFs & run AutoHKG</span>
              </div>
              {selectedRole === 'teacher' && <CheckCircle2 size={16} className="role-check-icon" />}
            </button>

            <button
              type="button"
              className={`role-select-btn ${selectedRole === 'student' ? 'active student-active' : ''}`}
              onClick={() => handleRoleChange('student')}
            >
              <GraduationCap size={18} />
              <div className="role-btn-text">
                <span className="role-name">Student</span>
                <span className="role-desc">Interactive learning paths & quizzes</span>
              </div>
              {selectedRole === 'student' && <CheckCircle2 size={16} className="role-check-icon" />}
            </button>
          </div>

          {/* Quick 1-Click Demo Buttons */}
          <div className="quick-access-banner">
            <div className="quick-banner-title">
              <Sparkles size={14} className="text-amber" />
              <span>One-Click Instant Access</span>
            </div>
            <div className="quick-buttons-row">
              <button 
                type="button" 
                className={`quick-pill-btn ${selectedRole === 'teacher' ? 'selected' : ''}`}
                onClick={() => handleQuickDemoLogin('teacher')}
                title="Sign in directly as Faculty Professor"
              >
                <span>👨‍🏫 Demo Teacher</span>
              </button>
              <button 
                type="button" 
                className={`quick-pill-btn ${selectedRole === 'student' ? 'selected' : ''}`}
                onClick={() => handleQuickDemoLogin('student')}
                title="Sign in directly as Enrolled Student"
              >
                <span>🎓 Demo Student</span>
              </button>
            </div>
          </div>

          {(localError || authError) && (
            <div className="auth-error-alert animate-fade-in">
              <span>{localError || authError}</span>
            </div>
          )}

          {/* Credentials Form */}
          <form onSubmit={handleFormSubmit} className="credentials-form">
            {authMode === 'register' && (
              <div className="input-group">
                <label>Full Name</label>
                <div className="input-field-wrap">
                  <User size={16} className="input-icon" />
                  <input 
                    type="text" 
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Dr. Sarah Connor"
                    required
                  />
                </div>
              </div>
            )}

            <div className="input-group">
              <label>Academic Email</label>
              <div className="input-field-wrap">
                <Mail size={16} className="input-icon" />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@university.edu"
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <div className="password-label-row">
                <label>Password</label>
                {authMode === 'login' && (
                  <a href="#forgot" onClick={(e) => e.preventDefault()} className="forgot-link">
                    Forgot password?
                  </a>
                )}
              </div>
              <div className="input-field-wrap">
                <Lock size={16} className="input-icon" />
                <input 
                  type={showPassword ? 'text' : 'password'} 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
                <button 
                  type="button" 
                  className="eye-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="form-options-row">
              <label className="checkbox-wrap">
                <input 
                  type="checkbox" 
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me on this workstation</span>
              </label>
            </div>

            <button 
              type="submit" 
              className={`submit-login-btn ${selectedRole === 'teacher' ? 'btn-teacher' : 'btn-student'}`}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner-border"></span>
                  <span>Authenticating with server...</span>
                </>
              ) : (
                <>
                  <span>
                    {authMode === 'register' 
                      ? `Register as ${selectedRole === 'teacher' ? 'Faculty' : 'Student'}`
                      : `Sign In to ${selectedRole === 'teacher' ? 'Teacher Dashboard' : 'Student Dashboard'}`}
                  </span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="role-policy-footnote">
            <ShieldCheck size={14} className="text-muted" />
            <span>
              FastAPI RBAC active. Non-faculty accounts are restricted from course PDF upload endpoints.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
