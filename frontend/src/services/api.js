/**
 * FastAPI REST API Client for AutoHKG & Cognitive-RAG Adaptive Learning Server
 * Handles JWT authentication, Teacher AutoHKG pipeline, Student BKT, and Knowledge Graph API.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const TOKEN_KEY = 'edugraph_jwt_token';
export const USER_KEY = 'edugraph_auth_user';

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (err) {
    console.error('Failed to read token from localStorage', err);
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (err) {
    console.error('Failed to save token to localStorage', err);
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (err) {
    console.error('Failed to read user from localStorage', err);
    return null;
  }
}

export function setStoredUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  } catch (err) {
    console.error('Failed to save user to localStorage', err);
  }
}

/**
 * Base HTTP request helper
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = { ...options.headers };

  const token = getStoredToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Do not set Content-Type if sending FormData (browser automatically sets boundary)
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Unauthorized: token might be expired
    console.warn('Received 401 Unauthorized from backend');
  }

  const contentType = response.headers.get('content-type') || '';
  let data;
  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = (data && data.detail) || (typeof data === 'string' ? data : `HTTP ${response.status}`);
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

// ==========================================
// 1. Health API
// ==========================================
export const healthApi = {
  checkHealth: () => request('/api/health', { method: 'GET' }),
};

// ==========================================
// 2. Authentication API (/api/v1/auth)
// ==========================================
export const authApi = {
  register: ({ email, password, full_name, role }) =>
    request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, role }),
    }),

  login: ({ email, password }) =>
    request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  getMe: () => request('/api/v1/auth/me', { method: 'GET' }),
};

// ==========================================
// 3. Teacher API (/api/v1/teacher)
// ==========================================
export const teacherApi = {
  /**
   * Upload textbook PDF
   * @param {File} file - PDF file binary
   * @param {string} title - Course title
   * @param {string} description - Optional description
   */
  uploadPdf: (file, title, description = '') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    if (description) {
      formData.append('description', description);
    }
    return request('/api/v1/teacher/upload', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Start the 7-stage AutoHKG pipeline in background
   * @param {string} courseId
   */
  startPipeline: (courseId) =>
    request(`/api/v1/teacher/pipeline/start/${courseId}`, {
      method: 'POST',
    }),

  /**
   * Poll pipeline progress (stages, percentages, logs)
   * @param {string} taskId
   */
  getPipelineStatus: (taskId) =>
    request(`/api/v1/teacher/pipeline/status/${taskId}`, {
      method: 'GET',
    }),

  /**
   * List all teacher courses
   */
  getCourses: () =>
    request('/api/v1/teacher/courses', {
      method: 'GET',
    }),

  /**
   * Get knowledge graph nodes & edges for graph visualizer
   * @param {string} courseId
   */
  getKnowledgeGraph: (courseId) =>
    request(`/api/v1/teacher/knowledge-graph/${courseId}`, {
      method: 'GET',
    }),

  /**
   * Override concept relationships (Human-in-the-loop curation)
   * @param {string} courseId
   * @param {object} payload - { concept_name, coarse_grained_category, prerequisites }
   */
  overrideConcept: (courseId, payload) =>
    request(`/api/v1/teacher/knowledge-graph/${courseId}/concept`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
};

// ==========================================
// 4. Student API (/api/v1/student)
// ==========================================
export const studentApi = {
  /**
   * List available courses with completed knowledge graphs
   */
  getCourses: () =>
    request('/api/v1/student/courses', {
      method: 'GET',
    }),

  /**
   * Get topological prerequisite learning path with concept mastery statuses
   * @param {string} courseId
   */
  getLearningPath: (courseId) =>
    request(`/api/v1/student/learning-path/${courseId}`, {
      method: 'GET',
    }),

  /**
   * Get dynamic Cognitive-RAG quiz question
   * @param {string} courseId
   * @param {string} [concept] - Optional specific concept name
   */
  getNextQuestion: (courseId, concept = null) => {
    const query = concept ? `?concept=${encodeURIComponent(concept)}` : '';
    return request(`/api/v1/student/quiz/next-question/${courseId}${query}`, {
      method: 'GET',
    });
  },

  /**
   * Submit quiz answer and trigger Bayesian Knowledge Tracing (BKT) update
   * @param {object} payload
   */
  submitQuizAnswer: (payload) =>
    request('/api/v1/student/quiz/submit-answer', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Get student mastery heatmap overview across all concepts
   * @param {string} courseId
   */
  getMasteryHeatmap: (courseId) =>
    request(`/api/v1/student/mastery/${courseId}`, {
      method: 'GET',
    }),
};

// ==========================================
// 5. Graph API (/api/v1/graph)
// ==========================================
export const graphApi = {
  getRawHtmlUrl: () => `${API_BASE}/api/v1/graph/raw-html`,

  getCourseRawHtmlUrl: (courseId) => `${API_BASE}/api/v1/graph/${courseId}/raw-html`,

  getGmlUrl: (courseId) => `${API_BASE}/api/v1/graph/${courseId}/gml`,

  getNeighborhood: (courseId, conceptName) =>
    request(`/api/v1/graph/${courseId}/concept-neighborhood/${encodeURIComponent(conceptName)}`, {
      method: 'GET',
    }),
};
