import React, { useState } from 'react';
import StudentOverview from '../components/student/StudentOverview';
import StudentMaterialsView from '../components/student/StudentMaterialsView';
import StudentConceptMapView from '../components/student/StudentConceptMapView';
import StudentAiTutorView from '../components/student/StudentAiTutorView';
import StudentQuizHistoryView from '../components/student/StudentQuizHistoryView';
import CognitiveRagQuizModal from '../components/student/CognitiveRagQuizModal';

export default function StudentDashboard({ 
  courses = [], 
  coursesLoading = false, 
  materials = [], 
  activeTab = 'my-learning',
  setActiveTab,
  onSwitchToTeacher 
}) {
  const [selectedConceptForTutor, setSelectedConceptForTutor] = useState(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const [quizModal, setQuizModal] = useState({
    isOpen: false,
    conceptName: null,
    courseId: null,
  });

  const handleAskTutor = (concept) => {
    setSelectedConceptForTutor(concept || null);
    if (setActiveTab) {
      setActiveTab('ai-tutor');
    }
  };

  const handleOpenConceptMap = () => {
    if (setActiveTab) {
      setActiveTab('concept-map');
    }
  };

  // Map 'dashboard' tab to 'my-learning' for default entry
  const normalizedTab = activeTab === 'dashboard' ? 'my-learning' : activeTab;

  return (
    <div className="student-page-container">
      {/* Tab 1: My Enrolled Courses & Topological Learning Path */}
      {normalizedTab === 'my-learning' && (
        <StudentOverview 
          courses={courses} 
          coursesLoading={coursesLoading}
          materials={materials} 
          onSwitchToTeacher={onSwitchToTeacher}
          onOpenConceptMap={handleOpenConceptMap}
          onAskTutor={handleAskTutor}
        />
      )}

      {/* Tab 2: Past Questions, Results & Grounded Source Context */}
      {normalizedTab === 'quiz-history' && (
        <StudentQuizHistoryView
          courses={courses}
          refreshTrigger={historyRefreshKey}
          onAskTutor={handleAskTutor}
          onTakeQuiz={(concept, cId) => setQuizModal({
            isOpen: true,
            conceptName: concept,
            courseId: cId || courses[0]?.id,
          })}
        />
      )}

      {/* Tab 3: Course Materials & Curriculum PDFs */}
      {normalizedTab === 'study-materials' && (
        <StudentMaterialsView 
          courses={courses}
          materials={materials}
          onOpenConceptMap={handleOpenConceptMap}
          onAskTutor={handleAskTutor}
        />
      )}

      {/* Tab 4: Interactive Concept Map (Knowledge Graph) */}
      {normalizedTab === 'concept-map' && (
        <StudentConceptMapView 
          courses={courses}
          onAskTutor={handleAskTutor}
          onTakeQuiz={(concept, cId) => setQuizModal({
            isOpen: true,
            conceptName: concept,
            courseId: cId || courses[0]?.id
          })}
        />
      )}

      {/* Tab 5: AI Tutor & Doubts Desk */}
      {normalizedTab === 'ai-tutor' && (
        <StudentAiTutorView 
          courses={courses}
          initialConcept={selectedConceptForTutor}
          onClearConcept={() => setSelectedConceptForTutor(null)}
        />
      )}

      {/* Global Quiz Modal for Concept Map & History Launches */}
      {quizModal.isOpen && (
        <CognitiveRagQuizModal
          isOpen={quizModal.isOpen}
          onClose={() => setQuizModal({ isOpen: false, conceptName: null, courseId: null })}
          courseId={quizModal.courseId || courses[0]?.id}
          conceptName={quizModal.conceptName}
          onMasteryUpdated={() => setHistoryRefreshKey((k) => k + 1)}
        />
      )}
    </div>
  );
}
