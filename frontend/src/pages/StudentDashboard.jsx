import React from 'react';
import StudentOverview from '../components/student/StudentOverview';

export default function StudentDashboard({ courses, materials, onSwitchToTeacher }) {
  return (
    <div className="student-page-container">
      <StudentOverview 
        courses={courses} 
        materials={materials} 
        onSwitchToTeacher={onSwitchToTeacher} 
      />
    </div>
  );
}
