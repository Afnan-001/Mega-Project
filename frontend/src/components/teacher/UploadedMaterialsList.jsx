import React, { useState } from 'react';
import { 
  FileText, 
  Share2, 
  Calendar, 
  Trash2, 
  ExternalLink, 
  CheckCircle2, 
  Loader2, 
  AlertTriangle,
  Search,
  Filter,
  Eye,
  Layers,
  ChevronDown
} from 'lucide-react';

export default function UploadedMaterialsList({ 
  materials, 
  onDeleteMaterial, 
  onSelectMaterial,
  onOpenUploadModal 
}) {
  const [selectedCourseFilter, setSelectedCourseFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Extract unique courses from materials
  const coursesList = [
    { id: 'all', name: 'All Courses' },
    ...Array.from(new Set(materials.map(m => m.courseId))).map(cId => {
      const mat = materials.find(m => m.courseId === cId);
      return { id: cId, name: mat?.courseName || cId };
    })
  ];

  const filteredMaterials = materials.filter((item) => {
    const matchesCourse = selectedCourseFilter === 'all' || item.courseId === selectedCourseFilter;
    const matchesSearch = 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.courseName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.modules && item.modules.some(m => m.toLowerCase().includes(searchQuery.toLowerCase())));
    return matchesCourse && matchesSearch;
  });

  const getStatusBadge = (status, msg) => {
    switch (status) {
      case 'indexed':
        return (
          <span className="status-badge status-indexed" title={msg}>
            <CheckCircle2 size={13} />
            <span>KG Indexed</span>
          </span>
        );
      case 'processing':
        return (
          <span className="status-badge status-processing" title={msg}>
            <Loader2 size={13} className="spin-icon" />
            <span>Extracting Triples</span>
          </span>
        );
      case 'failed':
        return (
          <span className="status-badge status-failed" title={msg}>
            <AlertTriangle size={13} />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="status-badge status-queued">
            <span>Uploaded</span>
          </span>
        );
    }
  };

  return (
    <div className="materials-container glass-panel">
      {/* Header & Controls */}
      <div className="materials-header">
        <div className="header-titles">
          <h3>Submitted Course Materials & Curriculum PDFs</h3>
          <p>Manage uploaded textbooks, research papers, and lecture slides processed by the graph engine</p>
        </div>

        <div className="materials-actions">
          <button 
            type="button" 
            className="btn-primary" 
            onClick={onOpenUploadModal}
          >
            <span>+ Submit New PDF</span>
          </button>
        </div>
      </div>

      <div className="materials-filter-bar">
        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search by title, module, or topic..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-dropdown-wrapper">
          <Filter size={15} className="filter-icon" />
          <select 
            value={selectedCourseFilter} 
            onChange={(e) => setSelectedCourseFilter(e.target.value)}
            className="filter-select"
          >
            {coursesList.map((course) => (
              <option key={course.id} value={course.id}>
                {course.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Materials Table / List */}
      <div className="materials-table-wrapper">
        {filteredMaterials.length === 0 ? (
          <div className="empty-materials-state">
            <FileText size={48} className="empty-icon" />
            <h4>No course materials found</h4>
            <p>
              {searchQuery 
                ? "No uploaded PDFs match your search query." 
                : "No course PDFs have been submitted for this selection yet."}
            </p>
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={onOpenUploadModal}
            >
              Upload First Course PDF
            </button>
          </div>
        ) : (
          <table className="materials-table">
            <thead>
              <tr>
                <th>Document & Source File</th>
                <th>Course & Module</th>
                <th>Pages & Size</th>
                <th>Status & KG Extraction</th>
                <th>Concept Triples</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredMaterials.map((item) => (
                <tr key={item.id} className="materials-row">
                  <td>
                    <div className="doc-cell-content">
                      <div className="pdf-icon-badge">
                        <FileText size={18} />
                      </div>
                      <div className="doc-details">
                        <span className="doc-title">{item.title}</span>
                        <span className="doc-filename">{item.fileName}</span>
                      </div>
                    </div>
                  </td>

                  <td>
                    <div className="course-module-cell">
                      <span className="course-tag">{item.courseName}</span>
                      {item.modules && item.modules.length > 0 && (
                        <span className="module-tag">{item.modules[0]}</span>
                      )}
                    </div>
                  </td>

                  <td>
                    <div className="size-cell">
                      <span className="page-count">{item.pages} pages</span>
                      <span className="file-size-text">{item.fileSize}</span>
                    </div>
                  </td>

                  <td>
                    <div className="status-cell">
                      {getStatusBadge(item.status, item.statusMessage)}
                      <div className="timestamp-text">
                        <Calendar size={12} />
                        <span>{item.uploadedAt}</span>
                      </div>
                    </div>
                  </td>

                  <td>
                    <div className="triples-stat-cell">
                      <div className="triple-metric">
                        <Share2 size={13} className="text-indigo" />
                        <span><strong>{item.conceptsExtracted || 0}</strong> Concepts</span>
                      </div>
                      <div className="triple-submetric">
                        <span>{item.relationsExtracted || 0} Relations</span>
                      </div>
                    </div>
                  </td>

                  <td>
                    <div className="row-actions text-right">
                      <button 
                        type="button" 
                        className="action-icon-btn view-btn"
                        title="View Concepts and Extracted Nodes"
                        onClick={() => onSelectMaterial && onSelectMaterial(item)}
                      >
                        <Eye size={16} />
                      </button>
                      <button 
                        type="button" 
                        className="action-icon-btn delete-btn"
                        title="Delete Document"
                        onClick={() => onDeleteMaterial(item.id)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
