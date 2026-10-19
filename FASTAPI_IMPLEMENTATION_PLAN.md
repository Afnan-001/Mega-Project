# FastAPI Server Implementation Plan: Role-Based AutoHKG & Cognitive-RAG Adaptive Learning

## 1. Executive Summary & Architectural Strategy

### Core Objectives
1. **FastAPI Server Architecture**: Transform the existing sequential Python pipeline into an asynchronous RESTful API server.
2. **Zero Modification to Existing Files**: Keep all code inside `Main/` 100% untouched as the core algorithm library, creating a clean modular server layer in `server/` that imports and calls existing logic.
3. **Role-Based Access Control (RBAC)**: Support two user personas—**Teacher** (material upload, pipeline execution, knowledge graph curation) and **Student** (prerequisite learning paths, adaptive cognitive-RAG quizzes, mastery tracking).
4. **MongoDB Persistence with Beanie ODM**: Replace file/folder-based storage in `outputs/` with structured MongoDB collections for chunks, embeddings metadata, extracted concepts, grounded mappings, enriched graphs, user credentials, quiz sessions, and student mastery history.
5. **Background Task Execution**: Run the long-running PDF processing and AutoHKG pipeline asynchronously using FastAPI `BackgroundTasks`, updating real-time progress percentages in MongoDB.
6. **Cognitive-RAG & Bayesian Knowledge Tracing (BKT)**: Dynamically retrieve grounded chunk evidence and graph neighborhoods to generate MCQs via LLM, updating per-concept student mastery using BKT.

---

## 2. System Architecture & Module Boundaries

```
+-------------------------------------------------------------------------------------------------+
|                                    Frontend (Web Application)                                   |
|       Teacher UI (Upload PDF, Pipeline Monitor, KG Editor) | Student UI (Adaptive Quiz, Heatmap)|
+------------------------------------------------+------------------------------------------------+
                                                 | HTTP / REST (JWT Auth)
                                                 v
+-------------------------------------------------------------------------------------------------+
|                                     FastAPI Server (server/)                                    |
|                                                                                                 |
|   ┌─────────────────────────────────── API Routers ─────────────────────────────────────────┐   |
|   │  /api/v1/auth     │  /api/v1/teacher    │  /api/v1/student     │  /api/v1/graph         │   |
|   └─────────┬─────────┴──────────┬──────────┴──────────┬───────────┴───────────┬────────────┘   |
|             │                    │                     │                       │                |
|             ▼                    ▼                     ▼                       ▼                |
|      [Auth & RBAC]      [Pipeline Service]    [Cognitive-RAG & BKT]    [Graph Serializer]       |
|      (JWT / bcrypt)    (BackgroundTasks)     (Adaptive Question Gen)   (Node & Edge Format)     |
+-------------┬────────────────────┬─────────────────────┬───────────────────────┬----------------+
              │                    │                     │                       │                |
              │                    │ Reads / Writes      │ Reads Context         │                |
              ▼                    ▼                     ▼                       ▼                |
+-------------------------------------------------------------------------------------------------+
|                                  MongoDB Database (Motor + Beanie)                              |
|   • users                   • content_chunks          • concept_chunk_mappings                  |
|   • courses                 • raw_concepts            • enriched_concepts                       |
|   • pipeline_tasks          • clean_concepts          • knowledge_graphs                        |
|   • quiz_attempts           • student_mastery_states  • chunk_embeddings_metadata               |
+----------------------------------┬--------------------------------------------------------------+
                                   │
                                   │ Invokes without code modification
                                   v
+-------------------------------------------------------------------------------------------------+
|                               Untouched Core Algorithm Library (Main/)                          |
|   • Main/llm.py                               (Unified LLM: Gemini multi-key + Ollama)          |
|   • Main/AutoHKG/extract_and_chunk.py         (PDF PyMuPDF extractor + RecursiveTextSplitter)   |
|   • Main/AutoHKG/concept_pipeline/*           (Headings, Definitions, Technical, Nouns, TF-IDF) |
|   • Main/AutoHKG/extract_concepts.py          (Multi-signal statistical NLP concept ranker)     |
|   • Main/AutoHKG/clean_concepts.py            (LLM terminology canonicalizer & cleaner)         |
|   • Main/AutoHKG/embed_chunks.py              (BAAI/bge-m3 dense vector embedding generator)    |
|   • Main/AutoHKG/map_concepts.py              (Knee/Elbow cosine similarity mapper & pruner)    |
|   • Main/AutoHKG/enrich_concepts.py           (Source-grounded hierarchy & prerequisite enrich) |
|   • Main/AutoHKG/post_process_dag.py          (NetworkX cycle detection & DAG resolution)       |
+-------------------------------------------------------------------------------------------------+
```

