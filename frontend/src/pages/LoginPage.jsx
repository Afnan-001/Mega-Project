import React, { useState } from 'react';
import { 
  BookOpen, 
  Sparkles, 
  ShieldCheck, 
  GraduationCap, 
  ArrowRight, 
  Lock, 
  Mail, 
  CheckCircle2, 
  Cpu, 
  FileText, 
  Share2,
  Eye,
  EyeOff
} from 'lucide-react';
import { useAuth, demoAccounts } from '../context/AuthContext';
import '../styles/login.css';

export default function LoginPage() {
  const { login } = useAuth();
  const [selectedRole, setSelectedRole] = useState('teacher'); // 'teacher' | 'student'
  const [email, setEmail] = useState('alex.mercer@university.edu');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleRoleChange = (role) => {
    setSelectedRole(role);
    setErrorMessage('');
    if (role === 'teacher') {
      setEmail('alex.mercer@university.edu');
      setPassword('••••••••••••');
    } else {
      setEmail('sarah.chen@student.edu');
      setPassword('••••••••••••');
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setErrorMessage('Please enter an email address.');
      return;
    }

    setIsLoading(true);
    setTimeout(() => {
      login(selectedRole, { email });
      setIsLoading(false);
    }, 500);
  };

  const handleQuickDemoLogin = (role) => {
    setSelectedRole(role);
    setIsLoading(true);
    setTimeout(() => {
      login(role, { email: demoAccounts[role].email });
      setIsLoading(false);
    }, 400);
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
              semantic graphs powered by AutoHKG.
            </p>

            <div className="features-list">
              <div className="feature-item">
                <div className="feature-icon-box">
                  <ShieldCheck size={18} className="text-indigo" />
                </div>
                <div>
                  <strong>Role-Based Access Control</strong>
                  <span>Dedicated, authenticated workspaces for faculty & enrolled students.</span>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon-box">
                  <FileText size={18} className="text-cyan" />
                </div>
                <div>
                  <strong>Teacher PDF Ingestion Engine</strong>
                  <span>Instant parsing, chunking, and concept hierarchy extraction.</span>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon-box">
                  <Share2 size={18} className="text-purple" />
                </div>
                <div>
                  <strong>Interactive Student Graphs</strong>
                  <span>Self-paced curriculum navigation with AI tutor citations.</span>
                </div>
              </div>
            </div>
          </div>

          <div className="brand-footer-stat">
            <div className="status-live-pill">
              <span className="live-dot"></span>
              <span>Secure Authentication & AutoHKG Ready</span>
            </div>
          </div>
        </div>

        {/* Right Side: Auth Form */}
        <div className="login-form-panel">
          <div className="form-header">
            <span className="auth-subtitle">Portal Authentication</span>
            <h2>Sign in to your account</h2>
            <p>Select your university academic role to access your dashboard</p>
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
                <span className="role-desc">Upload course PDFs & manage syllabus</span>
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
                <span className="role-desc">Explore course materials & graphs</span>
              </div>
              {selectedRole === 'student' && <CheckCircle2 size={16} className="role-check-icon" />}
            </button>
          </div>

          {/* Quick 1-Click Demo Buttons */}
          <div className="quick-access-banner">
            <div className="quick-banner-title">
              <Sparkles size={14} className="text-amber" />
              <span>One-Click Demo Access</span>
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

          {errorMessage && (
            <div className="auth-error-alert animate-fade-in">
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Credentials Form */}
          <form onSubmit={handleFormSubmit} className="credentials-form">
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
                <a href="#forgot" onClick={(e) => e.preventDefault()} className="forgot-link">
                  Forgot password?
                </a>
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
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to {selectedRole === 'teacher' ? 'Teacher Dashboard' : 'Student Dashboard'}</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="role-policy-footnote">
            <ShieldCheck size={14} className="text-muted" />
            <span>
              Role-based routing active. Non-faculty accounts are restricted from course PDF upload endpoints.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
