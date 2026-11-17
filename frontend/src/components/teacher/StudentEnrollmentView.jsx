import React, { useState, useEffect, useMemo } from 'react';
import { 
  Users, 
  UserCheck, 
  UserPlus, 
  UserMinus, 
  Search, 
  Filter, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  BookOpen, 
  Clock, 
  GraduationCap, 
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { teacherApi } from '../../services/api';

export default function StudentEnrollmentView({ 
  courses = [], 
  selectedCourseId: parentCourseId, 
  onSelectCourse 
}) {
  const [selectedCourseId, setSelectedCourseId] = useState(
    parentCourseId || courses[0]?.id || ''
  );
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [batchLoading, setBatchLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState('all'); // 'all' | 'enrolled' | 'not_enrolled'
  const [alert, setAlert] = useState(null);

  // Sync with prop changes
  useEffect(() => {
    if (parentCourseId && parentCourseId !== selectedCourseId) {
      setSelectedCourseId(parentCourseId);
    } else if (!selectedCourseId && courses.length > 0) {
      setSelectedCourseId(courses[0].id);
    }
  }, [parentCourseId, courses, selectedCourseId]);

  // Fetch students from database (with optional course enrollment status)
  const fetchStudents = async (cId = selectedCourseId) => {
    setLoading(true);
    setAlert(null);
    try {
      const activeCId = cId || (courses.length > 0 ? courses[0].id : null);
      const data = await teacherApi.getStudents(activeCId || null);
      setStudents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load students roster:', err);
      setAlert({
        type: 'error',
        message: err.message || 'Failed to load students from database.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const activeCId = selectedCourseId || (courses.length > 0 ? courses[0].id : null);
    fetchStudents(activeCId);
  }, [selectedCourseId, courses.length]);

  const currentCourse = useMemo(() => {
    return courses.find(c => c.id === selectedCourseId) || courses[0] || null;
  }, [courses, selectedCourseId]);

  // Statistics
  const totalStudents = students.length;
  const enrolledStudents = useMemo(() => students.filter(s => s.is_enrolled), [students]);
  const unenrolledStudents = useMemo(() => students.filter(s => !s.is_enrolled), [students]);
  const enrollmentRate = totalStudents > 0 
    ? Math.round((enrolledStudents.length / totalStudents) * 100) 
    : 0;

  // Filtered list
  const filteredStudents = useMemo(() => {
    return students.filter((s) => {
      // Tab filter
      if (filterTab === 'enrolled' && !s.is_enrolled) return false;
      if (filterTab === 'not_enrolled' && s.is_enrolled) return false;

      // Search query filter
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const matchName = (s.full_name || '').toLowerCase().includes(q);
      const matchEmail = (s.email || '').toLowerCase().includes(q);
      return matchName || matchEmail;
    });
  }, [students, filterTab, searchQuery]);

  // Handle single student enrollment toggle
  const handleToggleEnrollment = async (student) => {
    if (!selectedCourseId) return;
    const isEnrolling = !student.is_enrolled;
    const sId = student.id;

    setActionLoading(prev => ({ ...prev, [sId]: true }));
    setAlert(null);

    try {
      if (isEnrolling) {
        await teacherApi.enrollStudent(selectedCourseId, sId);
        setStudents(prev => prev.map(s => s.id === sId ? { ...s, is_enrolled: true, enrolled_at: new Date().toISOString() } : s));
        setAlert({
          type: 'success',
          message: `Successfully enrolled ${student.full_name} into ${currentCourse?.title || 'course'}.`,
        });
      } else {
        await teacherApi.unenrollStudent(selectedCourseId, sId);
        setStudents(prev => prev.map(s => s.id === sId ? { ...s, is_enrolled: false, enrolled_at: null } : s));
        setAlert({
          type: 'success',
          message: `Unenrolled ${student.full_name} from ${currentCourse?.title || 'course'}.`,
        });
      }
    } catch (err) {
      console.error('Enrollment action failed:', err);
      setAlert({
        type: 'error',
        message: err.message || `Failed to update enrollment for ${student.full_name}.`,
      });
    } finally {
      setActionLoading(prev => ({ ...prev, [sId]: false }));
    }
  };

  // Handle batch enroll all
  const handleEnrollAll = async () => {
    if (!selectedCourseId) return;
    setBatchLoading(true);
    setAlert(null);
    try {
      const res = await teacherApi.enrollAllStudents(selectedCourseId);
      await fetchStudents(selectedCourseId);
      setAlert({
        type: 'success',
        message: res.message || `All registered students have been enrolled into ${currentCourse?.title || 'the course'}!`,
      });
    } catch (err) {
      console.error('Batch enrollment failed:', err);
      setAlert({
        type: 'error',
        message: err.message || 'Failed to enroll all students.',
      });
    } finally {
      setBatchLoading(false);
    }
  };

  const getInitials = (name) => {
    if (!name) return 'S';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  };

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '—';
    }
  };

  return (
    <div className="student-enrollment-view animate-fade-in">
      {/* View Header */}
      <div className="materials-header" style={{ marginBottom: '1.5rem' }}>
        <div className="header-titles">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="faculty-badge">
              <GraduationCap size={14} className="text-accent" />
              <span>Student Roster & Course Enrollment</span>
            </span>
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fff', margin: '4px 0' }}>
            Course Student Enrollment Management
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            View all registered students in the database and enroll them into active courses with a single click.
          </p>
        </div>

        {/* Course Selector Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
            <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Target Course
            </span>
            <select
              value={selectedCourseId}
              onChange={(e) => {
                setSelectedCourseId(e.target.value);
                if (onSelectCourse) onSelectCourse(e.target.value);
              }}
              className="custom-select"
              style={{
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#e2e8f0',
                border: '1px solid rgba(99, 102, 241, 0.35)',
                borderRadius: '8px',
                padding: '7px 14px',
                fontSize: '13px',
                fontWeight: 600,
                outline: 'none',
                minWidth: '240px',
                cursor: 'pointer',
              }}
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title || c.name || `Course ${c.id}`}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="btn-ghost-hero"
            onClick={() => fetchStudents(selectedCourseId)}
            title="Refresh student roster"
            style={{ padding: '8px 12px', marginTop: '16px' }}
          >
            <RefreshCw size={15} className={loading ? 'spin-icon' : ''} />
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div 
        style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem',
          marginBottom: '1.5rem' 
        }}
      >
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Registered Students</span>
            <Users size={16} style={{ color: '#818cf8' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff' }}>{totalStudents}</div>
          <span style={{ fontSize: '11px', color: '#64748b' }}>In system database</span>
        </div>

        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', color: '#6ee7b7', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Enrolled Students</span>
            <UserCheck size={16} style={{ color: '#10b981' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#10b981' }}>{enrolledStudents.length}</div>
          <span style={{ fontSize: '11px', color: '#64748b' }}>Active in this course</span>
        </div>

        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', color: '#fcd34d', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Not Enrolled</span>
            <UserMinus size={16} style={{ color: '#f59e0b' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f59e0b' }}>{unenrolledStudents.length}</div>
          <span style={{ fontSize: '11px', color: '#64748b' }}>Available to enroll</span>
        </div>

        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', color: '#c7d2fe', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Enrollment Rate</span>
            <Sparkles size={16} style={{ color: '#6366f1' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#818cf8' }}>{enrollmentRate}%</div>
          <span style={{ fontSize: '11px', color: '#64748b' }}>Student body coverage</span>
        </div>
      </div>

      {/* Alert Banner if present */}
      {alert && (
        <div 
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 16px',
            borderRadius: '10px',
            marginBottom: '1.25rem',
            background: alert.type === 'error' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.12)',
            border: `1px solid ${alert.type === 'error' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
            color: alert.type === 'error' ? '#fca5a5' : '#6ee7b7',
            fontSize: '13px',
          }}
        >
          {alert.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          <span style={{ flex: 1 }}>{alert.message}</span>
          <button 
            type="button" 
            onClick={() => setAlert(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '14px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Table & Controls Container */}
      <div className="materials-container glass-panel" style={{ padding: '1.5rem' }}>
        {/* Filter and Action Bar */}
        <div className="materials-filter-bar" style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '1.25rem' }}>
          {/* Search Box */}
          <div className="search-box" style={{ minWidth: '260px', flex: 1 }}>
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by student name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button 
                type="button" 
                onClick={() => setSearchQuery('')}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '12px' }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Filter Tabs */}
          <div style={{ display: 'flex', gap: '4px', background: 'rgba(15, 23, 42, 0.6)', padding: '4px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <button
              type="button"
              onClick={() => setFilterTab('all')}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: filterTab === 'all' ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                color: filterTab === 'all' ? '#fff' : '#94a3b8',
                transition: 'all 0.15s ease',
              }}
            >
              All Students ({totalStudents})
            </button>
            <button
              type="button"
              onClick={() => setFilterTab('enrolled')}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: filterTab === 'enrolled' ? 'rgba(16, 185, 129, 0.25)' : 'transparent',
                color: filterTab === 'enrolled' ? '#34d399' : '#94a3b8',
                transition: 'all 0.15s ease',
              }}
            >
              Enrolled ({enrolledStudents.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterTab('not_enrolled')}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: filterTab === 'not_enrolled' ? 'rgba(245, 158, 11, 0.25)' : 'transparent',
                color: filterTab === 'not_enrolled' ? '#fbbf24' : '#94a3b8',
                transition: 'all 0.15s ease',
              }}
            >
              Not Enrolled ({unenrolledStudents.length})
            </button>
          </div>

          {/* Enroll All Button */}
          <button
            type="button"
            className="btn-primary"
            onClick={handleEnrollAll}
            disabled={batchLoading || unenrolledStudents.length === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 18px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: (batchLoading || unenrolledStudents.length === 0) ? 'not-allowed' : 'pointer',
              opacity: (batchLoading || unenrolledStudents.length === 0) ? 0.6 : 1,
              background: 'linear-gradient(135deg, #4f46e5, #06b6d4)',
              color: '#fff',
              border: 'none',
              boxShadow: '0 4px 14px rgba(79, 70, 229, 0.35)',
            }}
          >
            {batchLoading ? (
              <Loader2 size={15} className="spin-icon" />
            ) : (
              <UserPlus size={15} />
            )}
            <span>
              {batchLoading ? 'Enrolling Students...' : `+ Enroll All Students (${unenrolledStudents.length})`}
            </span>
          </button>
        </div>

        {/* Students Table */}
        <div className="materials-table-wrapper">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#94a3b8' }}>
              <Loader2 size={28} className="spin-icon" style={{ margin: '0 auto 12px' }} />
              <p>Fetching registered students from database...</p>
            </div>
          ) : filteredStudents.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3.5rem 1rem', color: '#94a3b8' }}>
              <Users size={36} style={{ color: '#475569', margin: '0 auto 12px' }} />
              <h4 style={{ color: '#e2e8f0', fontSize: '1rem', marginBottom: '4px' }}>
                {totalStudents === 0 
                  ? 'No students registered in the database yet'
                  : 'No students match your filter criteria'}
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#64748b', maxWidth: '400px', margin: '0 auto' }}>
                {totalStudents === 0 
                  ? 'When students create accounts and sign in, their profile will automatically appear in this roster.'
                  : 'Try clearing your search query or selecting "All Students" to see the full roster.'}
              </p>
            </div>
          ) : (
            <table className="materials-table">
              <thead>
                <tr>
                  <th style={{ width: '40%' }}>Student</th>
                  <th style={{ width: '20%' }}>Registered On</th>
                  <th style={{ width: '20%' }}>Status in Course</th>
                  <th style={{ width: '20%', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((student) => {
                  const isEnrolled = !!student.is_enrolled;
                  const isActionBusy = !!actionLoading[student.id];

                  return (
                    <tr key={student.id} className="materials-row">
                      {/* Student Info */}
                      <td>
                        <div className="doc-cell-content" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div
                            style={{
                              width: '38px',
                              height: '38px',
                              borderRadius: '50%',
                              background: isEnrolled 
                                ? 'linear-gradient(135deg, #10b981, #06b6d4)' 
                                : 'linear-gradient(135deg, #6366f1, #a855f7)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 700,
                              fontSize: '13px',
                              color: '#fff',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                              flexShrink: 0,
                            }}
                          >
                            {getInitials(student.full_name)}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem' }}>
                              {student.full_name || 'Unnamed Student'}
                            </div>
                            <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                              {student.email}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Registered Date */}
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '0.82rem' }}>
                          <Clock size={13} style={{ color: '#64748b' }} />
                          <span>{formatDate(student.created_at)}</span>
                        </div>
                      </td>

                      {/* Enrollment Status */}
                      <td>
                        {isEnrolled ? (
                          <span 
                            className="status-badge status-indexed" 
                            title={student.enrolled_at ? `Enrolled on ${formatDate(student.enrolled_at)}` : 'Enrolled'}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px' }}
                          >
                            <CheckCircle2 size={13} />
                            <span>Enrolled</span>
                          </span>
                        ) : (
                          <span 
                            className="status-badge"
                            style={{ 
                              display: 'inline-flex', 
                              alignItems: 'center', 
                              gap: '6px', 
                              padding: '4px 10px',
                              background: 'rgba(100, 116, 139, 0.15)',
                              color: '#94a3b8',
                              border: '1px solid rgba(148, 163, 184, 0.2)'
                            }}
                          >
                            <UserMinus size={13} />
                            <span>Not Enrolled</span>
                          </span>
                        )}
                      </td>

                      {/* Action Button */}
                      <td style={{ textAlign: 'right' }}>
                        {isEnrolled ? (
                          <button
                            type="button"
                            onClick={() => handleToggleEnrollment(student)}
                            disabled={isActionBusy}
                            style={{
                              background: 'rgba(239, 68, 68, 0.12)',
                              color: '#f87171',
                              border: '1px solid rgba(239, 68, 68, 0.25)',
                              borderRadius: '6px',
                              padding: '6px 14px',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: isActionBusy ? 'not-allowed' : 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              transition: 'all 0.15s ease',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.12)';
                            }}
                          >
                            {isActionBusy ? (
                              <Loader2 size={13} className="spin-icon" />
                            ) : (
                              <UserMinus size={13} />
                            )}
                            <span>Remove</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleToggleEnrollment(student)}
                            disabled={isActionBusy}
                            style={{
                              background: 'rgba(16, 185, 129, 0.15)',
                              color: '#34d399',
                              border: '1px solid rgba(16, 185, 129, 0.35)',
                              borderRadius: '6px',
                              padding: '6px 16px',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: isActionBusy ? 'not-allowed' : 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              transition: 'all 0.15s ease',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'rgba(16, 185, 129, 0.28)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)';
                            }}
                          >
                            {isActionBusy ? (
                              <Loader2 size={13} className="spin-icon" />
                            ) : (
                              <UserPlus size={13} />
                            )}
                            <span>+ Add</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
