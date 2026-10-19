# Automated Hierarchical Knowledge Graph (AutoHKG) & Adaptive Cognitive-RAG Learning System

A comprehensive framework for source-grounded automated Knowledge Graph (KG) construction from educational textbooks, paired with Cognitive-RAG and Bayesian Knowledge Tracing (BKT) for personalized, adaptive student learning.

> [!TIP]
> **FastAPI Server Documentation**: For the complete REST API reference, MongoDB schema, and Frontend integration guides, see [server/README.md](file:///e:/D%20Drive/LY/Project/Mega-Project/server/README.md).

---

## 📌 Table of Contents
1. [Project Overview](#-project-overview)
2. [High-Level System Architecture](#-high-level-system-architecture)
   - [Group 1: Knowledge Construction (AutoHKG)](#group-1-knowledge-construction-autohkg)
   - [Group 2: Cognitive-RAG](#group-2-cognitive-rag)
   - [Group 3: Adaptive Learning](#group-3-adaptive-learning)
   - [Group 4: User Interaction & BKT](#group-4-user-interaction--bkt)
3. [Repository Directory Structure](#-repository-directory-structure)
4. [Complete File-by-File & Function-by-Function Reference](#-complete-file-by-file--function-by-function-reference)
   - [Core Infrastructure (`Main/llm.py`)](#1-core-infrastructure-mainllmpy)
   - [Pipeline Step 1: Text Extraction & Chunking (`extract_and_chunk.py`)](#2-pipeline-step-1-text-extraction--chunking-mainautohkgextract_and_chunkpy)
   - [Pipeline Step 2: NLP Concept Extraction Subsystem (`concept_pipeline/`)](#3-pipeline-step-2-nlp-concept-extraction-subsystem-mainautohkgconcept_pipeline)
   - [Pipeline Step 3: NLP Orchestration (`extract_concepts.py`)](#4-pipeline-step-3-nlp-orchestration-mainautohkgextract_conceptspy)
   - [Pipeline Step 4: LLM Concept Cleaning (`clean_concepts.py`)](#5-pipeline-step-4-llm-concept-cleaning-mainautohkgclean_conceptspy)
   - [Pipeline Step 5: Chunk Vector Embeddings (`embed_chunks.py`)](#6-pipeline-step-5-chunk-vector-embeddings-mainautohkgembed_chunkspy)
   - [Pipeline Step 6: Semantic Concept-to-Chunk Mapping (`map_concepts.py`)](#7-pipeline-step-6-semantic-concept-to-chunk-mapping-mainautohkgmap_conceptspy)
   - [Pipeline Step 7: Hierarchy & Prerequisite Enrichment (`enrich_concepts.py`)](#8-pipeline-step-7-hierarchy--prerequisite-enrichment-mainautohkgenrich_conceptspy)
   - [Pipeline Step 8: DAG Cycle Breaking & Graph Output (`post_process_dag.py`)](#9-pipeline-step-8-dag-cycle-breaking--graph-output-mainautohkgpost_process_dagpy)
5. [Data Artifacts & Lifecycle (`Main/outputs/data/`)](#-data-artifacts--lifecycle)
6. [FastAPI Server Architecture & Migration Plan](#-fastapi-server-architecture--migration-plan)
   - [Teacher Workflow Endpoints](#teacher-workflow-endpoints)
   - [Student Workflow Endpoints](#student-workflow-endpoints)
   - [Proposed FastAPI Module Structure](#proposed-fastapi-module-structure)
7. [Environment Configuration & Dependencies](#-environment-configuration--dependencies)

---

## 🚀 Project Overview

The goal of this project is to eliminate the need for manual curriculum tagging and generic, one-size-fits-all question generation. The system operates in two core phases:

1. **Teacher / Ingestion Phase (AutoHKG Knowledge Construction)**:
   A teacher uploads academic material (e.g., textbook PDF, syllabus, or lecture notes). The server automatically cleans the text, extracts domain concepts using multi-signal statistical NLP, canonicalizes them via LLMs, embeds content chunks, grounds concepts to text via adaptive cosine similarity, extracts hierarchical parent-child and prerequisite relationships backed by citation evidence, and compiles a clean Directed Acyclic Graph (DAG) Knowledge Graph.

2. **Student / Interactive Learning Phase (Cognitive-RAG & Adaptive BKT)**:
   A student interacts with the system to learn and practice. The system selects concepts based on the student's mastery profile and prerequisite graph, constructs grounded retrieval context using both graph neighborhoods and semantic vector search, uses an LLM to generate targeted Multiple Choice Questions (MCQs), and updates the student's mastery probabilities in real-time using Bayesian Knowledge Tracing (BKT).

---

## 🏛 High-Level System Architecture

Based on the architectural blueprints located in `assets/Diagrams/`:

```
+----------------------------------------------------------------------------------------------------+
|                                    Group 1: Knowledge Construction                                 |
|                                                                                                    |
|  [Course Contents] ---> [Text Extraction & Chunking] ---> [Content Chunks JSON]                    |
|       (PDF)                        |                                  |                            |
|                                    v                                  v                            |
|                         [Multi-Signal NLP & LLM]              [Dense Embedding Model]              |
|                                    |                                  |                            |
|                                    v                                  v                            |
|                          [Concepts Extraction]               [Vector Store / NPY]                  |
|                                    \                                 /                             |
|                                     \                               /                              |
|                              [Adaptive Cosine Knee/Elbow Concept Grounding]                        |
|                                                    |                                               |
|                                                    v                                               |
|                             [LLM Hierarchy & Prerequisite Enrichment]                              |
|                                                    |                                               |
|                                                    v                                               |
|                              [DAG Cycle Resolution & Graph Assembly]                               |
|                                                    |                                               |
|                                                    v                                               |
|                                          [Knowledge Graph (GML)]                                   |
+----------------------------------------------------+-----------------------------------------------+
                                                     |
                                                     | Concept Neighborhood & Prerequisites
                                                     v
+----------------------------------------------------+-----------------------------------------------+
|                                        Group 2: Cognitive-RAG                                      |
|                                                                                                    |
|  +---------------------------+        +---------------------------------------------------------+  |
|  |      Adaptive Engine      | <----> |            Hybrid Retriever / Context Builder           |  |
|  | - Learning path selection |        | - Knowledge Graph neighborhood                          |  |
|  | - Difficulty modulation   |        | - Semantic similarity chunk search                      |  |
|  +-------------+-------------+        | - Grounded evidence assembly                            |  |
|                |                      +----------------------------+----------------------------+  |
|                | Grounded Context                                  | Relevant Concepts             |
|                +-----------------------------+---------------------+                               |
|                                              v                                                     |
|                                  [LLM MCQ Question Generator]                                      |
+----------------------------------------------+-----------------------------------------------------+
                                               |
                                               | Generated MCQ
                                               v
+----------------------------------------------+-----------------------------------------------------+
|                                    Group 4: User Interaction & BKT                                 |
|                                                                                                    |
|  [Student Web Interface] <====================+                                                    |
|           |                                                                                        |
|           | Student Response (Option selection)                                                    |
|           v                                                                                        |
|  [Bayesian Knowledge Tracing (BKT) Engine]                                                         |
|    P(L_t) = P(L_t-1 | Evidence) + (1 - P(L_t-1 | Evidence)) * P(T)                                 |
+----------------------------------------------+-----------------------------------------------------+
                                               |
                                               | Updated Current Mastery State
                                               v
+----------------------------------------------+-----------------------------------------------------+
|                                      Group 3: Adaptive Learning                                    |
|                                                                                                    |
|  [Student Mastery Model]: Per-concept mastery levels P(L), learning history, and knowledge state.  |
+----------------------------------------------------------------------------------------------------+
```

---

## 📂 Repository Directory Structure

```text
Mega-Project/
├── .env.example                               # Template for API keys and endpoint configuration
├── requirements.txt                           # Full python package dependencies
├── assets/
│   └── Diagrams/
│       ├── Architecture Diagram.png           # 4-group end-to-end architecture diagram
│       ├── High Level Approach.png            # Stepwise research & development lifecycle
│       └── Our Implementation Steps.png       # 5-step implementation pipeline diagram
├── lib/                                       # Vendored web libraries (vis-9.1.2, tom-select) for graph UI
├── Main/
│   ├── llm.py                                 # Unified LLM wrapper (Gemini multi-key rotation + Ollama)
│   ├── books/                                 # Storage directory for source PDF textbooks
│   │   └── Compiler_book.pdf                  # Example source document
│   ├── graph_model/                           # Serialized graph exports
│   │   └── knowledge_graph.gml                # Output Knowledge Graph in GML format
│   ├── outputs/
│   │   ├── data/                              # Intermediate and final JSON & numpy artifacts
│   │   │   ├── content_chunks.json            # Chunks from PDF extraction
│   │   │   ├── chunk_index.json               # Chunk metadata index
│   │   │   ├── chunk_embeddings.npy           # Dense embeddings matrix
│   │   │   ├── concepts.json                  # Candidate concepts extracted by NLP
│   │   │   ├── clean_concepts.json            # LLM-cleaned canonical concepts
│   │   │   ├── mapped_concepts.json           # Concepts grounded in source chunks
│   │   │   ├── concept_chunk_map.json         # Mapping of concept -> list of chunk IDs
│   │   │   ├── concept_chunk_scores.json      # Cosine similarity scores per concept-chunk pair
│   │   │   ├── enriched_concepts.json         # Concepts enriched with prerequisites & categories
│   │   │   └── cleaned_enriched_concepts.json # Cycle-free DAG concepts with citations
│   │   └── graph_model/
│   │       └── knowledge_graph.gml
│   └── AutoHKG/                               # Automated Hierarchical Knowledge Graph Pipeline
│       ├── extract_and_chunk.py               # Step 1: PDF text extractor & chunker
│       ├── extract_concepts.py                # Step 2: NLP candidate concept extractor runner
│       ├── clean_concepts.py                  # Step 3: LLM concept canonicalizer & noise cleaner
│       ├── embed_chunks.py                    # Step 4: Dense vector embeddings generator
│       ├── map_concepts.py                    # Step 5: Adaptive cosine similarity mapper & pruner
│       ├── enrich_concepts.py                 # Step 6: Source-grounded hierarchy & prerequisite enricher
│       ├── post_process_dag.py                # Step 7: NetworkX cycle detection & DAG enforcer
│       └── concept_pipeline/                  # Modular NLP feature extraction library
│           ├── __init__.py
│           ├── loader.py                      # JSON chunk loader and validator
│           ├── cleaner.py                     # Regex text cleaning & noise chunk filtration
│           ├── headings.py                    # Chapter & section heading detector
│           ├── definitions.py                 # Definitional pattern sentence detector
│           ├── technical_terms.py             # Domain abbreviations & technical regex matcher
│           ├── noun_phrases.py                # NLTK POS-tagging & regex noun phrase chunker
│           ├── ngrams.py                      # Scikit-learn n-grams (1-4) & TF-IDF scorer
│           ├── yake_extractor.py              # Pure-Python PositionalRank keyword scorer
│           ├── scorer.py                      # Multi-signal weighted candidate scoring & gating
│           ├── normalizer.py                  # Canonical key merger & capitalization mapper
│           └── saver.py                       # Concept JSON serializer
```

---

## 🔍 Complete File-by-File & Function-by-Function Reference

### 1. Core Infrastructure (`Main/llm.py`)
Provides an enterprise-grade unified interface supporting both Google Gemini API (with automatic multi-key rotation upon HTTP 429 quota exhaustion) and local Ollama inference.

#### Classes & Methods:
*   `class GeminiKeyManager`:
    *   `__init__(self, keys: list[str] | None = None)`: Parses comma-separated API keys from `GEMINI_API_KEYS` and single key from `GEMINI_API_KEY`. Initializes key rotation index.
    *   `get_current_key() -> str`: Returns the active Gemini API key. Raises `ValueError` if no keys are found.
    *   `rotate_key() -> str`: Rotates cyclically to the next available API key in the list and logs rotation event.
*   `class OllamaLLM`:
    *   `__init__(self, sys_msg=None, model_name="qwen2.5:7b-instruct-q4_K_M", temperature=0.0, base_url="http://localhost:11434", json_mode=True)`: Initializes local Ollama HTTP client with timeout and format options.
    *   `get_response(self, usr_msg: str, max_retries: int = 3) -> str`: Sends request to `{base_url}/api/chat`. Automatically relaxes JSON mode on final retry if constrained decoding fails.
*   `class LLM`:
    *   `__init__(self, sys_msg=None, model_name=None, temperature=0.0, keys=None, provider=None)`: Reads `LLM_PROVIDER` (`gemini` or `ollama`). Sets up the appropriate backend.
    *   `_configure_gemini_client()`: Initializes `google.generativeai.GenerativeModel` with system instruction and temperature using the current key.
    *   `get_response(self, usr_msg: str, max_retries: int | None = None) -> str`: Dispatches prompt to backend. If a Gemini quota/rate limit error (429, resource exhausted) occurs, calls `key_manager.rotate_key()`, reconfigures the client, and seamlessly retries.

---

### 2. Pipeline Step 1: Text Extraction & Chunking (`Main/AutoHKG/extract_and_chunk.py`)
Processes raw textbook PDF files from `Main/books/` into structured text chunks.

#### Functions:
*   `clean_text(text: str) -> str`: Replaces newline characters with spaces and collapses repeated whitespace.
*   `extract_text_from_pdf(pdf_path: Path) -> list[dict]`: Opens the PDF using PyMuPDF (`fitz`), iterates page by page, extracts raw text, cleans it, and returns non-empty pages with their page number.
*   `main()`: Discovers all PDFs in `Main/books/`, instantiates `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`, splits each page, assigns unique IDs (`{pdf_stem}_p{page}_c{idx}`), and writes results to `outputs/data/content_chunks.json`.

---

### 3. Pipeline Step 2: NLP Concept Extraction Subsystem (`Main/AutoHKG/concept_pipeline/`)
A modular statistical NLP engine designed to discover candidate concepts without relying on costly LLM passes over large texts.

#### `concept_pipeline/loader.py`
*   `load_chunks(path: str | Path) -> list[dict]`: Loads and validates `content_chunks.json`, verifying required keys (`chunk_id`, `text`, `page_number`), and filters out empty texts.

#### `concept_pipeline/cleaner.py`
*   `clean_text(text: str) -> str`: Removes hyphenated line breaks (`proc-\n-essors` $\rightarrow$ `processors`), strips control bytes, cleans publisher boilerplate (e.g. copyright, ISBN, web URLs, Bookey notices), normalizes OCR page numbers.
*   `is_noise_chunk(text: str) -> bool`: Checks if a chunk is shorter than 80 characters or dominated by noise.
*   `filter_noise_chunks(chunks: list[dict]) -> list[dict]`: Filters out noise chunks and stores cleaned text in `_cleaned_text`.

#### `concept_pipeline/headings.py`
*   `_clean_heading(raw: str) -> str`: Strips dot leaders (`...... 42`), trailing numbers, and whitespace.
*   `_add(d: dict[str, int], key: str)`: Normalizes and increments phrase frequency in a dictionary.
*   `extract_headings(texts: list[str]) -> dict[str, int]`: Scans chunks using regex patterns for Chapter headings, named sections, numbered subsections (`^\d+(\.\d+)*`), and ALL-CAPS lines. Filters common boilerplate (e.g., "Index", "Summary", "Exercises").

#### `concept_pipeline/definitions.py`
*   `_valid_term(term: str) -> bool`: Validates candidate length (3 to 6 words), verifies alphabetic content, and filters against leading stop words.
*   `detect_definitions(texts: list[str]) -> dict[str, int]`: Splits text into individual sentences and applies bounded non-backtracking regexes to capture definition subjects:
    - `"X is defined as / called / known as / referred to as"`
    - `"X refers to ..."`
    - `"A/An X is a/an ..."`
    - `"The X is a/an ..."`

#### `concept_pipeline/technical_terms.py`
*   `detect_technical_terms(texts: list[str]) -> dict[str, int]`: Scans corpus for technical abbreviations and patterns:
    - Normal Forms (`1NF`, `2NF`, `3NF`, `BCNF`, etc.)
    - All-caps abbreviations (3–8 letters: `SQL`, `ACID`, `MVCC`, `AST`, etc.)
    - Cardinality ratios (`1:1`, `1:N`, `M:N`)
    - Tree patterns (`B-tree`, `B+ tree`)
    - Built-in generic CS/DB seed terms (`GENERIC_SEED_TERMS`)

#### `concept_pipeline/noun_phrases.py`
*   `_ensure_nltk()`: Validates and loads NLTK POS taggers (`averaged_perceptron_tagger_eng`).
*   `_extract_nps_from_text(text: str, chunker, max_tokens: int | None) -> list[str]`: Uses Treebank tokenizer and POS tagging to extract noun phrase subtrees matching regex grammar `<DT>?<JJ.*|VBG|VBN>*<NN.*>+`. Strips leading determiners and punctuations.
*   `extract_noun_phrases(texts: list[str], batch_size: int = 0, sample_every: int = 1, max_tokens: int | None = None, strict: bool = False) -> dict[str, int]`: Runs noun-phrase extraction over the corpus with progress logging.

#### `concept_pipeline/ngrams.py`
*   `_token_ok(token: str) -> bool`: Verifies token contains alphabetic characters.
*   `_ngram_ok(tokens: list[str]) -> bool`: Rejects n-grams consisting solely of stop words or beginning/ending with grammatical stop words.
*   `extract_ngrams(texts: list[str], n_range=(1, 4), min_df=3, max_df_ratio=0.6) -> tuple[dict[str, int], dict[str, float]]`: Uses scikit-learn `CountVectorizer` and `TfidfVectorizer` to extract corpus frequency and document-level TF-IDF scores for 1-to-4-grams.

#### `concept_pipeline/yake_extractor.py`
*   `_tokenize(text: str) -> list[str]`: Tokenizes text into lowercase alphanumeric/hyphenated tokens.
*   `_sentence_tokens(text: str) -> list[list[str]]`: Splits text into sentences and tokenizes each sentence.
*   `extract_yake_keywords(texts: list[str], ...) -> dict[str, float]`: Pure-Python positional and co-occurrence ranker (`PositionalRank`). Rewards terms appearing early in chunk paragraphs (first 20% tokens get 2x weight) and scales by cross-sentence co-occurrence spread `log1p(spread)`.

#### `concept_pipeline/scorer.py`
*   `_is_noise_phrase(phrase: str) -> bool`: Flags OCR artefacts, single isolated characters, split word errors, and dummy symbols.
*   `_is_generic(phrase: str) -> bool`: Flags terms present in `_GENERIC_WORDS` or beginning/ending with stop words.
*   `_freq_normalize(freq: int, max_freq: int) -> float`: Computes `log(1 + freq) / log(1 + max_freq)`.
*   `_spread_score(phrase: str, chunk_spread: dict[str, int], total_chunks: int) -> float`: Scales chunk spread to `[0, 1]` while penalizing terms appearing in $> 50\%$ of chunks (too generic).
*   `compute_chunk_spread(phrases: set[str], texts: list[str]) -> dict[str, int]`: Counts the number of distinct chunks containing each phrase.
*   `score_candidates(...) -> list[dict]`: Combines all signals using the formula:
    $$\text{Final Score} = 2.5 \cdot \text{TF-IDF} + 1.0 \cdot \text{Freq} + 1.5 \cdot \text{NP} + 2.0 \cdot \text{YAKE} + 3.0 \cdot \text{Heading} + 3.0 \cdot \text{Def} + 1.5 \cdot \text{Spread} + 6.0 \cdot \text{Tech} + \text{Bonus}_{\text{multi-word}} - 4.0 \cdot \text{Generic} - 5.0 \cdot \text{Noise}$$
    Applies strict quality gates: structure gate ($\le 5$ words), length gate ($\ge 4$ chars unless technical), and signal agreement gate ($\ge 2$ independent signals required unless anchored by heading/definition/technical term).
*   `filter_candidates(scored: list[dict], min_score: float | None, top_k: int | None) -> list[dict]`: Filters candidates exceeding the threshold score.
*   `rank_candidates(scored: list[dict], top_k: int) -> list[dict]`: Returns top-K candidates.

#### `concept_pipeline/normalizer.py`
*   `singularize_word(word: str) -> str`: Converts plural forms to singular while respecting irregular technical terms (`matrices` $\rightarrow$ `matrix`, `queries` $\rightarrow$ `query`, `status` $\rightarrow$ `status`).
*   `_canonical_key(phrase: str) -> str`: Strips punctuation, replaces hyphens/slashes with spaces, collapses whitespace, and singularizes the terminal token.
*   `_best_display_form(canonical: str, raw_forms: list[tuple[str, int]]) -> str`: Selects display title based on priority: (1) `CAP_MAP` dictionary, (2) highest frequency raw occurrence, (3) Title-cased fallback.
*   `normalize_concept(phrase: str) -> str`: Returns canonical merge key.
*   `merge_candidates(raw_candidates: dict[str, int]) -> dict[str, dict]`: Groups raw variants by canonical key, sums frequencies, and assigns the best display representation.

#### `concept_pipeline/saver.py`
*   `save_concepts(concepts: list[str], output_path: str | Path)`: Writes `{"concepts": concepts}` formatted JSON to disk.

---

### 4. Pipeline Step 3: NLP Orchestration (`Main/AutoHKG/extract_concepts.py`)
Connects all `concept_pipeline` modules into an end-to-end extraction process.

#### Functions:
*   `extract_concepts_nlp(input_file: Path, output_file: Path, limit: int = 0, top_k: int = 1000, min_score: float = 3.0) -> list[str]`:
    Executes the 12-stage pipeline: load chunks $\rightarrow$ clean noise $\rightarrow$ detect headings $\rightarrow$ detect definitions $\rightarrow$ detect technical terms $\rightarrow$ extract noun phrases $\rightarrow$ compute n-grams and TF-IDF $\rightarrow$ compute PositionalRank $\rightarrow$ aggregate candidate union $\rightarrow$ calculate chunk spread $\rightarrow$ apply multi-signal scoring and gates $\rightarrow$ normalize and merge variants $\rightarrow$ write to `outputs/data/concepts.json`.
*   `main()`: CLI entry point supporting `--input`, `--output`, `--top-k`, `--min-score`, and `--limit`.

---

### 5. Pipeline Step 4: LLM Concept Cleaning (`Main/AutoHKG/clean_concepts.py`)
Applies LLM post-processing to clean OCR artefacts, standardize casing, remove truncated word fragments, and ensure domain-agnostic canonical terminology.

#### Functions:
*   `clean_concepts_batch(llm: LLM, raw_batch: list[str]) -> list[str]`: Prompts LLM with a 7-rule terminology refinement instruction, parses the resulting JSON array, and strips extraneous markdown.
*   `clean_concepts(input_file: Path, output_file: Path, batch_size: int = 50, limit: int = 0) -> list[str]`: Batches raw concepts (50 items/batch), calls `clean_concepts_batch`, deduplicates results, and writes sorted terms to `outputs/data/clean_concepts.json`.
*   `main()`: CLI entry point.

---

### 6. Pipeline Step 5: Chunk Vector Embeddings (`Main/AutoHKG/embed_chunks.py`)
Generates dense vector embeddings for all text chunks to enable semantic search and concept grounding.

#### Functions:
*   `load_chunks() -> list[dict]`: Reads `outputs/data/content_chunks.json`.
*   `normalize_vector(vec) -> np.ndarray`: Performs unit L2 vector normalization.
*   `_fmt_time(seconds: float) -> str`: Converts seconds into human-readable `Xh Ym Zs`.
*   `save_checkpoint(vectors: list[np.ndarray], next_batch: int)`: Writes intermediate embeddings to `chunk_embeddings.partial.npz` every 5 batches for fault tolerance.
*   `load_checkpoint(total_batches: int) -> tuple[list[np.ndarray], int]`: Loads partial embeddings if a previous run was interrupted.
*   `get_embeddings_api(texts: list[str]) -> np.ndarray`: Remote OpenAI-compatible API embedder.
*   `_load_flag_model()`: Loads `BAAI/bge-m3` using `FlagEmbedding` library with CUDA GPU auto-detection and FP16 inference.
*   `_load_st_model()`: Fallback loader using `sentence-transformers.SentenceTransformer`.
*   `_encode_flag(model, batch: list[str]) -> np.ndarray`: Encodes texts to dense vectors via `FlagEmbedding`.
*   `_encode_st(model, batch: list[str]) -> np.ndarray`: Encodes texts via SentenceTransformer.
*   `get_embeddings_local(texts: list[str]) -> np.ndarray`: Coordinates local batch embedding with progress bars, checkpointing, and ETA estimation.
*   `main()`: Saves metadata index to `chunk_index.json` and embeddings matrix to `chunk_embeddings.npy`.

---

### 7. Pipeline Step 6: Semantic Concept-to-Chunk Mapping (`Main/AutoHKG/map_concepts.py`)
Bridges the gap between extracted concept strings and source chunks using adaptive cosine similarity.

#### Functions:
*   `normalize_vector(vec: np.ndarray) -> np.ndarray`: Unit L2 normalization.
*   `embed_concepts_local(concepts: list[str]) -> np.ndarray`: Generates embeddings for concept strings using SentenceTransformer.
*   `detect_knee_elbow_similarity(sorted_sims: np.ndarray, candidate_window: int = 50) -> float`: Calculates the knee/elbow cutoff point on the descending cosine similarity curve using the maximum perpendicular distance to the secant line between $P_1$ and $P_N$.
*   `map_and_prune_concepts(concepts_file: Path, chunks_file: Path, embeddings_file: Path, min_rejection_similarity: float = 0.60, max_chunks_cap: int = 25) -> tuple[dict, dict, list]`:
    - Computes cosine similarity matrix: $\text{Sim} = \mathbf{E}_{\text{concepts}} \cdot \mathbf{E}_{\text{chunks}}^T$.
    - **Rejection Rule**: Discards any concept whose maximum chunk similarity is $< 0.60$ (prunes ungrounded concepts).
    - **Adaptive Retention**: Applies the knee/elbow threshold to keep only strongly associated chunks (capped at top 25 chunks).
    - Writes `concept_chunk_map.json` (concept $\rightarrow$ chunk IDs), `concept_chunk_scores.json` (similarity scores), and `mapped_concepts.json` (retained grounded concepts).
*   `main()`: CLI entry point.

---

### 8. Pipeline Step 7: Hierarchy & Prerequisite Enrichment (`Main/AutoHKG/enrich_concepts.py`)
Discovers parent-child categories and prerequisite relationships using LLM prompts strictly grounded in the cited textbook chunks.

#### Functions:
*   `load_json(path)` & `safe_parse_json(text)`: Safe file loaders and markdown code block strippers.
*   `build_chunk_lookup(chunks: list[dict]) -> dict[str, str]`: Creates `chunk_id -> text` mapping.
*   `format_source_chunks(concept_name: str, concept_chunk_map: dict, chunk_lookup: dict) -> tuple[str, list[str]]`: Assembles text from up to 4 top chunks (750 chars max per chunk) to include in the LLM prompt.
*   `parse_chunk_page(chunk_id: str) -> int | None`: Extracts page numbers from chunk IDs (`*_p12_c0` $\rightarrow$ `12`).
*   `get_candidate_concepts(...) -> list[str]`: Selects candidate concepts for the prompt using two signals: (1) direct co-occurrence in source chunk text, and (2) page proximity window ($\pm 10$ pages).
*   `verify_citation_grounding(evidence_text: str, evidence_chunk: str, chunk_lookup: dict) -> bool`: Verifies that cited evidence text is actually present in the source chunk (direct substring or $\ge 70\%$ word overlap).
*   `validate_category(...)`: Validates that coarse-grained category nodes exist in `ALL CONCEPTS`, are not self-referential, have confidence $\ge 0.60$, cite a valid chunk, and pass citation grounding.
*   `validate_prerequisite_edges(...)`: Validates prerequisite edges with confidence $\ge 0.60$, deduplication, and citation checks.
*   `validate_enrichment(...)`: Assembles and standardizes the validated enrichment record.
*   `enrich_concept(...)`: Calls LLM, parses response, runs validation, and retries up to 3 times on failure.
*   `main()`: Coordinates iteration over all mapped concepts with checkpoint/resume support, periodically writing progress to `outputs/data/enriched_concepts.json`.

---

### 9. Pipeline Step 8: DAG Cycle Breaking & Graph Output (`Main/AutoHKG/post_process_dag.py`)
Ensures pedagogical prerequisite graphs form a valid Directed Acyclic Graph (DAG) for learning paths.

#### Functions:
*   `post_process_dag(input_file: Path, output_file: Path, perform_transitive_reduction: bool = False) -> list[dict]`:
    - Constructs a `networkx.DiGraph` from all prerequisite edges with weights equal to confidence scores.
    - **Cycle Detection & Resolution**: Repeatedly detects directed cycles (`nx.find_cycle`) and removes the edge with the lowest confidence score in each cycle until the graph is strictly acyclic.
    - **Optional Transitive Reduction**: Removes redundant shortcut edges ($A \rightarrow B, B \rightarrow C \implies$ remove $A \rightarrow C$) using `nx.transitive_reduction`.
    - Updates concept prerequisite records and saves clean data to `outputs/data/cleaned_enriched_concepts.json` and `Main/graph_model/knowledge_graph.gml`.
*   `main()`: CLI entry point.

---

## 💾 Data Artifacts & Lifecycle

| Artifact File | Producer Script | Description & Role |
| :--- | :--- | :--- |
| `content_chunks.json` | `extract_and_chunk.py` | Array of text chunks with `chunk_id`, `book_name`, `page_number`, and `text`. |
| `chunk_index.json` | `embed_chunks.py` | Lightweight JSON mapping of chunk index positions to metadata. |
| `chunk_embeddings.npy` | `embed_chunks.py` | Numpy binary 2D array of dense chunk vectors (`float32`). |
| `concepts.json` | `extract_concepts.py` | Raw concept candidate strings extracted by the multi-signal statistical NLP pipeline. |
| `clean_concepts.json` | `clean_concepts.py` | Canonicalized, OCR-cleaned, Title-cased technical terms filtered by LLM. |
| `concept_chunk_map.json` | `map_concepts.py` | Grounding index mapping each concept to its qualifying source chunk IDs. |
| `concept_chunk_scores.json` | `map_concepts.py` | Cosine similarity scores for each concept-to-chunk association. |
| `mapped_concepts.json` | `map_concepts.py` | List of concept terms that met the grounding criteria ($\text{max\_sim} \ge 0.60$). |
| `enriched_concepts.json` | `enrich_concepts.py` | Concept hierarchy containing category and prerequisite relationships with chunk citations. |
| `cleaned_enriched_concepts.json` | `post_process_dag.py` | Validated, cycle-free DAG concept records ready for learning path navigation. |
| `knowledge_graph.gml` | `post_process_dag.py` | Complete Knowledge Graph exported in Graph Modeling Language (GML) for visualization and graph queries. |

---

## ⚡ FastAPI Server Architecture & Migration Plan

Currently, each file is run sequentially via CLI scripts. In the target architecture, these operations are exposed via a **FastAPI** backend supporting two primary roles: **Teacher** and **Student**.

### Teacher Workflow Endpoints
The Teacher role manages curriculum materials and builds the Knowledge Graph.

```text
POST   /api/v1/teacher/upload-material
       -> Accepts multipart/form-data (PDF/Word/PPT)
       -> Saves to books directory, generates course ID

POST   /api/v1/teacher/pipeline/start
       -> Body: { course_id, options: { chunk_size, min_score, provider } }
       -> Starts pipeline as a BackgroundTask / Celery task
       -> Returns task_id

GET    /api/v1/teacher/pipeline/status/{task_id}
       -> Returns real-time step progress (Chunking -> NLP -> Embedding -> Mapping -> Enrichment -> DAG)
       -> Supports Server-Sent Events (SSE) or WebSockets for live progress streaming

GET    /api/v1/teacher/knowledge-graph/{course_id}
       -> Returns graph nodes (categories, concepts) and edges (CONTAINS, PREREQUISITE_FOR)
       -> Enables interactive frontend visualization (vis.js / cytoscape)

PATCH  /api/v1/teacher/knowledge-graph/concept/{concept_id}
       -> Allows human-in-the-loop editing of concepts, categories, or prerequisite edges
```

### Student Workflow Endpoints
The Student role navigates learning paths, takes adaptive quizzes, and tracks mastery.

```text
GET    /api/v1/student/learning-path/{course_id}
       -> Traverses DAG starting from root concepts (nodes with 0 incoming prerequisites)
       -> Returns ordered pedagogical roadmap

GET    /api/v1/student/quiz/next-question
       -> Query params: student_id, course_id, current_concept (optional)
       -> Adaptive Engine selects next concept based on prerequisite DAG and BKT mastery state
       -> Hybrid Retriever pulls evidence chunks from Vector Store & KG neighborhood
       -> LLM generates grounded MCQ (question, 4 choices, explanation)
       -> Returns question payload (without revealing correct option)

POST   /api/v1/student/quiz/submit-answer
       -> Body: { student_id, question_id, concept, selected_option }
       -> Evaluates correctness
       -> Runs Bayesian Knowledge Tracing (BKT) update:
            Updates P(Mastery) for target concept
       -> Returns: { is_correct, explanation, updated_mastery, next_recommended_concept }

GET    /api/v1/student/mastery/{student_id}/{course_id}
       -> Returns per-concept mastery heatmap data and progress statistics
```

### Proposed FastAPI Module Structure

```text
server/
├── main.py                    # FastAPI application initialization & middleware
├── config.py                  # Pydantic Settings for environment variables
├── api/
│   ├── v1/
│   │   ├── router.py          # Master API v1 router
│   │   ├── teacher.py         # Material upload & pipeline management endpoints
│   │   ├── student.py         # Learning paths & quiz interaction endpoints
│   │   └── graph.py           # Graph visualization & query endpoints
├── core/
│   ├── pipeline_runner.py     # Asynchronous orchestration of AutoHKG steps
│   ├── bkt_engine.py          # Bayesian Knowledge Tracing calculation engine
│   ├── cognitive_rag.py       # Hybrid retrieval & grounded prompt builder
│   └── question_gen.py        # MCQ generation and validation engine
└── models/
    ├── schemas.py             # Pydantic request/response schemas
    └── db_models.py           # Database models (Student, Course, QuizAttempt, MasteryState)
```

---

## ⚙️ Environment Configuration & Dependencies

### Environment Variables (`.env`)
```bash
# LLM Provider Configuration ("gemini" or "ollama")
LLM_PROVIDER=gemini

# Google Gemini Multi-Key Rotation (comma-separated list for failover)
GEMINI_API_KEYS=key1,key2,key3
GEMINI_API_KEY=primary_key

# Local Ollama Configuration (used if LLM_PROVIDER=ollama)
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
OLLAMA_BASE_URL=http://localhost:11434

# Embedding Configuration
EMBEDDING_MODEL=BAAI/bge-m3
USE_EMBEDDING_API=false
EMBEDDING_API_BASE=http://localhost:4000/v1
EMBEDDING_API_KEY=your_key
EMBEDDING_BATCH_SIZE=32
```

### Key Python Dependencies (`requirements.txt`)
*   `fastapi`, `uvicorn`: Modern, fast async web framework and ASGI server (to be used for API server).
*   `pymupdf` (`fitz`): Fast, accurate PDF document parsing and text extraction.
*   `langchain-text-splitters`: Recursive character-based text chunking with configurable overlap.
*   `nltk`, `scikit-learn`: POS tagging, n-gram extraction, and TF-IDF calculation.
*   `sentence-transformers`, `FlagEmbedding`, `torch`: Dense vector embedding generation with GPU acceleration.
*   `google-generativeai`: Google Gemini API client.
*   `networkx`: Directed graph management, cycle detection, and topological analysis.
*   `python-dotenv`: Environment configuration management.
