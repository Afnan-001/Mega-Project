import React from 'react';
import { 
  GraduationCap, 
  Sparkles, 
  BookOpen, 
  Bell, 
  Search, 
  ShieldCheck, 
  LogOut,
  User
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function Navbar({ onOpenUploadModal }) {
  const { user, role, logout } = useAuth();

  return (
    <header className="navbar glass-panel">
      <div className="navbar-left">
        <div className="brand-logo">
          <div className="logo-icon-wrap">
            <Sparkles className="logo-sparkle" size={20} />
            <BookOpen size={24} className="logo-icon" />
          </div>
          <div className="brand-text">
            <span className="brand-title">EduGraph<span className="accent-dot">.AI</span></span>
            <span className="brand-subtitle">Knowledge-Driven Learning</span>
          </div>
        </div>

        {/* Active Role Indicator */}
        <div className="role-switcher-container">
          <span className="role-label">Authenticated Role:</span>
          <div className="role-indicator-badge">
            {role === 'teacher' ? (
              <span className="active-role-pill teacher-pill">
                <ShieldCheck size={15} />
                <span>Faculty Portal</span>
              </span>
            ) : (
              <span className="active-role-pill student-pill">
                <GraduationCap size={15} />
                <span>Student Portal</span>
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="navbar-right">
        <div className="search-pill">
          <Search size={16} className="search-icon" />
          <input 
            type="text" 
            placeholder={role === 'teacher' ? "Search course documents, syllabus, nodes..." : "Search study concepts, chapters, notes..."}
            className="search-input" 
          />
        </div>

        {/* Teacher-only upload button */}
        {role === 'teacher' && (
          <button 
            type="button" 
            className="quick-upload-btn"
            onClick={onOpenUploadModal}
            id="navbar-upload-pdf-btn"
          >
            <span>+ Upload PDF</span>
          </button>
        )}

        {/* Profile Card & Logout */}
        <div className="profile-badge">
          <div className="avatar">
            {user?.avatar || (role === 'teacher' ? 'AM' : 'SC')}
          </div>
          <div className="user-info">
            <span className="user-name">
              {user?.name || (role === 'teacher' ? 'Prof. Alex Mercer' : 'Sarah Chen')}
            </span>
            <span className="user-role-tag">
              {role === 'teacher' ? 'Senior Faculty' : 'Enrolled Student'}
            </span>
          </div>

          <button 
            type="button" 
            className="logout-action-btn"
            onClick={logout}
            title="Sign out of account"
            id="logout-btn"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
}
