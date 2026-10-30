import React from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  Share2, 
  GitMerge, 
  Layers, 
  BookMarked, 
  HelpCircle,
  UploadCloud,
  ChevronRight,
  Database,
  Network
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, currentRole, onOpenUploadModal }) {
  // Faculty Workspace Navigation Sections
  const teacherMenuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'course-content', label: 'Course Content', icon: FileText, badge: 'PDF' },
    { id: 'content-chunks', label: 'Content Chunks', icon: Database, badge: 'JSON' },
    { id: 'mapped-concepts', label: 'Mapped Concepts', icon: Share2, badge: 'JSON' },
    { id: 'concept-chunk-map', label: 'Concept Chunk Map', icon: GitMerge, badge: 'JSON' },
    { id: 'knowledge-graph', label: 'View Knowledge Graph', icon: Network, badge: 'GRAPH' },
  ];

  const studentMenuItems = [
    { id: 'my-learning', label: 'My Enrolled Courses', icon: BookMarked },
    { id: 'study-materials', label: 'Course Materials & PDFs', icon: FileText },
    { id: 'concept-map', label: 'Interactive Concept Map', icon: Share2 },
    { id: 'ai-tutor', label: 'AI Tutor & Doubts', icon: HelpCircle },
  ];

  const menuItems = currentRole === 'teacher' ? teacherMenuItems : studentMenuItems;

  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-section-title">
        {currentRole === 'teacher' ? 'Faculty Workspace' : 'Student Workspace'}
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <div className="nav-item-left">
                <Icon size={18} className="nav-item-icon" />
                <span className="nav-item-label">{item.label}</span>
              </div>
              {item.badge && (
                <span className={`nav-badge-pill ${item.badge === 'JSON' ? 'badge-json' : ''}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {currentRole === 'teacher' && (
        <div className="sidebar-upload-card">
          <div className="upload-card-glow"></div>
          <div className="upload-card-content">
            <div className="upload-icon-circle">
              <UploadCloud size={20} />
            </div>
            <h4>Ingest Batch PDFs</h4>
            <p>Upload multiple course PDFs at once to extract chunks and concept graphs.</p>
            <button 
              type="button" 
              className="sidebar-upload-btn"
              onClick={onOpenUploadModal}
            >
              <span>+ Add Multiple PDFs</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      <div className="sidebar-footer">
        <div className="system-status-indicator">
          <span className="status-dot-pulsing"></span>
          <span className="status-text">JSON Pipeline Connected</span>
        </div>
      </div>
    </aside>
  );
}
