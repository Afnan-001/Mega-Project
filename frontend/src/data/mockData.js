export const initialCourses = [
  { id: 'cs301', code: 'CS-301', name: 'Advanced Data Structures & Algorithms', department: 'Computer Science', activeStudents: 74 },
  { id: 'ai402', code: 'AI-402', name: 'Knowledge Graphs & Multi-Agent Systems', department: 'Artificial Intelligence', activeStudents: 52 },
  { id: 'db201', code: 'DB-201', name: 'Database Management & Distributed Systems', department: 'Information Systems', activeStudents: 89 },
];

export const initialMaterials = [
  {
    id: 'mat-101',
    courseId: 'ai402',
    courseName: 'AI-402: Knowledge Graphs',
    title: 'Chapter 04 - Hierarchical Knowledge Extraction.pdf',
    fileName: 'hierarchical_knowledge_extraction_v2.pdf',
    fileSize: '4.8 MB',
    pages: 42,
    uploadedAt: '2026-10-17 14:20',
    status: 'indexed', // 'uploading' | 'processing' | 'indexed' | 'failed'
    statusMessage: 'Knowledge Graph Generated (128 Concepts, 312 Relations)',
    modules: ['Knowledge Representation', 'Concept Hierarchy', 'Triple Extraction'],
    conceptsExtracted: 128,
    relationsExtracted: 312,
  },
  {
    id: 'mat-102',
    courseId: 'ai402',
    courseName: 'AI-402: Knowledge Graphs',
    title: 'Lecture 08 - Graph Neural Networks & Embeddings.pdf',
    fileName: 'gnn_embeddings_lecture8.pdf',
    fileSize: '7.2 MB',
    pages: 58,
    uploadedAt: '2026-10-18 09:15',
    status: 'indexed',
    statusMessage: 'Knowledge Graph Generated (85 Concepts, 194 Relations)',
    modules: ['GNN Basics', 'Node2Vec', 'Relation Prediction'],
    conceptsExtracted: 85,
    relationsExtracted: 194,
  },
  {
    id: 'mat-103',
    courseId: 'cs301',
    courseName: 'CS-301: Advanced Data Structures',
    title: 'Module 02 - Red-Black Trees and B-Trees.pdf',
    fileName: 'balanced_search_trees_curriculum.pdf',
    fileSize: '3.1 MB',
    pages: 31,
    uploadedAt: '2026-10-18 11:40',
    status: 'processing',
    statusMessage: 'Extracting semantic chunks and entity links...',
    modules: ['Balanced BST', 'B-Tree Splitting', 'Amortized Analysis'],
    conceptsExtracted: 46,
    relationsExtracted: 92,
  },
  {
    id: 'mat-104',
    courseId: 'db201',
    courseName: 'DB-201: Database Management',
    title: 'Chapter 06 - Concurrency Control & ACID Protocols.pdf',
    fileName: 'concurrency_control_protocols.pdf',
    fileSize: '5.4 MB',
    pages: 49,
    uploadedAt: '2026-10-16 16:30',
    status: 'indexed',
    statusMessage: 'Knowledge Graph Generated (94 Concepts, 215 Relations)',
    modules: ['Strict 2PL', 'Timestamp Ordering', 'Deadlock Detection'],
    conceptsExtracted: 94,
    relationsExtracted: 215,
  }
];

export const teacherStats = {
  totalCourses: 3,
  uploadedPdfs: 12,
  processedPages: 418,
  extractedConcepts: 842,
  activeEnrolledStudents: 215,
  accuracyRate: '98.4%'
};
