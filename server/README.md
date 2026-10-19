# AutoHKG & Cognitive-RAG Adaptive Learning Server

An asynchronous FastAPI REST API backend providing Role-Based Access Control (RBAC) for **Teachers** (PDF textbook ingestion, automated 7-stage AutoHKG pipeline, interactive knowledge graph curation) and **Students** (topological prerequisite learning paths, Bayesian Knowledge Tracing, and adaptive Cognitive-RAG quizzes).

All original algorithm code inside `Main/` remains **100% untouched**, imported and orchestrated cleanly by the server layer.

---

## Table of Contents
1. [Architecture & System Flow](#1-architecture--system-flow)
2. [Prerequisites & Environment Configuration](#2-prerequisites--environment-configuration)
3. [Running the Server](#3-running-the-server)
4. [Database Collections & Schemas (MongoDB + Beanie)](#4-database-collections--schemas-mongodb--beanie)
5. [Complete REST API Specification for Frontend](#5-complete-rest-api-specification-for-frontend)
   - [Authentication Endpoints (`/api/v1/auth`)](#authentication-endpoints-apiv1auth)
   - [Teacher Endpoints (`/api/v1/teacher`)](#teacher-endpoints-apiv1teacher)
   - [Student Endpoints (`/api/v1/student`)](#student-endpoints-apiv1student)
   - [Graph Endpoints (`/api/v1/graph`)](#graph-endpoints-apiv1graph)
   - [Health Endpoints (`/api/health`)](#health-endpoints-apihealth)
6. [Frontend Developer Integration Guide](#6-frontend-developer-integration-guide)
   - [Teacher UI Integration](#teacher-ui-integration-flow)
   - [Student UI Integration](#student-ui-integration-flow)
   - [Vis.js / Cytoscape Graph Rendering](#visjs--cytoscape-graph-rendering)
7. [Algorithm Engines: Cognitive-RAG & BKT](#7-algorithm-engines-cognitive-rag--bkt)
8. [Extensibility & Future Updates](#8-extensibility--future-updates)

---

## 1. Architecture & System Flow

```
                               ┌──────────────────────────────────────────────┐
                               │               Frontend Web App               │
                               │  Teacher UI (Upload, Pipeline, KG Editor)    │
                               │  Student UI (Learning Path, Quiz, Heatmap)   │
                               └──────────────────────┬───────────────────────┘
                                                      │ HTTP / REST (JWT Bearer)
                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          FastAPI Server (server/)                                        │
│                                                                                                          │
│   ┌─────────────────────────────── REST API Routers ─────────────────────────────────────────────────┐   │
│   │   /api/v1/auth         │   /api/v1/teacher       │   /api/v1/student       │   /api/v1/graph     │   │
│   └───────────┬────────────┴───────────┬─────────────┴───────────┬─────────────┴───────────┬─────────┘   │
│               │                        │                         │                         │             │
│               ▼                        ▼                         ▼                         ▼             │
│       [Security & RBAC]       [Pipeline Service]       [Cognitive-RAG & BKT]     [Graph Serializer]      │
│       (Bcrypt / PyJWT)       (BackgroundTasks runner) (Dynamic MCQ & Tracking) (Vis.js / GML format)     │
└───────────────┬────────────────────────┬─────────────────────────┬─────────────────────────┬─────────────┘
                │                        │                         │                         │
                │                        │ Reads / Writes          │ Reads Grounded Context  │
                ▼                        ▼                         ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       MongoDB Database (Motor + Beanie)                                  │
│   • users                     • courses                     • pipeline_tasks                             │
│   • content_chunks            • concepts                    • concept_chunk_mappings                     │
│   • enriched_concepts         • knowledge_graphs            • student_mastery_states                     │
│   • quiz_attempts                                                                                        │
└────────────────────────────────────────┬─────────────────────────────────────────────────────────────────┘
                                         │
                                         │ Calls without altering any code
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Untouched Algorithm Library (Main/)                                   │
│   • Main/AutoHKG/extract_and_chunk.py       • Main/AutoHKG/embed_chunks.py                               │
│   • Main/AutoHKG/extract_concepts.py        • Main/AutoHKG/map_concepts.py                               │
│   • Main/AutoHKG/clean_concepts.py          • Main/AutoHKG/enrich_concepts.py                            │
│   • Main/AutoHKG/post_process_dag.py        • Main/llm.py (Gemini multi-key rotation & Ollama)           │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites & Environment Configuration

### Requirements
- **Python 3.10+** (tested on Python 3.13)
- **MongoDB 6.0+** running locally or remotely (e.g., MongoDB Atlas)
- **Gemini API Key(s)** or local **Ollama** instance

### Environment Variables (`.env`)
Create a `.env` file in the root of the repository:

```env
# ── MongoDB ───────────────────────────────────────────────────────
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=mega_project

# ── JWT Authentication ────────────────────────────────────────────
JWT_SECRET_KEY=mega-project-super-secret-jwt-key-development-2026-secure
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── LLM Configuration ─────────────────────────────────────────────
# Supports comma-separated keys for automatic rate-limit rotation
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEYS=key1,key2,key3
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash

# ── Embedding Model ───────────────────────────────────────────────
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
```

---

## 3. Running the Server

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Verify Health & Open API Docs
- **Swagger Interactive Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Interactive Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 4. Database Collections & Schemas (MongoDB + Beanie)

The server stores all state, artifacts, and student progress in MongoDB using **Beanie ODM**:

| Collection | Model Class | Description |
| :--- | :--- | :--- |
| `users` | `UserDocument` | User credentials, roles (`teacher` \| `student`), timestamps. |
| `courses` | `CourseDocument` | Uploaded courses, textbook PDF paths, processing statuses. |
| `pipeline_tasks` | `PipelineTaskDocument` | Background AutoHKG tasks, execution stages, logs, progress (0–100%). |
| `content_chunks` | `ContentChunkDocument` | Chunks of textbook text with page numbers and dense vector embeddings. |
| `concepts` | `ConceptDocument` | Candidate and canonical technical concepts extracted from text. |
| `concept_chunk_mappings` | `ConceptChunkMappingDocument` | Grounded mappings between concepts and qualifying source chunks. |
| `enriched_concepts` | `EnrichedConceptDocument` | Category and prerequisite relationships backed by citation evidence. |
| `knowledge_graphs` | `KnowledgeGraphDocument` | Final cycle-free DAG nodes, edges, and GML graph string. |
| `student_mastery_states` | `StudentMasteryDocument` | Per-student, per-concept latent BKT mastery probability ($P(L_t) \in [0.01, 0.99]$). |
| `quiz_attempts` | `QuizAttemptDocument` | Full audit log of questions asked, options selected, correctness, and BKT updates. |

---

## 5. Complete REST API Specification for Frontend

All authenticated endpoints require the standard Bearer header:
```http
Authorization: Bearer <your_jwt_access_token>
```

---

### Authentication Endpoints (`/api/v1/auth`)

#### 1. Register User
- **Method**: `POST`
- **Path**: `/api/v1/auth/register`
- **Request Body (JSON)**:
  ```json
  {
    "email": "teacher@university.edu",
    "password": "StrongPassword123!",
    "full_name": "Dr. Sarah Connor",
    "role": "teacher"  // or "student"
  }
  ```
- **Success Response (`201 Created`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "role": "teacher",
    "user_id": "67123456789abcdef0123456",
    "full_name": "Dr. Sarah Connor"
  }
  ```

#### 2. User Login
- **Method**: `POST`
- **Path**: `/api/v1/auth/login`
- **Supports**: JSON body or OAuth2 Form Data.
- **Request Body (JSON)**:
  ```json
  {
    "email": "teacher@university.edu",
    "password": "StrongPassword123!"
  }
  ```
- **Success Response (`200 OK`)**: Same `TokenResponse` as register.

#### 3. Current User Profile
- **Method**: `GET`
- **Path**: `/api/v1/auth/me`
- **Success Response (`200 OK`)**:
  ```json
  {
    "id": "67123456789abcdef0123456",
    "email": "teacher@university.edu",
    "full_name": "Dr. Sarah Connor",
    "role": "teacher",
    "created_at": "2026-10-18T10:00:00Z"
  }
  ```

---

### Teacher Endpoints (`/api/v1/teacher`)
*Requires `teacher` role token.*

#### 1. Upload Textbook PDF
- **Method**: `POST`
- **Path**: `/api/v1/teacher/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: PDF file binary
  - `title`: string (e.g. `"Compilers: Principles & Techniques"`)
  - `description`: string (optional)
- **Success Response (`201 Created`)**:
  ```json
  {
    "id": "67123456789abcdef0123457",
    "title": "Compilers: Principles & Techniques",
    "description": "Comprehensive textbook on compiler design.",
    "teacher_id": "67123456789abcdef0123456",
    "uploaded_pdf_name": "compilers_dragon.pdf",
    "status": "ready",
    "active_task_id": null,
    "created_at": "2026-10-18T10:15:00Z"
  }
  ```

#### 2. Start AutoHKG Pipeline
- **Method**: `POST`
- **Path**: `/api/v1/teacher/pipeline/start/{course_id}`
- **Description**: Spawns the 7-stage pipeline in a background task.
- **Success Response (`200 OK`)**:
  ```json
  {
    "task_id": "67123456789abcdef0123458",
    "course_id": "67123456789abcdef0123457",
    "status": "queued",
    "message": "AutoHKG knowledge graph pipeline initiated in the background."
  }
  ```

#### 3. Check Pipeline Progress
- **Method**: `GET`
- **Path**: `/api/v1/teacher/pipeline/status/{task_id}`
- **Success Response (`200 OK`)**:
  ```json
  {
    "task_id": "67123456789abcdef0123458",
    "course_id": "67123456789abcdef0123457",
    "status": "running", // "queued" | "running" | "completed" | "failed"
    "current_stage": "ENRICHMENT", // "CHUNKING" | "NLP_CONCEPTS" | "LLM_CLEANING" | "EMBEDDING" | "MAPPING" | "ENRICHMENT" | "DAG_RESOLVE" | "COMPLETED"
    "progress_percentage": 88,
    "stage_details": {
      "stage_1_chunks": "450",
      "stage_2_raw_concepts": "230",
      "stage_3_clean_concepts": "140",
      "stage_5_grounded_concepts": "95"
    },
    "logs": [
      "[10:15:02] Started AutoHKG pipeline for course 'Compilers'",
      "[10:15:10] Stage 1 Completed: Generated 450 chunks across 180 pages (8.1s)",
      "[10:16:05] Stage 6 Completed: Enriched 95 concepts (55.0s)"
    ],
    "error_message": null,
    "started_at": "2026-10-18T10:15:02Z",
    "completed_at": null
  }
  ```

#### 4. List Teacher Courses
- **Method**: `GET`
- **Path**: `/api/v1/teacher/courses`
- **Success Response (`200 OK`)**: Array of `CourseResponse` objects.

#### 5. Get Knowledge Graph for Visualizer
- **Method**: `GET`
- **Path**: `/api/v1/teacher/knowledge-graph/{course_id}`
- **Success Response (`200 OK`)**:
  ```json
  {
    "course_id": "67123456789abcdef0123457",
    "total_nodes": 45,
    "total_edges": 68,
    "nodes": [
      { "id": "Lexical Analysis", "label": "Lexical Analysis", "type": "fine_grained_concept" },
      { "id": "Compiler Front End", "label": "Compiler Front End", "type": "coarse_grained_category" }
    ],
    "edges": [
      {
        "source": "Compiler Front End",
        "target": "Lexical Analysis",
        "relation": "CONTAINS",
        "confidence": 1.0,
        "evidence_chunk": "compilers_p12_c1",
        "evidence_text": "The front end consists of lexical analysis, syntax analysis..."
      },
      {
        "source": "Lexical Analysis",
        "target": "Syntax Analysis",
        "relation": "PREREQUISITE_FOR",
        "confidence": 0.94,
        "evidence_chunk": "compilers_p45_c2",
        "evidence_text": "Syntax analysis takes the tokens generated by lexical analysis."
      }
    ]
  }
  ```

#### 6. Override Concept Relationships (Human-in-the-Loop)
- **Method**: `PATCH`
- **Path**: `/api/v1/teacher/knowledge-graph/{course_id}/concept`
- **Request Body (JSON)**:
  ```json
  {
    "concept_name": "Syntax Analysis",
    "coarse_grained_category": ["Compiler Front End"],
    "prerequisites": ["Lexical Analysis", "Regular Expressions"]
  }
  ```
- **Success Response (`200 OK`)**: Returns the updated `GraphVisualizerResponse`.

---

### Student Endpoints (`/api/v1/student`)
*Requires `student` role token.*

#### 1. List Available Courses
- **Method**: `GET`
- **Path**: `/api/v1/student/courses`
- **Success Response (`200 OK`)**: Array of courses that have completed pipeline graphs.

#### 2. Get Topological Prerequisite Learning Path
- **Method**: `GET`
- **Path**: `/api/v1/student/learning-path/{course_id}`
- **Success Response (`200 OK`)**:
  ```json
  {
    "course_id": "67123456789abcdef0123457",
    "course_title": "Compilers: Principles & Techniques",
    "total_concepts": 32,
    "path": [
      {
        "concept_name": "Lexical Analysis",
        "node_type": "fine_grained_concept",
        "coarse_grained_category": ["Compiler Front End"],
        "prerequisites": [],
        "mastery_percentage": 78.5,
        "status": "In Progress" // "Mastered" (>=85%) | "In Progress" | "Ready to Learn" | "Locked"
      },
      {
        "concept_name": "Syntax Analysis",
        "node_type": "fine_grained_concept",
        "coarse_grained_category": ["Compiler Front End"],
        "prerequisites": ["Lexical Analysis"],
        "mastery_percentage": 10.0,
        "status": "Ready to Learn" // Unlocked because Lexical Analysis >= 70%
      },
      {
        "concept_name": "LR Parsing",
        "node_type": "fine_grained_concept",
        "coarse_grained_category": ["Compiler Front End"],
        "prerequisites": ["Syntax Analysis"],
        "mastery_percentage": 10.0,
        "status": "Locked" // Locked because Syntax Analysis < 70%
      }
    ]
  }
  ```

#### 3. Get Next Dynamic Quiz Question (Cognitive-RAG)
- **Method**: `GET`
- **Path**: `/api/v1/student/quiz/next-question/{course_id}?concept={optional_concept_name}`
- **Description**: If `concept` is omitted, the engine automatically selects the optimal unlocked concept along the student's learning frontier.
- **Success Response (`200 OK`)**:
  ```json
  {
    "question_id": "q_a1b2c3d4e5",
    "course_id": "67123456789abcdef0123457",
    "concept_name": "Lexical Analysis",
    "question_text": "Which data structure is primarily produced by lexical analysis and consumed by the syntax analyzer?",
    "options": [
      "Stream of tokens",
      "Abstract syntax tree",
      "Symbol table entry records only",
      "Target machine assembly code"
    ],
    "evidence_chunk_ids": ["compilers_p12_c1", "compilers_p14_c3"]
  }
  ```
  *(Notice: The correct option is concealed from this response payload to prevent client-side inspection).*

#### 4. Submit Quiz Answer (BKT Update)
- **Method**: `POST`
- **Path**: `/api/v1/student/quiz/submit-answer`
- **Request Body (JSON)**:
  ```json
  {
    "course_id": "67123456789abcdef0123457",
    "concept_name": "Lexical Analysis",
    "question_id": "q_a1b2c3d4e5",
    "selected_option": "Stream of tokens",
    "correct_option": "Stream of tokens",
    "question_text": "Which data structure is primarily produced by...",
    "explanation": "According to section 1.2, lexical analysis converts raw source text into a token stream.",
    "options": ["Stream of tokens", "Abstract syntax tree", "..."]
  }
  ```
- **Success Response (`200 OK`)**:
  ```json
  {
    "is_correct": true,
    "correct_option": "Stream of tokens",
    "explanation": "According to section 1.2, lexical analysis converts raw source text into a token stream.",
    "prior_mastery": 10.0,
    "updated_mastery": 39.3,
    "next_recommended_concept": "Lexical Analysis" // or unlocked downstream concept
  }
  ```

#### 5. Get Student Mastery Heatmap Overview
- **Method**: `GET`
- **Path**: `/api/v1/student/mastery/{course_id}`
- **Success Response (`200 OK`)**:
  ```json
  {
    "course_id": "67123456789abcdef0123457",
    "student_id": "67123456789abcdef0123499",
    "overall_mastery_percentage": 42.1,
    "concepts": [
      {
        "concept_name": "Lexical Analysis",
        "mastery_probability": 0.8624,
        "mastery_percentage": 86.2,
        "attempts_count": 4,
        "correct_count": 4,
        "status": "Mastered"
      },
      {
        "concept_name": "Syntax Analysis",
        "mastery_probability": 0.3929,
        "mastery_percentage": 39.3,
        "attempts_count": 1,
        "correct_count": 1,
        "status": "In Progress"
      }
    ]
  }
  ```

---

### Graph Endpoints (`/api/v1/graph`)

#### 1. Download Raw GML Graph
- **Method**: `GET`
- **Path**: `/api/v1/graph/{course_id}/gml`
- **Response**: `text/plain` attachment containing the standardized Graph Modeling Language (`.gml`) file.

#### 2. Query Concept Ego-Neighborhood
- **Method**: `GET`
- **Path**: `/api/v1/graph/{course_id}/concept-neighborhood/{concept_name}`
- **Success Response (`200 OK`)**:
  ```json
  {
    "concept": "Syntax Analysis",
    "node_type": "fine_grained_concept",
    "parents": ["Compiler Front End"],
    "prerequisites": ["Lexical Analysis"],
    "dependents": ["Semantic Analysis", "LR Parsing"],
    "evidence_chunks": [
      {
        "chunk_id": "compilers_p45_c2",
        "similarity": 0.91,
        "text": "Syntax analysis groups tokens into parse trees..."
      }
    ]
  }
  ```

---

### Health Endpoints (`/api/health`)

#### Health Check
- **Method**: `GET`
- **Path**: `/api/health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "database": "mega_project",
    "llm_provider": "gemini"
  }
  ```

---

## 6. Frontend Developer Integration Guide

### Teacher UI Integration Flow
1. **Upload Textbook**:
   - Provide a file upload dropzone accepting `.pdf`.
   - Send `POST /api/v1/teacher/upload` with `multipart/form-data`.
   - On success, store returned `course_id`.
2. **Start Pipeline**:
   - Prompt the user to start processing: `POST /api/v1/teacher/pipeline/start/{course_id}`.
   - Capture `task_id`.
3. **Display Real-Time Pipeline Progress**:
   - Poll `GET /api/v1/teacher/pipeline/status/{task_id}` every 2 seconds.
   - Render a progress bar using `progress_percentage`.
   - Display a stage badge matching `current_stage` (e.g., `CHUNKING`, `NLP_CONCEPTS`, `EMBEDDING`, `MAPPING`, `ENRICHMENT`, `DAG_RESOLVE`).
   - Show live streaming logs from the `logs` array.
4. **Visual Knowledge Graph & Relationship Editor**:
   - Once task status is `completed`, call `GET /api/v1/teacher/knowledge-graph/{course_id}`.
   - Feed `nodes` and `edges` into Vis.js / Cytoscape (see below).
   - If the teacher modifies edges in the UI, save the change via `PATCH /api/v1/teacher/knowledge-graph/{course_id}/concept`.

---

### Student UI Integration Flow
1. **Browse Courses**:
   - Fetch available courses via `GET /api/v1/student/courses`.
2. **Prerequisite Learning Path**:
   - Call `GET /api/v1/student/learning-path/{course_id}`.
   - Render the curriculum roadmap in sequential order.
   - Style concept cards according to their status:
     - `Mastered`: Green badge / checkmark ($P(L) \ge 85\%$).
     - `In Progress`: Blue badge with mastery percentage bar ($10\% < P(L) < 85\%$).
     - `Ready to Learn`: Yellow/Amber button inviting the student to practice.
     - `Locked`: Grayed-out card with a lock icon, displaying list of unfulfilled prerequisites.
3. **Adaptive Quiz Modal**:
   - When the student clicks "Practice" or "Next Question", call `GET /api/v1/student/quiz/next-question/{course_id}`.
   - Render the 4 options as selectable buttons.
   - When submitted, call `POST /api/v1/student/quiz/submit-answer`.
   - Animate the result (Success / Incorrect), show the explanation, and update the progress bar with the difference between `prior_mastery` and `updated_mastery`.
4. **Student Mastery Heatmap**:
   - Fetch `GET /api/v1/student/mastery/{course_id}`.
   - Display a color-coded grid or treemap where cell color intensity reflects `mastery_percentage`.

---

### Vis.js / Cytoscape Graph Rendering
The server returns nodes and edges pre-formatted for direct ingestion into graph libraries:

```javascript
// Example Vis.js integration
const response = await fetch(`/api/v1/teacher/knowledge-graph/${courseId}`, {
  headers: { Authorization: `Bearer ${token}` }
});
const { nodes, edges } = await response.json();

const visData = {
  nodes: nodes.map(n => ({
    id: n.id,
    label: n.label,
    shape: n.type === 'coarse_grained_category' ? 'box' : 'ellipse',
    color: n.type === 'coarse_grained_category' ? '#4F46E5' : '#10B981',
    font: { color: '#ffffff' }
  })),
  edges: edges.map(e => ({
    from: e.source,
    to: e.target,
    label: e.relation,
    arrows: 'to',
    dashes: e.relation === 'CONTAINS',
    title: `Confidence: ${e.confidence} | Citation: ${e.evidence_chunk}`
  }))
};

const container = document.getElementById('network-graph');
new vis.Network(container, visData, {
  physics: { hierarchicalRepulsion: { nodeDistance: 150 } },
  layout: { hierarchical: { direction: 'UD', sortMethod: 'directed' } }
});
```

---

## 7. Algorithm Engines: Cognitive-RAG & BKT

### Bayesian Knowledge Tracing (BKT) Engine
Located at [`server/services/bkt_engine.py`](file:///e:/D%20Drive/LY/Project/Mega-Project/server/services/bkt_engine.py).

Tracks student latent mastery for each concept via four standard parameters:
- $P(L_0) = 0.10$: Initial prior mastery.
- $P(T) = 0.15$: Probability of learning transition after answering.
- $P(G) = 0.25$: Probability of guessing correctly without mastery.
- $P(S) = 0.10$: Probability of slipping / making an error despite mastery.

**Formulas**:
- **If Answer is Correct**:
  $$P(L_t \mid \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
- **If Answer is Incorrect**:
  $$P(L_t \mid \text{Incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$
- **Next Trial Projected Mastery**:
  $$P(L_{t+1}) = P(L_t \mid \text{Obs}) + (1 - P(L_t \mid \text{Obs})) \cdot P(T)$$

### Cognitive-RAG Context Builder
Located at [`server/services/cognitive_rag.py`](file:///e:/D%20Drive/LY/Project/Mega-Project/server/services/cognitive_rag.py).
1. Inspects student BKT mastery profile across all DAG nodes.
2. Selects concepts whose prerequisite concepts all satisfy $P(L) \ge 0.70$.
3. Gathers the concept's grounded chunk IDs from `concept_chunk_mappings`.
4. Retrieves exact chunk texts from `content_chunks`.
5. Prompts the LLM with strict grounding constraints to generate a 4-choice question with clear distractors and textbook citation justifications.

---

## 8. Extensibility & Future Updates

- **Adding New Roles**: Update `role` check in [`server/routers/auth.py`](file:///e:/D%20Drive/LY/Project/Mega-Project/server/routers/auth.py) and create corresponding guards in [`server/core/dependencies.py`](file:///e:/D%20Drive/LY/Project/Mega-Project/server/core/dependencies.py).
- **Switching LLMs**: Change `LLM_PROVIDER` in `.env` to `ollama` or `gemini`, or specify alternate models in [`server/config.py`](file:///e:/D%20Drive/LY/Project/Mega-Project/server/config.py).
- **Remote Vector Databases**: Chunks in `content_chunks` already preserve dense embedding vectors in MongoDB; they can easily be synchronized to Milvus, Qdrant, or Pinecone if scale requires external vector indexing.