---

## 3. MongoDB Database Schema & Beanie ODM Models

All documents inherit from Beanie's `Document` class and use Pydantic models for validation.

### Collection Specifications:

#### 1. `users` (`UserDocument`)
*   `id`: `PydanticObjectId`
*   `email`: `Indexed(str, unique=True)`
*   `hashed_password`: `str`
*   `full_name`: `str`
*   `role`: `str` (`"teacher"` | `"student"`)
*   `created_at`: `datetime`

#### 2. `courses` (`CourseDocument`)
*   `id`: `PydanticObjectId`
*   `title`: `str`
*   `description`: `str | None`
*   `teacher_id`: `str` (reference to User)
*   `uploaded_pdf_name`: `str`
*   `pdf_storage_path`: `str`
*   `status`: `str` (`"ready"` | `"processing"` | `"error"`)
*   `active_task_id`: `str | None`
*   `created_at`: `datetime`

#### 3. `pipeline_tasks` (`PipelineTaskDocument`)
*   `id`: `PydanticObjectId`
*   `course_id`: `str`
*   `status`: `str` (`"queued"` | `"running"` | `"completed"` | `"failed"`)
*   `current_stage`: `str` (`"CHUNKING"` | `"NLP_CONCEPTS"` | `"LLM_CLEANING"` | `"EMBEDDING"` | `"MAPPING"` | `"ENRICHMENT"` | `"DAG_RESOLVE"` | `"FINISHED"`)
*   `progress_percentage`: `int` (0 to 100)
*   `stage_details`: `dict[str, str]` (per-stage execution times and metrics)
*   `logs`: `list[str]` (timestamped log messages)
*   `error_message`: `str | None`
*   `started_at`: `datetime`
*   `completed_at`: `datetime | None`

#### 4. `content_chunks` (`ContentChunkDocument`)
*   `id`: `PydanticObjectId`
*   `course_id`: `Indexed(str)`
*   `chunk_id`: `Indexed(str)` (e.g. `Compiler_book_p12_c0`)
*   `page_number`: `int`
*   `book_name`: `str`
*   `text`: `str`
*   `embedding_vector`: `list[float] | None` (dense float vector, stored in MongoDB or FAISS/file with DB metadata)

#### 5. `concepts` (`ConceptDocument`)
*   `id`: `PydanticObjectId`
*   `course_id`: `Indexed(str)`
*   `concept_name`: `str`
*   `canonical_name`: `str`
*   `node_type`: `str` (`"fine_grained_concept"` | `"coarse_grained_category"`)
*   `is_grounded`: `bool`
*   `max_chunk_similarity`: `float | None`
*   `created_at`: `datetime`

#### 6. `concept_chunk_mappings` (`ConceptChunkMappingDocument`)
*   `id`: `PydanticObjectId`
*   `course_id`: `Indexed(str)`
*   `concept_name`: `Indexed(str)`
*   `qualifying_chunks`: `list[dict]` (e.g. `[{"chunk_id": "...", "similarity": 0.84}]`)
*   `elbow_threshold`: `float`

#### 7. `enriched_concepts` (`EnrichedConceptDocument`)
*   `id`: `PydanticObjectId`
*   `course_id`: `Indexed(str)`
*   `concept`: `Indexed(str)`
*   `node_type`: `str`
*   `coarse_grained_category`: `list[str]`
*   `parent_concept`: `list[str]`
*   `prerequisites`: `list[str]`
*   `category_edge`: `dict | None` (`{"concept": "...", "confidence": 1.0, "evidence_chunk": "...", "evidence_text": "..."}`)
*   `prerequisite_edges`: `list[dict]` (`[{"prerequisite": "...", "confidence": 0.95, "evidence_chunk": "...", "evidence_text": "..."}]`)

