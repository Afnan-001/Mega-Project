import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import Navbar from './components/common/Navbar';
import Sidebar from './components/common/Sidebar';
import TeacherDashboard from './pages/TeacherDashboard';
import StudentDashboard from './pages/StudentDashboard';
import { initialCourses, initialMaterials } from './data/mockData';
import { ShieldAlert, ArrowRight } from 'lucide-react';
import './styles/dashboard.css';

function MainAppContent() {
  const { user, isAuthenticated, role, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [courses] = useState(initialCourses);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Initialize materials from localStorage or initial mock data
  const [materials, setMaterials] = useState(() => {
    try {
      const saved = localStorage.getItem('edugraph_materials');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error('Failed to load materials from localStorage', e);
    }
    return initialMaterials;
  });

  useEffect(() => {
    try {
      localStorage.setItem('edugraph_materials', JSON.stringify(materials));
    } catch (e) {
      console.error('Failed to save materials to localStorage', e);
    }
  }, [materials]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  const handleAddMaterial = (newMaterial) => {
    // Role protection check: only teacher can add materials
    if (role !== 'teacher') {
      showToast('❌ Unauthorized: Only faculty members can upload course content.');
      return;
    }
    setMaterials((prev) => [newMaterial, ...prev]);
    showToast(`✓ Ingested "${newMaterial.title}" via AutoHKG pipeline!`);
  };

  const handleDeleteMaterial = (id) => {
    if (role !== 'teacher') {
      showToast('❌ Unauthorized: Only faculty members can delete course content.');
      return;
    }
    const itemToDelete = materials.find((m) => m.id === id);
    if (window.confirm(`Are you sure you want to remove "${itemToDelete?.title || 'this document'}"?`)) {
      setMaterials((prev) => prev.filter((m) => m.id !== id));
      showToast(`Removed "${itemToDelete?.title || 'document'}" from curriculum.`);
    }
  };

  // If not authenticated, always show LoginPage as the starting point
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="app-layout">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast-notification-banner glass-panel animate-fade-in">
          <span>{toastMessage}</span>
          <button 
            type="button" 
            className="toast-close"
            onClick={() => setToastMessage(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Navbar with User Profile & Role Info */}
      <Navbar 
        onOpenUploadModal={() => {
          if (role === 'teacher') {
            setIsUploadModalOpen(true);
          } else {
            showToast('❌ Unauthorized: Students cannot access course upload tools.');
          }
        }}
      />

      <div className="main-wrapper">
        {/* Contextual Sidebar strictly matching user role */}
        <Sidebar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab}
          currentRole={role}
          onOpenUploadModal={() => {
            if (role === 'teacher') {
              setIsUploadModalOpen(true);
            }
          }}
        />

        {/* Protected Dashboard Content */}
        <main className="content-area">
          {role === 'teacher' ? (
            <TeacherDashboard 
              courses={courses}
              materials={materials}
              onAddMaterial={handleAddMaterial}
              onDeleteMaterial={handleDeleteMaterial}
              isUploadModalOpen={isUploadModalOpen}
              setIsUploadModalOpen={setIsUploadModalOpen}
              activeTab={activeTab}
              setActiveTab={setActiveTab}
            />
          ) : role === 'student' ? (
            <StudentDashboard 
              courses={courses}
              materials={materials}
              onSwitchToTeacher={() => {
                // When student tries to switch to teacher, require login as teacher
                logout();
              }}
            />
          ) : (
            <div className="unauthorized-access-banner glass-panel">
              <ShieldAlert size={36} className="text-rose" />
              <h3>Unauthorized Role Detected</h3>
              <p>Your session does not have permission to view this resource.</p>
              <button type="button" className="btn-secondary" onClick={logout}>
                Return to Login
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
}