#### 8. `knowledge_graphs` (`KnowledgeGraphDocument`)
*   `id`: `PydanticObjectId`
*   `course_id`: `Indexed(str, unique=True)`
*   `nodes`: `list[dict]` (`[{"id": "...", "label": "...", "type": "..."}]`)
*   `edges`: `list[dict]` (`[{"source": "...", "target": "...", "relation": "PREREQUISITE_FOR"|"CONTAINS", "confidence": float, "evidence_chunk": str, "evidence_text": str}]`)
*   `gml_content`: `str`
*   `total_nodes`: `int`
*   `total_edges`: `int`
*   `updated_at`: `datetime`

#### 9. `student_mastery_states` (`StudentMasteryDocument`)
*   `id`: `PydanticObjectId`
*   `student_id`: `Indexed(str)`
*   `course_id`: `Indexed(str)`
*   `concept_name`: `Indexed(str)`
*   `mastery_probability`: `float` ($P(L_t) \in [0.0, 1.0]$, initialized at $0.10$)
*   `attempts_count`: `int`
*   `correct_count`: `int`
*   `last_practiced_at`: `datetime`

#### 10. `quiz_attempts` (`QuizAttemptDocument`)
*   `id`: `PydanticObjectId`
*   `student_id`: `Indexed(str)`
*   `course_id`: `Indexed(str)`
*   `concept_name`: `str`
*   `question_id`: `str`
*   `question_text`: `str`
*   `options`: `list[str]`
*   `correct_option`: `str`
*   `selected_option`: `str`
*   `is_correct`: `bool`
*   `explanation`: `str`
*   `prior_mastery`: `float`
*   `posterior_mastery`: `float`
*   `created_at`: `datetime`

---

## 4. Authentication & Role-Based Access Control (RBAC)

### Security Components:
*   **Password Hashing**: `bcrypt` / `passlib` with Salt.
*   **Token Standard**: JSON Web Tokens (JWT) using `pyjwt` with SHA-256 HMAC (`HS256`).
*   **Expiration**: Access token valid for 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

### Dependency Injection Pipeline:
```python
# server/core/dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserDocument: ...
async def require_teacher(current_user: UserDocument = Depends(get_current_user)) -> UserDocument:
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher permission required")
    return current_user

async def require_student(current_user: UserDocument = Depends(get_current_user)) -> UserDocument:
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student permission required")
    return current_user
```

---

## 5. Non-Destructive AutoHKG Pipeline Service

### Execution Strategy:
The pipeline runner in `server/services/pipeline_service.py` acts as an asynchronous orchestrator that:
1. Dynamically imports the existing modules from `Main.AutoHKG...` without altering a single character of their code.
2. Directs inputs and outputs through temporary memory or MongoDB, executing each stage in order:

| Stage # | Pipeline Step | Function Called in `Main/` | Input Source | MongoDB Collection Updated |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | Text & Chunking | `extract_and_chunk.extract_text_from_pdf` | Uploaded PDF file path | `content_chunks` |
| **Stage 2** | NLP Concepts | `extract_concepts.extract_concepts_nlp` | Chunks from Stage 1 | `concepts` (Raw candidates) |
| **Stage 3** | LLM Cleaning | `clean_concepts.clean_concepts_batch` via `LLM` | Raw candidates from Stage 2 | `concepts` (Clean canonical terms) |
| **Stage 4** | Dense Embeddings | `embed_chunks.get_embeddings_local` | Chunks from Stage 1 | `content_chunks` + NPY cache |
| **Stage 5** | Knee/Elbow Mapping | `map_concepts.map_and_prune_concepts` | Clean concepts + embeddings | `concept_chunk_mappings` |
| **Stage 6** | LLM Enrichment | `enrich_concepts.enrich_concept` via `LLM` | Grounded concepts + chunk citations | `enriched_concepts` |
| **Stage 7** | DAG Resolution | `post_process_dag.post_process_dag` | Enriched records from Stage 6 | `knowledge_graphs` (GML & Nodes/Edges) |

### Real-Time Task Progress Tracking:
Every stage records progress (0%, 15%, 30%, 50%, 70%, 85%, 100%) in `pipeline_tasks`, which can be queried via polling or Server-Sent Events (SSE).

---

## 6. Cognitive-RAG & Bayesian Knowledge Tracing (BKT) Engine

### Component A: Cognitive-RAG Hybrid Retriever (`server/services/cognitive_rag.py`)
1. **Concept Selection**:
   The engine reads the student's current mastery profile. It inspects the `knowledge_graphs` DAG:
   - Concepts with 0 unfulfilled prerequisites and mastery $< 0.85$ are flagged as **Ready to Learn**.
   - If all prerequisites for a target concept have mastery $\ge 0.70$, the target concept becomes available.
2. **Context Retrieval**:
   - Fetches the concept's grounded chunk IDs from `concept_chunk_mappings`.
   - Loads the exact chunk texts from `content_chunks`.
   - Retrieves the concept's parent category and immediate prerequisite names from `enriched_concepts`.
3. **MCQ Generation**:
   Calls `Main.llm.LLM` with a structured Cognitive-RAG prompt:
   - Inputs: Concept name, course topic, grounded source chunks, student current difficulty level.
   - Outputs: Strict JSON containing `{ question, options: [A, B, C, D], correct_answer: "A", explanation: "..." }`.

### Component B: Bayesian Knowledge Tracing (BKT) (`server/services/bkt_engine.py`)
Tracks the latent knowledge state of the student for each specific concept:
*   **Parameters**:
    - $P(L_0) = 0.10$ (Initial prior mastery)
    - $P(T) = 0.15$ (Probability of transit / learning after practice)
    - $P(G) = 0.25$ (Probability of guessing correctly without mastery)
    - $P(S) = 0.10$ (Probability of slipping / making a mistake despite mastery)

*   **Bayesian Update Formulas**:
    $$\text{If Correct: } P(L_t \mid \text{Obs}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
    $$\text{If Incorrect: } P(L_t \mid \text{Obs}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$
    $$\text{Posterior for Next Trial: } P(L_{t+1}) = P(L_t \mid \text{Obs}) + (1 - P(L_t \mid \text{Obs})) \cdot P(T)$$

---

## 7. Complete REST API Endpoints Specification

### 1. Authentication Router (`/api/v1/auth`)
*   `POST /api/v1/auth/register`:
    - Payload: `{ email, password, full_name, role: "teacher" | "student" }`
    - Response: `{ id, email, full_name, role, token }`
*   `POST /api/v1/auth/login`:
    - Payload: Standard OAuth2 password form (`username` (email), `password`)
    - Response: `{ access_token, token_type: "bearer", role, user_id }`
*   `GET /api/v1/auth/me`:
    - Headers: `Authorization: Bearer <token>`
    - Response: Current user profile details.

### 2. Teacher Router (`/api/v1/teacher`)
*   `POST /api/v1/teacher/upload`:
    - Form Data: `file: UploadFile` (PDF), `title: str`, `description: str`
    - Logic: Saves PDF to `Main/books/`, creates `CourseDocument`, returns `course_id`.
*   `POST /api/v1/teacher/pipeline/start/{course_id}`:
    - Logic: Spawns `pipeline_service.run_full_pipeline` via `BackgroundTasks`. Returns `task_id`.
*   `GET /api/v1/teacher/pipeline/status/{task_id}`:
    - Response: `{ task_id, status, current_stage, progress_percentage, logs, error }`.
*   `GET /api/v1/teacher/courses`:
    - Response: List of all courses uploaded by the teacher.
*   `GET /api/v1/teacher/knowledge-graph/{course_id}`:
    - Response: Node and edge payload formatted for Vis.js / Cytoscape graph visualizers.
*   `PATCH /api/v1/teacher/knowledge-graph/{course_id}/concept`:
    - Payload: `{ concept_name, coarse_grained_category, prerequisites }`
    - Logic: Manual human-in-the-loop override of relationships.

### 3. Student Router (`/api/v1/student`)
*   `GET /api/v1/student/courses`:
    - Response: List of available courses with ready knowledge graphs.
*   `GET /api/v1/student/learning-path/{course_id}`:
    - Response: Topological sort of concept nodes from the DAG, categorized into `"Mastered"`, `"In Progress"`, and `"Locked"` based on BKT states.
*   `GET /api/v1/student/quiz/next-question/{course_id}`:
    - Logic: Identifies next optimal concept, retrieves chunks, invokes Cognitive-RAG LLM prompt, returns question + options (hiding correct answer and explanation).
*   `POST /api/v1/student/quiz/submit-answer`:
    - Payload: `{ course_id, concept_name, question_id, selected_option, correct_option, question_text, explanation }`
    - Logic: Evaluates response, computes BKT update, updates `student_mastery_states`, records `quiz_attempts`.
    - Response: `{ is_correct, explanation, previous_mastery, updated_mastery, next_recommended_concept }`.
*   `GET /api/v1/student/mastery/{course_id}`:
    - Response: Per-concept mastery percentages ($P(L)$) for heatmap visualization.

### 4. Graph Router (`/api/v1/graph`)
*   `GET /api/v1/graph/{course_id}/gml`:
    - Returns raw `.gml` file content.
*   `GET /api/v1/graph/{course_id}/concept-neighborhood/{concept_name}`:
    - Returns ego-network (parents, children, prerequisites, evidence chunks) for a single concept.

---

## 8. Proposed Project Directory Structure

```text
Mega-Project/
├── server/                               # NEW: Complete FastAPI Server Module
│   ├── main.py                           # App creation, CORS, router inclusion, lifespan
│   ├── config.py                         # Pydantic Settings (.env configuration)
│   ├── database.py                       # Motor client & Beanie initialization
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py                   # Password hashing (bcrypt) & JWT creation/decoding
│   │   └── dependencies.py               # Auth dependency guards (require_teacher, require_student)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                       # UserDocument
│   │   ├── course.py                     # CourseDocument, PipelineTaskDocument
│   │   ├── knowledge.py                  # ContentChunkDocument, ConceptDocument, KnowledgeGraphDocument
│   │   ├── student.py                    # StudentMasteryDocument, QuizAttemptDocument
│   │   └── schemas.py                    # Pydantic Request/Response DTOs
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pipeline_service.py           # Background task orchestrator calling Main.AutoHKG
│   │   ├── cognitive_rag.py              # Context builder & MCQ question generation engine
│   │   └── bkt_engine.py                 # Bayesian Knowledge Tracing math engine
│   └── routers/
│       ├── __init__.py
│       ├── auth.py                       # /api/v1/auth routes
│       ├── teacher.py                    # /api/v1/teacher routes
│       ├── student.py                    # /api/v1/student routes
│       └── graph.py                      # /api/v1/graph routes
│
├── Main/                                 # UNTOUCHED: Core Algorithm Pipeline
│   ├── llm.py
│   ├── books/
│   ├── graph_model/
│   ├── outputs/
│   └── AutoHKG/
│       ├── extract_and_chunk.py
│       ├── extract_concepts.py
│       ├── clean_concepts.py
│       ├── embed_chunks.py
│       ├── map_concepts.py
│       ├── enrich_concepts.py
│       ├── post_process_dag.py
│       └── concept_pipeline/
│
├── requirements.txt                      # Dependencies list
├── .env                                  # Configuration (MongoDB URL, Secret Key, etc.)
└── README.md                             # Codebase documentation
```

---

## 9. Step-by-Step Implementation Roadmap

```
Step 1: Dependencies & Environment Configuration
  │  ├── Add motor, beanie, pyjwt, bcrypt, python-multipart to requirements.txt
  │  └── Add MONGODB_URL, JWT_SECRET_KEY, and API settings to .env
  ▼
Step 2: Database Connection & Beanie ODM Models
  │  ├── Configure Motor async client and Beanie initialization in server/database.py
  │  └── Implement Beanie models in server/models/ (User, Course, PipelineTask, Knowledge, Student)
  ▼
Step 3: Authentication & Role-Based Access Control (RBAC)
  │  ├── Implement password hashing & JWT encoding in server/core/security.py
  │  ├── Implement auth dependencies in server/core/dependencies.py
  │  └── Build /api/v1/auth router in server/routers/auth.py
  ▼
Step 4: Non-Destructive Teacher Ingestion Pipeline Service
  │  ├── Implement server/services/pipeline_service.py calling Main.AutoHKG functions
  │  ├── Save chunks, concepts, mappings, enrichments, and graph to MongoDB
  │  └── Build /api/v1/teacher/upload and /api/v1/teacher/pipeline/start routers
  ▼
Step 5: Cognitive-RAG Question Generator & BKT Engine
  │  ├── Implement Hybrid context retrieval and LLM prompt in server/services/cognitive_rag.py
  │  ├── Implement Bayesian Knowledge Tracing updates in server/services/bkt_engine.py
  │  └── Build /api/v1/student/quiz/next-question and /api/v1/student/quiz/submit-answer
  ▼
Step 6: Master Application Assembly & Testing
     ├── Connect all routers to server/main.py with CORS middleware
     └── Validate end-to-end flow with Teacher and Student roles
```
