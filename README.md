# Automated Hierarchical Knowledge Graph (AutoHKG) & Adaptive Cognitive-RAG Learning System
### *Comprehensive Architectural, Algorithmic, and Mathematical Specification*

---

> [!IMPORTANT]
> **LLM Context & Engineering Reference Notice**:  
> This document is the definitive master specification for the **AutoHKG & Cognitive-RAG** platform. It contains exhaustive technical details, data contracts, and complete mathematical formulations for all scoring models, vector geometry, graph algorithms, and probabilistic state estimators used across the system. It is structured to serve as an authoritative context injection source for Large Language Models (LLMs), software engineers, and researchers.

---

## 📌 Table of Contents
1. [Executive Summary & System Objectives](#1-executive-summary--system-objectives)
2. [High-Level Architecture & 4-Group Functional Blueprint](#2-high-level-architecture--4-group-functional-blueprint)
3. [Comprehensive Mathematical Formulations & Formula Index](#3-comprehensive-mathematical-formulations--formula-index)
   - [3.1. Text Chunking & Sliding Window Geometry](#31-text-chunking--sliding-window-geometry)
   - [3.2. Statistical NLP Feature Extraction Formulations](#32-statistical-nlp-feature-extraction-formulations)
   - [3.3. Multi-Signal Concept Scoring & Quality Gating Function](#33-multi-signal-concept-scoring--quality-gating-function)
   - [3.4. Dense Vector Space & Cosine Similarity Geometry](#34-dense-vector-space--cosine-similarity-geometry)
   - [3.5. Adaptive Knee/Elbow Concept Grounding Algorithm](#35-adaptive-kneeelbow-concept-grounding-algorithm)
   - [3.6. Source-Grounded Citation Verification & Lexical Overlap Metric](#36-source-grounded-citation-verification--lexical-overlap-metric)
   - [3.7. Prerequisite Graph Cycle Elimination & Transitive Reduction](#37-prerequisite-graph-cycle-elimination--transitive-reduction)
   - [3.8. Bayesian Knowledge Tracing (BKT) Mathematical Engine](#38-bayesian-knowledge-tracing-bkt-mathematical-engine)
   - [3.9. Cognitive-RAG Traversal, Readiness, and Concept Selection](#39-cognitive-rag-traversal-readiness-and-concept-selection)
   - [3.10. Learner Response Confidence Model (Exponential Saturation & Consistency)](#310-learner-response-confidence-model)
   - [3.11. Multi-Concept Cognitive Load Weight Updating](#311-multi-concept-cognitive-load-weight-updating)
   - [3.12. Semantic Duplicate Question Avoidance (Cosine Distance)](#312-semantic-duplicate-question-avoidance)
4. [End-to-End Pipeline & File-by-File Implementation Reference](#4-end-to-end-pipeline--file-by-file-implementation-reference)
   - [4.A. Teacher Knowledge Construction Pipeline (`Main/AutoHKG/`)](#4a-teacher-knowledge-construction-pipeline-mainautohkg)
     - [Stage 0: LLM Core Infrastructure (`Main/llm.py`)](#stage-0-llm-core-infrastructure-mainllmpy)
     - [Stage 1: PDF Extraction & Chunking (`extract_and_chunk.py`)](#stage-1-pdf-extraction--chunking-mainautohkgextract_and_chunkpy)
     - [Stage 2: Modular NLP Candidate Extraction (`concept_pipeline/`)](#stage-2-modular-nlp-candidate-extraction-mainautohkgconcept_pipeline)
     - [Stage 3: NLP Pipeline Orchestration (`extract_concepts.py`)](#stage-3-nlp-pipeline-orchestration-mainautohkgextract_conceptspy)
     - [Stage 4: LLM Concept Canonicalization & Cleaning (`clean_concepts.py`)](#stage-4-llm-concept-canonicalization--cleaning-mainautohkgclean_conceptspy)
     - [Stage 5: Dense Vector Embeddings Generation (`embed_chunks.py`)](#stage-5-dense-vector-embeddings-generation-mainautohkgembed_chunkspy)
     - [Stage 6: Adaptive Knee/Elbow Semantic Concept Mapping (`map_concepts.py`)](#stage-6-adaptive-kneeelbow-semantic-concept-mapping-mainautohkgmap_conceptspy)
     - [Stage 7: Grounded Hierarchy & Prerequisite Enrichment (`enrich_concepts.py`)](#stage-7-grounded-hierarchy--prerequisite-enrichment-mainautohkgenrich_conceptspy)
     - [Stage 8: DAG Cycle Breaking & Knowledge Graph Export (`post_process_dag.py`)](#stage-8-dag-cycle-breaking--knowledge-graph-export-mainautohkgpost_process_dagpy)
   - [4.B. Student-Side Adaptive Learning Engine (`Main/CogRAG/`)](#4b-student-side-adaptive-learning-engine-maincograg)
     - [Module 1: Hybrid Graph & Semantic Context Retriever (`retriever.py`)](#module-1-hybrid-graph--semantic-context-retriever-maincogragretrieverpy)
     - [Module 2: Grounded Assessment Synthesizer (`question_generator.py`)](#module-2-grounded-assessment-synthesizer-maincogragquestion_generatorpy)
     - [Module 3: Learner Confidence Estimator (`confidence.py`)](#module-3-learner-confidence-estimator-maincogragconfidencepy)
     - [Module 4: Baseline BKT Profile Initializer (`mastery_scores.py`)](#module-4-baseline-bkt-profile-initializer-maincogragmastery_scorespy)
     - [Module 5: Graph-Aware Adaptive Learning & Navigation Engine (`adaptive_engine.py`)](#module-5-graph-aware-adaptive-learning--navigation-engine-maincogragadaptive_enginepy)
5. [Backend Server Architecture & Complete REST API Specification](#5-backend-server-architecture--complete-rest-api-specification)
   - [Technology Stack & System Design](#technology-stack--system-design)
   - [Database Collections & Schemas (MongoDB + Beanie)](#database-collections--schemas-mongodb--beanie)
   - [REST API Endpoints Reference](#rest-api-endpoints-reference)
6. [Data Artifacts, Schemas & Lifecycle Management](#6-data-artifacts-schemas--lifecycle-management)
7. [LLM Prompt Engineering Specifications](#7-llm-prompt-engineering-specifications)
8. [Frontend Visualization & Client Integration Protocols](#8-frontend-visualization--client-integration-protocols)
9. [Environment Configuration, Installation & Execution](#9-environment-configuration-installation--execution)

---

## 1. Executive Summary & System Objectives

Modern computer-assisted education suffers from three fundamental bottlenecks:
1. **Manual Curriculum Tagging**: Structuring complex textbooks into fine-grained topic graphs requires dozens of hours of manual labor by domain experts.
2. **Ungrounded Assessment Generation**: Generic Large Language Models hallucinate facts, invent out-of-syllabus distractor choices, and cannot provide precise chapter/page citations for their answers.
3. **Non-Adaptive Assessment Delivery**: Static quiz delivery fails to adapt to student learning curves or prerequisites, presenting advanced concepts before foundational dependencies are mastered.

**AutoHKG & Cognitive-RAG** solves these challenges through an end-to-end autonomous architecture divided into two synchronized paradigms:

```
                  ┌─────────────────────────────────────────────────────────────┐
                  │                 AUTOHKG & COGNITIVE-RAG                     │
                  └──────────────┬──────────────────────────────┬───────────────┘
                                 │                              │
                                 ▼                              ▼
          ┌────────────────────────────────────────┐  ┌────────────────────────────────────────┐
          │      TEACHER / INGESTION PARADIGM      │  │      STUDENT / LEARNING PARADIGM       │
          │         (AutoHKG Construction)         │  │     (Cognitive-RAG & Adaptive BKT)     │
          ├────────────────────────────────────────┤  ├────────────────────────────────────────┤
          │ • Academic PDF Ingestion               │  │ • DAG Topological Learning Paths       │
          │ • Recursive Overlapping Chunking       │  │ • Prerequisite Gate Evaluation         │
          │ • Multi-Signal Statistical NLP         │  │ • Grounded Cognitive-RAG Assessment    │
          │ • Dense Vector Embedding (BGE-M3)      │  │ • Real-time Bayesian Knowledge Tracing │
          │ • Adaptive Knee/Elbow Grounding        │  │ • Student Latent Mastery State Updates │
          │ • LLM Hierarchy & Citation Enrichment  │  │ • Mastery Heatmap Visualizations       │
          │ • Minimum-Weight DAG Cycle Breaking    │  │ • Dynamic Difficulty Modulation        │
          └────────────────────────────────────────┘  └────────────────────────────────────────┘
```

---

## 2. High-Level Architecture & 4-Group Functional Blueprint

The platform architecture is organized into four interconnected functional groups:

```
+----------------------------------------------------------------------------------------------------+
|                                  GROUP 1: KNOWLEDGE CONSTRUCTION                                   |
|                                                                                                    |
|  [Textbook PDF] ──> [Text Extraction & Chunking] ──> [Content Chunks JSON]                         |
|                             │                                   │                                  |
|                             ▼                                   ▼                                  |
|                 [Multi-Signal NLP Pipeline]          [Dense Vector Embedding Model]                |
|                  - Headings, Definitions, NP          - BAAI/bge-m3 (1024-dim, FP16)               |
|                  - Scikit TF-IDF & PositionalRank               │                                  |
|                             │                                   ▼                                  |
|                             ▼                         [Chunk Embeddings Matrix]                    |
|                    [Candidate Concepts]                         │                                  |
|                             │                                   │                                  |
|                             ▼                                   │                                  |
|                 [LLM Concept Normalizer]                        │                                  |
|                             │                                   │                                  |
|                             └─────────────────┬─────────────────┘                                  |
|                                               ▼                                                    |
|                              [Adaptive Knee/Elbow Vector Grounding]                                |
|                                 (Cosine Sim Matrix Dot Product)                                    |
|                                               │                                                    |
|                                               ▼                                                    |
|                                  [Mapped Grounded Concepts]                                        |
|                                               │                                                    |
|                                               ▼                                                    |
|                              [LLM Hierarchy & Prerequisite Enricher]                               |
|                               (Source Chunks Evidence & Citations)                                 |
|                                               │                                                    |
|                                               ▼                                                    |
|                                [DAG Cycle Detection & Removal]                                     |
|                               (Minimum-Weight Edge Elimination)                                    |
|                                               │                                                    |
|                                               ▼                                                    |
|                                    [Knowledge Graph (GML)]                                         |
+-----------------------------------------------+----------------------------------------------------+
                                                │
                                                │ Prerequisite Directed Acyclic Graph (DAG)
                                                ▼
+----------------------------------------------------------------------------------------------------+
|                                      GROUP 2: COGNITIVE-RAG                                        |
|                                                                                                    |
|    ┌───────────────────────────┐         ┌────────────────────────────────────────────────────┐    |
|    │   Adaptive Select Policy  │ <═════> │             Context Retrieval Subsystem            │    |
|    │  - Evaluates BKT profile  │         │  - Fetches concept-to-chunk grounded citations     │    |
|    │  - Checks prereq gates    │         │  - Gathers 1-hop graph neighborhood & category     │    |
|    └─────────────┬─────────────┘         └─────────────────────────┬──────────────────────────┘    |
|                  │                                                 │                               |
|                  └───────────────────────┬─────────────────────────┘                               |
|                                          ▼                                                         |
|                       [Constrained LLM Assessment Generator]                                       |
|                         - Grounded 4-Option MCQ Synthesis                                          |
|                         - Distractor Formulation & Source Citation                                 |
+------------------------------------------┬---------------------------------------------------------+
                                           │
                                           │ Generated Question Payload
                                           ▼
+----------------------------------------------------------------------------------------------------+
|                                 GROUP 4: USER INTERACTION & BKT                                    |
|                                                                                                    |
|    [Student Web Application] ◄─────────────────────────────────────────────────────────────────┐   |
|               │                                                                                │   |
|               │ Student Option Selection (Observed Response)                                   │   |
|               ▼                                                                                │   |
|    [Bayesian Knowledge Tracing Engine]                                                         │   |
|      P(L_t | Correct)   = Posterior given hit                                                  │   |
|      P(L_t | Incorrect) = Posterior given miss                                                 │   |
|      P(L_t+1)           = Posterior + (1 - Posterior) * P(Transit)                             │   |
+------------------------------------------┬-----------------------------------------------------+---+
                                           │
                                           │ Updated Mastery Probability P(L_t+1)
                                           ▼
+----------------------------------------------------------------------------------------------------+
|                                   GROUP 3: ADAPTIVE LEARNING                                       |
|                                                                                                    |
|    [Student Latent Knowledge Profile]: Tracks vector of per-concept masteries P(L) in MongoDB.     |
|    Enables real-time student mastery heatmaps, unlock statuses, and personalized roadmaps.         |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Comprehensive Mathematical Formulations & Formula Index

### 3.1. Text Chunking & Sliding Window Geometry
Given a document $D$ consisting of a stream of extracted characters of length $|D|$, the text splitter applies a recursive sliding window with length $L_{\text{chunk}} = 1000$ and overlap $\Delta = 200$.

- **Window Step Size ($S$)**:
  $$S = L_{\text{chunk}} - \Delta = 1000 - 200 = 800 \text{ characters}$$
- **Total Chunks Produced ($N_{\text{chunks}}$)**:
  $$N_{\text{chunks}} = \left\lceil \frac{|D| - \Delta}{S} \right\rceil = \left\lceil \frac{|D| - 200}{800} \right\rceil$$
- **Character Span for Chunk $i \in \{0, 1, \dots, N_{\text{chunks}}-1\}$**:
  $$\text{Span}(i) = \left[ i \cdot S, \, \min(|D|, \, i \cdot S + L_{\text{chunk}}) \right)$$

---

### 3.2. Statistical NLP Feature Extraction Formulations

#### 1. Term Frequency–Inverse Document Frequency (TF-IDF)
For candidate phrase $t$ in text chunk $d \in D$:
- **Term Frequency**:
  $$\text{TF}(t, d) = \frac{f_{t, d}}{\sum_{t' \in d} f_{t', d}}$$
- **Smooth Inverse Document Frequency**:
  $$\text{IDF}(t, D) = \ln\left(\frac{1 + |D|}{1 + \text{DF}(t, D)}\right) + 1$$
  where $\text{DF}(t, D) = |\{d \in D \mid t \in d\}|$.
- **Document TF-IDF Weight**:
  $$\text{TF-IDF}(t, d) = \text{TF}(t, d) \cdot \text{IDF}(t, D)$$
- **Candidate Aggregated Score**:
  $$S_{\text{tfidf}}(t) = \max_{d \in D} \left( \frac{\text{TF-IDF}(t, d)}{\|\mathbf{TF-IDF}(d)\|_2} \right)$$

#### 2. PositionalRank (Positional Bias + Sentence Spread Keyword Extraction)
Designed to run in sub-second time without graph deadlock dependencies, replacing standard YAKE.

Let chunk $c$ have sentences $S_c = (s_1, s_2, \dots, s_{|S_c|})$.
- **Sentence Positional Weight**:
  $$w_{\text{pos}}(s_k, c) = \begin{cases} 2.0 & \text{if } \frac{k}{|S_c|} < 0.20 \quad (\text{first 20\% of chunk text}) \\ 1.0 & \text{otherwise} \end{cases}$$
- **Positional Cumulative Score for Phrase $p$**:
  $$\text{Score}_{\text{pos}}(p) = \sum_{c \in D} \sum_{s_k \in S_c} w_{\text{pos}}(s_k, c) \cdot \mathbb{I}(p \in s_k)$$
- **Sentence Co-occurrence Spread**:
  $$\text{Spread}_{\text{sent}}(p) = \left| \left\{ (c, k) \mid p \in s_k \text{ of chunk } c \right\} \right|$$
- **Raw Combined Keyword Score**:
  $$\text{Score}_{\text{raw\_yake}}(p) = \text{Score}_{\text{pos}}(p) \cdot \ln(1 + \text{Spread}_{\text{sent}}(p))$$
- **Normalized YAKE Score ($S_{\text{yake}} \in [0, 1]$)**:
  $$S_{\text{yake}}(p) = \frac{\text{Score}_{\text{raw\_yake}}(p)}{\max_{p'} \text{Score}_{\text{raw\_yake}}(p')}$$

#### 3. Relative Term Frequency Normalization ($S_{\text{freq}} \in [0, 1]$)
$$\text{Freq}_{\text{norm}}(p) = \frac{\ln(1 + \text{Freq}(p))}{\ln(1 + \max_{p'} \text{Freq}(p'))}$$

#### 4. Chunk Spread Normalization ($S_{\text{spread}} \in [0, 1]$)
Let $\text{DF}_{\text{chunk}}(p)$ be the number of chunks containing $p$, and $N = |D|$:
$$S_{\text{spread}}(p) = \begin{cases} 2.0 \cdot \left(\frac{\text{DF}_{\text{chunk}}(p)}{N}\right) & \text{if } \frac{\text{DF}_{\text{chunk}}(p)}{N} \le 0.50 \\ 0.0 & \text{if } \frac{\text{DF}_{\text{chunk}}(p)}{N} > 0.50 \quad (\text{penalizes terms that are too generic}) \end{cases}$$

---

### 3.3. Multi-Signal Concept Scoring & Quality Gating Function

Candidate phrases extracted by the NLP components are scored using a linear combination of signals with safety penalties:

$$\begin{aligned}
\text{Score}_{\text{final}}(p) = \; & w_{\text{tech}} \cdot S_{\text{tech}}(p) + w_{\text{head}} \cdot S_{\text{head}}(p) + w_{\text{def}} \cdot S_{\text{def}}(p) \\
& + w_{\text{tfidf}} \cdot S_{\text{tfidf}}(p) + w_{\text{yake}} \cdot S_{\text{yake}}(p) + w_{\text{spread}} \cdot S_{\text{spread}}(p) \\
& + w_{\text{np}} \cdot S_{\text{np}}(p) + w_{\text{freq}} \cdot S_{\text{freq}}(p) \\
& + \text{Bonus}_{\text{multi}}(p) - p_{\text{gen}} \cdot P_{\text{gen}}(p) - p_{\text{noise}} \cdot P_{\text{noise}}(p)
\end{aligned}$$

#### Exact Weights & Hyperparameters:
| Parameter | Symbol | Value | Description / Rationalization |
| :--- | :--- | :--- | :--- |
| **Technical Weight** | $w_{\text{tech}}$ | **6.0** | Matches domain acronyms (`SQL`, `AST`, `1NF`, `B-tree`). |
| **Heading Weight** | $w_{\text{head}}$ | **3.0** | Chapter or section title match (authoritative domain signal). |
| **Definition Weight** | $w_{\text{def}}$ | **3.0** | Matches `"X is defined as / refers to / known as"`. |
| **TF-IDF Weight** | $w_{\text{tfidf}}$ | **2.5** | Unsupervised corpus-level salience. |
| **YAKE / Positional** | $w_{\text{yake}}$ | **2.0** | Positional priority in chunk lead text. |
| **Noun Phrase Weight** | $w_{\text{np}}$ | **1.5** | Validates POS grammatical parse tree structure. |
| **Chunk Spread Weight**| $w_{\text{spread}}$ | **1.5** | Rewards distribution across distinct chunks. |
| **Frequency Weight** | $w_{\text{freq}}$ | **1.0** | Logarithmic occurrence frequency tie-breaker. |
| **Generic Penalty** | $p_{\text{gen}}$ | **4.0** | Penalizes terms in generic stopword lists (`system`, `data`). |
| **Noise Penalty** | $p_{\text{noise}}$ | **5.0** | Hard block for boilerplate and OCR errors. |

#### Multi-Word Structural Bonus:
$$\text{Bonus}_{\text{multi}}(p) = \begin{cases} 2.5 & \text{if } 2 \le |W(p)| \le 4 \; \land \; S_{\text{tfidf}}(p) > 0.08 \; \land \; \sum \text{structural\_signals} \ge 2 \\ 0.0 & \text{otherwise} \end{cases}$$
where $\text{structural\_signals} = \left\{ \mathbb{I}(S_{\text{np}} = 1), \, \mathbb{I}(S_{\text{head}} = 1), \, \mathbb{I}(S_{\text{def}} = 1), \, \mathbb{I}(S_{\text{tech}} = 1), \, \mathbb{I}(S_{\text{tfidf}} > 0.08) \right\}$.

#### Quality Gates (Applied Prior to Scoring):
1. **Structure Gate**: Words count $|W(p)| \le 5$. Candidates with $>5$ words are discarded ($S_{\text{final}} = -100.0$).
2. **Length Gate**: Single-word terms must have character length $\ge 4$ unless in the technical seed dictionary. Single words lacking technical, heading, or definition signals are dropped.
3. **Signal Agreement Gate**:
   $$\text{SignalCount}(p) = \sum_{s \in \{\text{tfidf}, \text{np}, \text{yake}, \text{spread}, \text{head}, \text{def}, \text{tech}\}} \mathbb{I}(S_s(p) > 0.05)$$
   $$\text{If } \neg (S_{\text{head}} \lor S_{\text{def}} \lor S_{\text{tech}}) \;\land\; \text{SignalCount}(p) < 2 \implies \text{Drop Candidate}$$

---

### 3.4. Dense Vector Space & Cosine Similarity Geometry

All chunks and canonical concepts are embedded into dense continuous vector representations using `BAAI/bge-m3` ($d = 1024$ dimensions).

- **Unit L2 Vector Normalization**:
  $$\hat{\mathbf{v}} = \frac{\mathbf{v}}{\max\left(\|\mathbf{v}\|_2, \, \epsilon\right)}, \quad \|\mathbf{v}\|_2 = \sqrt{\sum_{k=1}^d v_k^2}, \quad \epsilon = 10^{-12}$$
- **Cosine Similarity via Inner Dot Product**:
  Because all vectors are pre-normalized to $\|\hat{\mathbf{e}}\|_2 = 1.0$:
  $$\text{CosineSim}(\mathbf{e}_{\text{concept}}, \mathbf{e}_{\text{chunk}}) = \frac{\mathbf{e}_{\text{concept}} \cdot \mathbf{e}_{\text{chunk}}}{\|\mathbf{e}_{\text{concept}}\|_2 \|\mathbf{e}_{\text{chunk}}\|_2} = \hat{\mathbf{e}}_{\text{concept}} \cdot \hat{\mathbf{e}}_{\text{chunk}} = \sum_{k=1}^d \hat{e}_{\text{concept}, k} \cdot \hat{e}_{\text{chunk}, k}$$
- **Full Similarity Matrix**:
  Given $M$ concepts and $N$ chunks:
  $$\mathbf{S} = \mathbf{E}_{\text{concepts}} \cdot \mathbf{E}_{\text{chunks}}^T \in \mathbb{R}^{M \times N}$$

---

### 3.5. Adaptive Knee/Elbow Concept Grounding Algorithm

Rather than using an arbitrary, rigid similarity cutoff for every concept, AutoHKG calculates the **maximum curvature (knee/elbow) point** on each concept's descending cosine similarity profile.

```
Cosine Similarity
      ▲
  1.0 │  P_1 (1, s_1)
      │   \
  0.8 │    \   Secant Line Vector
      │     \------------------------- P_N (N, s_N)
  0.6 │      \       ▲
      │       \      │  Perpendicular Distance D_i (Knee/Elbow Point)
  0.4 │        `-----*-------.._
      │                         ````-----.._
  0.2 │                                     ````-----
      └───────────────────────────────────────────────► Chunk Rank (Index i)
```

#### Step-by-Step Derivation:
1. For concept $c$, extract row vector $\mathbf{s}_c = \mathbf{S}[c, :]$.
2. Sort similarities in descending order: $s_{(1)} \ge s_{(2)} \ge \dots \ge s_{(N)}$.
3. Restrict curve analysis to the candidate window $W = \{s_{(i)} \mid s_{(i)} \ge 0.30\}$, capped at $|W| \le 50$. Let $K = |W|$.
4. Represent the similarity curve as $K$ discrete 2D points:
   $$P_i = (x_i, y_i) = (i, s_{(i)}), \quad \text{for } i \in \{1, 2, \dots, K\}$$
5. Form the secant line between the first point $P_1 = (1, s_{(1)})$ and terminal point $P_K = (K, s_{(K)})$:
   $$\vec{\mathbf{v}} = P_K - P_1 = \big(K - 1, \, s_{(K)} - s_{(1)}\big)$$
   $$\hat{\mathbf{u}} = \frac{\vec{\mathbf{v}}}{\|\vec{\mathbf{v}}\|_2} = \frac{\big(K - 1, \, s_{(K)} - s_{(1)}\big)}{\sqrt{(K - 1)^2 + (s_{(K)} - s_{(1)})^2}}$$
6. For each intermediate point $P_i$, calculate vector $\vec{\mathbf{w}}_i = P_i - P_1 = (i - 1, \, s_{(i)} - s_{(1)})$.
7. Compute the perpendicular distance from $P_i$ to the secant line:
   $$D(P_i) = \left\| \vec{\mathbf{w}}_i - (\vec{\mathbf{w}}_i \cdot \hat{\mathbf{u}})\hat{\mathbf{u}} \right\|_2 = \frac{\left| (s_{(K)} - s_{(1)})(i - 1) - (K - 1)(s_{(i)} - s_{(1)}) \right|}{\sqrt{(K - 1)^2 + (s_{(K)} - s_{(1)})^2}}$$
8. **Knee Point Selection**:
   $$i^* = \arg\max_{i \in \{1, \dots, K\}} D(P_i)$$
   $$\tau_{\text{elbow}} = s_{(i^*)}$$
9. **Dual Gating & Pruning Rule**:
   - **Rejection Floor**: Discard concept if maximum similarity is ungrounded:
     $$\text{If } s_{(1)} < 0.60 \implies \text{Reject Concept Entirely}$$
   - **Adaptive Threshold**:
     $$\tau_{\text{final}} = \max\left(\tau_{\text{elbow}}, \, 0.60\right)$$
   - **Retained Chunks Set**:
     $$\text{Chunks}(c) = \left\{ \text{chunk}_{(i)} \;\middle|\; s_{(i)} \ge \tau_{\text{final}} \right\} \quad \text{subject to } |\text{Chunks}(c)| \le 25$$

---

### 3.6. Source-Grounded Citation Verification & Lexical Overlap Metric

To prevent hallucinated links, any category or prerequisite relationship proposed by an LLM must cite an evidence string $\mathcal{E}$ from chunk text $\mathcal{C}$.

1. **Exact Substring Inclusion Check**:
   $$\mathbb{I}_{\text{exact}} = \mathbb{I}(\mathcal{E}_{\text{clean}} \subseteq \mathcal{C}_{\text{clean}})$$
2. **Lexical Token Overlap Ratio (Jaccard-like Recall Metric)**:
   Let $T(\mathcal{E})$ be the set of whitespace-tokenized words in $\mathcal{E}$, and $T(\mathcal{C})$ in $\mathcal{C}$:
   $$\text{OverlapRatio}(\mathcal{E}, \mathcal{C}) = \frac{\left| T(\mathcal{E}) \cap T(\mathcal{C}) \right|}{\left| T(\mathcal{E}) \right|}$$
3. **Acceptance Criteria**:
   $$\text{CitationValid}(\mathcal{E}, \mathcal{C}) \iff \Big( \mathbb{I}_{\text{exact}} = 1 \;\lor\; \text{OverlapRatio}(\mathcal{E}, \mathcal{C}) \ge 0.70 \Big) \;\land\; \text{Confidence} \ge 0.60$$

---

### 3.7. Prerequisite Graph Cycle Elimination & Transitive Reduction

Curriculum prerequisites must form a valid **Directed Acyclic Graph (DAG)** to allow topological sorting.

#### Minimum-Weight Feedback Arc Set Cycle Elimination
Let $G = (V, E, w)$ be the directed prerequisite graph, where directed edge $(u, v) \in E$ denotes that $u$ is a prerequisite for $v$, and $w(u, v) \in [0.60, 1.00]$ is the LLM relationship confidence.

```
Cycle Detection & Resolution:
        ┌─────────────(0.85)────────────┐
        ▼                               │
   [Concept A] ──(0.95)──► [Concept B] ──(0.72)──► [Concept C]
                                │                       │
                                └─────────(0.65)────────┘  <-- Min confidence edge removed!
```

1. Cycle detection executes Tarjan's algorithm or DFS cycle finding:
   $$\text{Cycle } \mathcal{Z} = \left( (u_1, v_1), \, (u_2, v_2), \, \dots, \, (u_m, v_m) \right)$$
2. While $\neg \text{is\_directed\_acyclic\_graph}(G)$:
   - Find edge with minimum confidence in cycle $\mathcal{Z}$:
     $$e^* = \arg\min_{e \in \mathcal{Z}} w(e)$$
   - Eliminate $e^*$ from edge set $E$:
     $$E \leftarrow E \setminus \{e^*\}$$
3. Repeat until no cycles remain.

#### Transitive Reduction
Removes redundant shortcut edges to yield the most direct pedagogical path:
$$\text{If } (u \rightarrow v \in E) \;\land\; (v \rightarrow w \in E) \;\land\; (u \rightarrow w \in E) \implies E \leftarrow E \setminus \{(u, w)\}$$

Formally, the transitive reduction $G_{\text{TR}} = (V, E_{\text{TR}})$ satisfies:
$$(u, w) \in E_{\text{TR}} \iff (u \rightarrow w \in E) \;\land\; \neg \exists \text{ path } u \rightsquigarrow w \text{ of length } \ge 2$$

---

### 3.8. Bayesian Knowledge Tracing (BKT) Mathematical Engine

Bayesian Knowledge Tracing models student concept mastery as a two-state Hidden Markov Model (HMM):
- **Latent State $L_t \in \{0, 1\}$**: 0 = Unmastered, 1 = Mastered.
- **Observed Response $O_t \in \{0, 1\}$**: 0 = Incorrect, 1 = Correct.

```
       Prior: P(L_0)
            │
            ▼
     ┌──────────────┐   Transition P(T)   ┌──────────────┐
     │ State L_t=0  ├────────────────────►│ State L_t=1  │
     └──────┬───────┘                     └──────┬───────┘
            │                                    │
    Guess   │                               Slip │
     P(G)   ▼                               P(S) ▼
     ┌──────────────┐                     ┌──────────────┐
     │ Obs: Correct │                     │Obs: Incorrect│
     └──────────────┘                     └──────────────┘
```

#### System Parameters:
| Parameter | Default Value | Mathematical Definition |
| :--- | :--- | :--- |
| **Prior Mastery** | $P(L_0) = 0.10$ | $P(L_0 = 1)$ — Probability student has initial mastery before practice. |
| **Learning Transition** | $P(T) = 0.15$ | $P(L_{t} = 1 \mid L_{t-1} = 0)$ — Probability of learning between trials. |
| **Guess Probability** | $P(G) = 0.25$ | $P(O_t = 1 \mid L_t = 0)$ — Answering correctly by guessing. |
| **Slip Probability** | $P(S) = 0.10$ | $P(O_t = 0 \mid L_t = 1)$ — Making an error despite mastering concept. |

#### 1. Bayesian Posterior Given Observation:
- **Case A: Student Answers Correctly ($O_t = 1$)**:
  $$P(L_t \mid O_t = 1) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$

- **Case B: Student Answers Incorrectly ($O_t = 0$)**:
  $$P(L_t \mid O_t = 0) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$

#### 2. Projection for Next Trial incorporating Learning Step ($P(T)$):
$$P(L_{t+1}) = P(L_t \mid O_t) + \Big(1 - P(L_t \mid O_t)\Big) \cdot P(T)$$

#### 3. Numerical Guardrails:
To prevent numerical collapse or zero-division:
- Prior input clamp: $P(L_{t-1}) \in [0.001, 0.999]$
- Posterior output clamp: $P(L_{t+1}) \in [0.01, 0.99]$

---

### 3.9. Cognitive-RAG Traversal, Readiness, and Concept Selection

Let $G = (V, E)$ be the prerequisite DAG. Student mastery state is represented as a function $\mathcal{M}: V \rightarrow [0.0, 1.0]$ where $\mathcal{M}(v) = P(L_v)$.

#### 1. Node Pedagogical Readiness Gate:
A concept $v \in V$ is unlocked ("Ready to Learn") if and only if all immediate prerequisites have attained baseline mastery:
$$\text{IsReady}(v) \iff \forall u \in \text{Predecessors}(G, v), \quad \mathcal{M}(u) \ge \tau_{\text{prereq}} \quad (\tau_{\text{prereq}} = 0.70)$$

#### 2. Concept Status Classification:
$$\text{Status}(v) = \begin{cases}
\text{Mastered} & \text{if } \mathcal{M}(v) \ge 0.85 \\
\text{In Progress} & \text{if } \text{IsReady}(v) \;\land\; 0.10 < \mathcal{M}(v) < 0.85 \\
\text{Ready to Learn} & \text{if } \text{IsReady}(v) \;\land\; \mathcal{M}(v) \le 0.10 \\
\text{Locked} & \text{if } \neg \text{IsReady}(v)
\end{cases}$$

#### 3. Next Optimal Target Concept Policy:
When the student requests practice, Cognitive-RAG selects the candidate concept maximizing educational utility:
$$v^* = \arg\min_{v \in \mathcal{U}} \mathcal{M}(v), \quad \text{where } \mathcal{U} = \{v \in V \mid \text{IsReady}(v) \;\land\; \mathcal{M}(v) < 0.85\}$$
If $\mathcal{U} = \emptyset$, it selects the concept with lowest overall mastery across all non-mastered nodes.

---

### 3.10. Learner Response Confidence Model (Exponential Saturation & Consistency)

To ensure that mastery updates reflect true knowledge rather than transient lucky guesses or slips, the system estimates a real-time **Learner Confidence Score** $\text{Conf} \in [0.0, 1.0]$.

#### 1. Attempt-Based Confidence ($\text{Conf}_{\text{attempt}}$):
Models evidence accumulation using an exponential saturation curve parameterized by rate $\alpha = 0.35$:
$$\text{Conf}_{\text{attempt}}(N) = 1 - e^{-\alpha \cdot N_{\text{attempts}}}$$
As questions attempted $N \to \infty$, $\text{Conf}_{\text{attempt}} \to 1.0$.

#### 2. Answer Consistency Confidence ($\text{Conf}_{\text{consistency}}$):
Evaluates response stability over a sliding window $R$ of the last 10 binary outcomes ($r_i \in \{0, 1\}$):
- **Empirical Accuracy Probability ($p$)**:
  $$p = \frac{1}{|R|} \sum_{r_i \in R} r_i$$
- **Bernoulli Variance / Variability ($\text{Var}$)**:
  $$\text{Variability}(p) = 4 \cdot p \cdot (1 - p) \in [0.0, 1.0]$$
  Notice that variability reaches maximum $1.0$ when $p = 0.50$ (inconsistent alternating answers) and drops to $0.0$ when $p = 1.0$ (consistently strong) or $p = 0.0$ (consistently weak).
- **Consistency Score**:
  $$\text{Conf}_{\text{consistency}}(R) = 1.0 - \text{Variability}(p) = 1.0 - 4p(1 - p)$$

#### 3. Combined Confidence & Reliability Gating:
Weighted synthesis normalized by attempt threshold $N_{\text{min}} = 6$:
$$\text{Conf}_{\text{raw}} = w_a \cdot \text{Conf}_{\text{attempt}} + w_c \cdot \text{Conf}_{\text{consistency}} \quad (w_a = 0.5, \, w_c = 0.5)$$
$$\text{Conf}_{\text{final}} = \text{Conf}_{\text{raw}} \cdot \min\left(1.0, \, \frac{N_{\text{attempts}}}{N_{\text{min}}}\right)$$

---

### 3.11. Multi-Concept Cognitive Load Weight Updating

When an assessment question evaluates multi-concept interactions (e.g., testing both `Parse Tree` and `Context-Free Grammar`), the update magnitude on latent mastery is distributed according to psychometric cognitive weights $w_i \in [0.0, 1.0]$.

- **Weight Constraints**:
  $$\sum_{i=1}^K w_i = 1.0, \quad w_{\text{primary}} \ge 0.51, \quad w_{\text{secondary}} \in [0.25, 0.40]$$
- **Weighted Latent Mastery Step**:
  For each concept $c_i$ involved in question $q$:
  1. Compute base BKT projected transition $p_{\text{new}}(c_i)$ from observation $O$.
  2. Scale the update magnitude by cognitive weight $w_i$:
     $$\Delta p(c_i) = w_i \cdot \big( p_{\text{new}}(c_i) - p_{\text{prior}}(c_i) \big)$$
     $$p_{\text{updated}}(c_i) = p_{\text{prior}}(c_i) + \Delta p(c_i)$$

---

### 3.12. Semantic Duplicate Question Avoidance (Cosine Distance)

To prevent cognitive fatigue and memorization, candidate questions generated by the LLM are checked against the historical question pool $Q_{\text{hist}}$ using dense sentence embeddings:
$$\text{Sim}_{\text{max}}(q_{\text{new}}, Q_{\text{hist}}) = \max_{q \in Q_{\text{hist}}} \big( \hat{\mathbf{e}}_{q_{\text{new}}} \cdot \hat{\mathbf{e}}_q \big)$$
$$\text{IsDuplicate}(q_{\text{new}}) \iff \text{Sim}_{\text{max}}(q_{\text{new}}, Q_{\text{hist}}) \ge \theta_{\text{dup}} \quad (\theta_{\text{dup}} = 0.82)$$
If duplicate condition triggers, the question is rejected and regenerated under an alternate cognitive style or distinct chunk anchor.

---

## 4. End-to-End Pipeline & File-by-File Implementation Reference

```text
Mega-Project/
├── Main/
│   ├── llm.py                                 # Core LLM wrapper (Gemini multi-key rotation + Ollama)
│   ├── books/                                 # Raw input PDF repository
│   ├── outputs/data/                          # Persisted pipeline JSON & NPY data artifacts
│   ├── outputs/graph_model/                   # Exported Knowledge Graph GML
│   ├── AutoHKG/                               # 4.A: Teacher Knowledge Construction Pipeline
│   │   ├── extract_and_chunk.py               # Stage 1: PyMuPDF + RecursiveCharacterTextSplitter
│   │   ├── concept_pipeline/                  # Stage 2: 12-Module Statistical NLP Engine
│   │   ├── extract_concepts.py                # Stage 3: Orchestrates Stage 2 NLP candidate extraction
│   │   ├── clean_concepts.py                  # Stage 4: LLM canonicalization & OCR denoiser
│   │   ├── embed_chunks.py                    # Stage 5: Dense embeddings (BAAI/bge-m3)
│   │   ├── map_concepts.py                    # Stage 6: Adaptive knee/elbow cosine grounding
│   │   ├── enrich_concepts.py                 # Stage 7: Citation-grounded hierarchy & prerequisites
│   │   └── post_process_dag.py                # Stage 8: NetworkX cycle elimination & DAG builder
│   └── CogRAG/                                # 4.B: Student Adaptive Learning & Assessment Engine
│       ├── retriever.py                       # Module 1: Graph-augmented semantic context retriever
│       ├── question_generator.py              # Module 2: Psychometric MCQ generator with cognitive weights
│       ├── confidence.py                      # Module 3: Learner attempt & consistency confidence estimator
│       ├── mastery_scores.py                  # Module 4: Baseline BKT profile initializer & state tracker
│       └── adaptive_engine.py                 # Module 5: Adaptive learning path & BKT update engine
```

---

### 4.A. Teacher Knowledge Construction Pipeline (`Main/AutoHKG/`)

### Stage 0: LLM Core Infrastructure (`Main/llm.py`)
Provides a fault-tolerant interface supporting Google Gemini (with automated cyclic multi-key failover upon HTTP 429 quota exhaustion) and local Ollama inference.

#### Classes & Key Methods:
- `GeminiKeyManager`:
  - `__init__(keys)`: Reads comma-separated keys from `GEMINI_API_KEYS` and single key from `GEMINI_API_KEY`.
  - `get_current_key() -> str`: Returns active key.
  - `rotate_key() -> str`: Rotates cyclically: $\text{idx} \leftarrow (\text{idx} + 1) \pmod K$.
- `OllamaLLM`:
  - `__init__(sys_msg, model_name, temperature, base_url, json_mode)`: Sets up local endpoint.
  - `get_response(usr_msg, max_retries) -> str`: Posts to `{base_url}/api/chat`, relaxing JSON constraints on final retry.
- `LLM`:
  - `get_response(usr_msg) -> str`: Transparently dispatches prompt. Catches rate limit errors (Google 429), calls `rotate_key()`, reconfigures the client, and seamlessly retries.

---

### Stage 1: PDF Extraction & Chunking (`Main/AutoHKG/extract_and_chunk.py`)
- **PDF Extraction**: Uses PyMuPDF (`fitz`) to extract text per page, recording `{page_number, text}`.
- **Cleaning**: Replaces newlines, collapses spaces, and cleans hyphen breaks.
- **Recursive Splitting**: Uses `langchain_text_splitters.RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`.
- **Output Artifact**: Saves array of chunk objects with `{chunk_id, book_name, page_number, text}` to `outputs/data/content_chunks.json`.

---

### Stage 2: Modular NLP Candidate Extraction (`Main/AutoHKG/concept_pipeline/`)
A pure statistical NLP extraction engine consisting of 12 modular files:

1. `loader.py`: Reads `content_chunks.json`, verifies required fields (`chunk_id`, `text`), and discards malformed chunks.
2. `cleaner.py`: Strips OCR control characters, hyphenated splits (`algo-\n-rithm` $\rightarrow$ `algorithm`), publisher boilerplate, ISBNs, and copyright notices.
3. `headings.py`: Scans text using regex patterns for `Chapter \d+`, `Section \d+`, numbered headers (`^\d+(\.\d+)*`), and uppercase titles.
4. `definitions.py`: Detects formal definitional statements using patterns like `X is defined as`, `X refers to`, `X is called`, `X is known as`.
5. `technical_terms.py`: Detects domain-specific CS acronyms (`SQL`, `ACID`, `BCNF`), Normal Forms (`1NF`-`5NF`), Tree algorithms (`B-Tree`, `B+ Tree`), and relational symbols.
6. `noun_phrases.py`: Uses NLTK Treebank POS-tagging (`averaged_perceptron_tagger_eng`) with chunk grammar `<DT>?<JJ.*|VBG|VBN>*<NN.*>+`. Strips leading determiners.
7. `ngrams.py`: Calculates document-level TF-IDF and n-gram frequencies (1-to-4 grams) using `CountVectorizer` and `TfidfVectorizer`.
8. `yake_extractor.py`: Computes `PositionalRank` using sentence positional weighting and cross-sentence co-occurrence spread.
9. `scorer.py`: Combines all 8 signals, enforces the multi-signal scoring equation, applies the structure gate ($\le 5$ words), length gate, and signal agreement gate ($\ge 2$ independent signals).
10. `normalizer.py`: Singularizes nouns (`matrices` $\rightarrow$ `matrix`), removes punctuation, standardizes casing via `CAP_MAP`, and merges candidate variants.
11. `saver.py`: Serializes concept candidate records into `outputs/data/concepts.json`.

---

### Stage 3: NLP Pipeline Orchestration (`Main/AutoHKG/extract_concepts.py`)
Orchestrates the 12 submodules of `concept_pipeline`:
- Loads chunks $\rightarrow$ Cleans noise $\rightarrow$ Extracts headings, definitions, technical terms, noun phrases, TF-IDF, PositionalRank $\rightarrow$ Calculates chunk spread $\rightarrow$ Scores and gates candidates $\rightarrow$ Normalizes and merges $\rightarrow$ Outputs top $K$ candidates (default: 1000 concepts, $\text{min\_score} = 3.0$).

---

### Stage 4: LLM Concept Canonicalization & Cleaning (`Main/AutoHKG/clean_concepts.py`)
Cleans noisy NLP candidates using LLM batches (50 items/batch).
- Enforces a 7-rule canonicalization prompt:
  1. Fix broken OCR fragments.
  2. Normalize to Title Case (preserving acronyms).
  3. Remove publisher metadata and exercise fragments.
  4. Expand truncated prefixes/suffixes.
  5. Deduplicate synonyms.
  6. Discard sentence fragments.
  7. Retain only valid domain concepts.
- Writes cleaned canonical list to `outputs/data/clean_concepts.json`.

---

### Stage 5: Dense Vector Embeddings Generation (`Main/AutoHKG/embed_chunks.py`)
- Loads `content_chunks.json`.
- Uses `BAAI/bge-m3` via `FlagEmbedding` or `sentence-transformers` with CUDA FP16 acceleration.
- Batch size: 32 chunks per step. Includes checkpointing to `chunk_embeddings.partial.npz` every 5 batches.
- Performs unit L2 normalization: $\hat{\mathbf{v}} = \mathbf{v} / \|\mathbf{v}\|_2$.
- Outputs: `outputs/data/chunk_index.json` and binary `outputs/data/chunk_embeddings.npy`.

---

### Stage 6: Adaptive Knee/Elbow Semantic Concept Mapping (`Main/AutoHKG/map_concepts.py`)
- Embeds cleaned concepts into the dense embedding space.
- Calculates dense similarity matrix: $\mathbf{S} = \mathbf{E}_{\text{concepts}} \cdot \mathbf{E}_{\text{chunks}}^T$.
- Rejects concepts with maximum similarity $< 0.60$.
- Calculates perpendicular distance to secant line on the descending similarity curve to identify the knee/elbow point $\tau_{\text{elbow}}$.
- Retains chunks with $\text{Sim} \ge \max(\tau_{\text{elbow}}, 0.60)$, capped at top 25 chunks.
- Outputs:
  - `concept_chunk_map.json`: Mapping of `concept_name -> [chunk_ids]`.
  - `concept_chunk_scores.json`: Mapping of `concept_name -> [{chunk_id, similarity}]`.
  - `mapped_concepts.json`: List of grounded concepts passing the threshold.

---

### Stage 7: Grounded Hierarchy & Prerequisite Enrichment (`Main/AutoHKG/enrich_concepts.py`)
- For each grounded concept, retrieves its top 3 qualifying source chunks.
- Assembles candidate pool using chunk co-occurrence, text mentions, and page proximity ($\pm 3$ pages).
- Prompts LLM to select 1 coarse-grained parent category and prerequisite relationships.
- Verifies that cited evidence satisfies the token overlap metric ($\ge 70\%$) and edge confidence threshold ($\ge 0.60$).
- Outputs: `outputs/data/enriched_concepts.json`.

---

### Stage 8: DAG Cycle Breaking & Knowledge Graph Export (`Main/AutoHKG/post_process_dag.py`)
- Builds directed prerequisite graph $G = (V, E, w)$ using `networkx.DiGraph`.
- Iteratively detects cycles (`nx.find_cycle`) and removes the edge with the lowest confidence score until the graph is strictly acyclic.
- Performs optional transitive reduction (`nx.transitive_reduction`) to prune shortcut edges.
- Exports validated artifacts:
  - `outputs/data/cleaned_enriched_concepts.json`
  - `Main/graph_model/knowledge_graph.gml`

---

### 4.B. Student-Side Adaptive Learning Engine (`Main/CogRAG/`)

While `AutoHKG` builds the knowledge graph during teacher ingestion, `Main/CogRAG/` drives the interactive student learning experience. It implements graph-guided retrieval, grounded MCQ assessment generation, confidence-aware navigation, and multi-concept Bayesian Knowledge Tracing.

```
+──────────────────────────────────────────────────────────────────────────────────────────+
|                               Main/CogRAG/ Architecture Flow                             |
|                                                                                          |
|       [knowledge_graph.gml] + [mastery_scores.json] + [navigation_state.json]            |
|                                    │                                                     |
|                                    ▼                                                     |
|                     [adaptive_engine.py: select_next_concept()]                          |
|                       - Checks BKT P(L) and prerequisite gates                           |
|                       - Weak (<=0.40) -> Remediate to prerequisite                       |
|                       - Mastered (>=0.85) -> Advance along successor edge                |
|                                    │                                                     |
|                         Selected Target Concept & Difficulty                             |
|                                    ▼                                                     |
|                      [retriever.py: retrieve_context_for_concepts()]                     |
|                       - 1-hop neighborhood: parents (CONTAINS), prereqs                  |
|                       - Candidate chunk pool + dense BGE-M3 semantic ranking             |
|                       - Top-K grounded text context assembly                             |
|                                    │                                                     |
|                         Grounded Context & Chunks                                        |
|                                    ▼                                                     |
|                   [question_generator.py: generate_question()]                           |
|                       - 4-choice MCQ with style template & explanation                   |
|                       - Psychometric cognitive weights (sum = 1.0)                       |
|                       - Dense embedding semantic duplicate rejection                     |
|                                    │                                                     |
|                         Student Answer Submission (A/B/C/D)                              |
|                                    ▼                                                     |
|                      [adaptive_engine.py: process_answer()]                              |
|                       - Evaluates correctness                                            |
|                       - confidence.py: compute_confidence(attempts, consistency)        |
|                       - BKT Update: Delta P(L) = weight * (P_new - P_prior)              |
|                       - Updates mastery_scores.json and navigation_state.json            |
+──────────────────────────────────────────────────────────────────────────────────────────+
```

---

#### Module 1: Hybrid Graph & Semantic Context Retriever (`Main/CogRAG/retriever.py`)
Fetches topological graph neighborhoods and dense vector chunk representations to build context for question generation.

- **Lazy Singleton Loaders**:
  - `get_graph() -> nx.DiGraph`: Reads `outputs/graph_model/knowledge_graph.gml` with fallback to `Main/graph_model/`.
  - `get_chunk_lookup() -> dict[str, str]`: Reads `content_chunks.json` into an in-memory `chunk_id -> text` dictionary.
  - `get_concept_chunk_map() -> dict[str, list[str]]`: Reads `concept_chunk_map.json`.
  - `get_chunk_embeddings_data()`: Loads `chunk_index.json` and unit-normalized `chunk_embeddings.npy`.
- **Topological Traversal Functions**:
  - `get_parents(graph, concept) -> list[str]`: Traverses incoming `CONTAINS` edges.
  - `get_prerequisites(graph, concept) -> list[str]`: Traverses incoming `PREREQUISITE_FOR` edges.
  - `get_neighbors(graph, concept) -> list[str]`: Traverses outgoing `PREREQUISITE_FOR` edges.
- **Semantic Ranking & Retrieval**:
  - `embed_query(text: str) -> np.ndarray`: Encodes rich query string using the active `BAAI/bge-m3` model ($d = 1024$), matching the chunk embeddings matrix.
  - `rank_chunks_semantically(candidate_chunk_ids, query_text) -> list[tuple[float, str]]`: Computes dot-product cosine similarity between query vector and candidate chunk vectors.
  - `retrieve_context(concept_name, max_chunks=10)`: Assembles 1-hop graph context and returns top ranked chunks with similarity scores.
  - `retrieve_context_for_concepts(primary_concept, secondary_concepts, max_chunks=12)`: Builds multi-concept query combining primary and secondary prerequisite terms.

---

#### Module 2: Grounded Assessment Synthesizer (`Main/CogRAG/question_generator.py`)
Generates difficulty-calibrated assessment questions with psychometric cognitive weights grounded in source chunks.

- **Key Functions**:
  - `generate_question(concept_name, difficulty, asked_ids, wrong_ids, secondary_concepts) -> dict`: Main generator function. Coordinates retrieval, prompt formulation, LLM inference, JSON parsing, validation, and semantic deduplication.
  - `choose_question_style(concept, difficulty) -> str`: Selects question templates cyclically across:
    - *Easy*: definition-based, terminology-based, basic identification, simple recognition.
    - *Medium*: comparison-based, why/how reasoning, identify correct statement, relationship analysis.
    - *Hard*: application scenario, error spotting / debugging, case-based reasoning, best design choice.
  - `is_semantically_duplicate(new_q, old_q_list, threshold=0.82) -> tuple[bool, float, str]`: Uses dense sentence embeddings to reject candidate questions too semantically similar to recently asked items.
  - `normalize_concept_weights(concept_weights, primary_concept, allowed_concepts) -> dict[str, float]`: Normalizes cognitive load weights such that $\sum w_i = 1.0$, $w_{\text{primary}} \ge 0.51$, and secondary dependencies receive proportional weights ($0.25 - 0.40$).
  - `save_mcq(primary_concept, difficulty, question) -> bool`: Caches generated questions in `outputs/data/generated_mcqs.json` for reuse.

---

#### Module 3: Learner Confidence Estimator (`Main/CogRAG/confidence.py`)
Estimates student response reliability to guard against premature mastery advancement.

- **Key Functions**:
  - `compute_attempt_confidence(questions_attempted, saturation_rate=0.35) -> float`: Evaluates evidence volume:
    $$\text{Conf}_{\text{attempt}} = 1.0 - e^{-0.35 \cdot N_{\text{attempts}}}$$
  - `compute_consistency_confidence(recent_answers) -> float`: Evaluates answer stability over the last 10 trials using Bernoulli variance:
    $$\text{Conf}_{\text{consistency}} = 1.0 - 4p(1 - p), \quad \text{where } p = \text{mean}(r_i)$$
  - `compute_confidence(questions_attempted, recent_answers) -> float`: Returns combined confidence in $[0.0, 1.0]$, scaled down by $(N_{\text{attempts}} / 6)$ when fewer than 6 attempts have been recorded.

---

#### Module 4: Baseline BKT Profile Initializer (`Main/CogRAG/mastery_scores.py`)
Initializes and serializes baseline student mastery states across the prerequisite DAG.

- **Key Functions**:
  - `resolve_concepts_file() -> Path`: Dynamically discovers the most refined concept artifact (`cleaned_enriched_concepts.json` $\to$ `enriched_concepts_dag.json` $\to$ `enriched_concepts.json`).
  - `load_concepts() -> list[str]`: Loads and deduplicates concept names from JSON files.
  - `create_initial_mastery(concepts, initial_p_know=0.10) -> dict`: Builds per-concept state records:
    ```json
    {
      "p_know": 0.10,
      "confidence": 0.0,
      "questions_attempted": 0,
      "correct_answers": 0,
      "recent_answers": [],
      "asked_question_ids": [],
      "wrong_question_ids": []
    }
    ```
  - `save_mastery(data)`: Persists profile to `outputs/data/mastery_scores.json`.
  - `initialize_mastery_profile(force=False)`: Programmatic entry point for initializing student state.

---

#### Module 5: Graph-Aware Adaptive Learning & Navigation Engine (`Main/CogRAG/adaptive_engine.py`)
The central orchestrator connecting graph traversal, question generation, and real-time Bayesian Knowledge Tracing.

- **Key Functions**:
  - `select_next_concept() -> str`: Executes the pedagogical navigation policy:
    1. *Root Selection*: On first run, starts from the weakest root node (nodes with zero incoming prerequisites).
    2. *Prerequisite Remediation*: If current concept mastery is weak ($P(L) \le 0.40$), branches back to the weakest unmastered prerequisite and stores the current node as a `return_target`.
    3. *Return Target Resumption*: Once prerequisites achieve mastery, resumes the `return_target`.
    4. *Forward Progression*: If current concept is mastered ($P(L) \ge 0.85$), advances along outgoing prerequisite edges prioritizing highest edge confidence.
    5. *Branch Exhaustion*: Jumps to the weakest unmastered global concept.
  - `get_adaptive_question() -> dict[str, Any]`: Determines next target concept, modulates difficulty (`easy`, `medium`, `hard`), selects unmastered secondary prerequisite concepts, and calls `generate_question()`.
  - `update_mastery_multi(concepts, question_id, correct, concept_weights) -> dict`: Updates latent mastery for each concept involved in the question:
    $$\text{Posterior} = \begin{cases} \frac{p \cdot (1 - P(S))}{p \cdot (1 - P(S)) + (1 - p) \cdot P(G)} & \text{if Correct} \\ \frac{p \cdot P(S)}{p \cdot P(S) + (1 - p) \cdot (1 - P(G))} & \text{if Incorrect} \end{cases}$$
    $$p_{\text{new}} = \text{Posterior} + (1 - \text{Posterior}) \cdot P(T)$$
    $$\Delta p = w_i \cdot (p_{\text{new}} - p_{\text{prior}})$$
    $$p_{\text{updated}} = p_{\text{prior}} + \Delta p$$
  - `process_answer(concept, question_data, user_answer) -> dict`: Evaluates student option selection, runs multi-concept BKT updates, calculates updated confidence, and persists progress to `mastery_scores.json`.
  - `interactive_session()`: Interactive terminal CLI study mode (`python Main/CogRAG/adaptive_engine.py --interactive`).

---

## 5. Backend Server Architecture & Complete REST API Specification

### Technology Stack & System Design
- **Web Framework**: FastAPI with asynchronous event loops (`uvicorn`).
- **Database**: MongoDB (via `motor` async driver and `beanie` Object Document Mapper).
- **Authentication**: JWT Bearer Tokens (HS256) with `passlib[bcrypt]` password hashing and Role-Based Access Control (`teacher` vs `student`).
- **Graph Modeling**: NetworkX for topological sorting and cycle detection.
- **Orchestration**: Asynchronous `BackgroundTasks` runner executing non-destructive imports of `Main/` algorithms.

---

### Database Collections & Schemas (MongoDB + Beanie)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MONGODB DATABASE                                       │
├─────────────────────────┬──────────────────────────┬───────────────────────────────────┤
│ Collection Name         │ Beanie Document Class    │ Key Document Fields               │
├─────────────────────────┼──────────────────────────┼───────────────────────────────────┤
│ users                   │ UserDocument             │ email, hashed_password, role      │
│ courses                 │ CourseDocument           │ title, pdf_path, status, task_id  │
│ pipeline_tasks          │ PipelineTaskDocument     │ stage, progress, logs, metrics    │
│ content_chunks          │ ContentChunkDocument     │ course_id, chunk_id, page, text   │
│ concepts                │ ConceptDocument          │ course_id, concept, final_score   │
│ concept_chunk_mappings  │ ConceptChunkMappingDoc   │ course_id, concept, chunks[]      │
│ enriched_concepts       │ EnrichedConceptDocument  │ course_id, concept, prereqs[]     │
│ knowledge_graphs        │ KnowledgeGraphDocument   │ course_id, nodes[], edges[]       │
│ student_mastery_states  │ StudentMasteryDocument   │ student_id, concept, mastery P(L) │
│ quiz_attempts           │ QuizAttemptDocument      │ student_id, question, correct     │
└─────────────────────────┴──────────────────────────┴───────────────────────────────────┘
```

---

### REST API Endpoints Reference

#### 1. Authentication (`/api/v1/auth`)
| Method | Path | Auth | Request Body | Response Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/register` | None | `{email, password, role: "teacher"\|"student"}` | Returns created user object. |
| `POST` | `/login` | None | `OAuth2PasswordRequestForm (username, password)` | Returns `{access_token, token_type: "bearer"}`. |
| `GET` | `/me` | Bearer | None | Returns active user profile and role. |

#### 2. Teacher Ingestion & Pipeline (`/api/v1/teacher`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/upload` | Teacher | Accepts multipart PDF file. Creates course entry. |
| `POST` | `/pipeline/start/{course_id}` | Teacher | Triggers 7-stage AutoHKG pipeline in background. Returns `task_id`. |
| `GET` | `/pipeline/status/{task_id}` | Teacher | Returns `{current_stage, progress_percentage, logs[]}`. |
| `GET` | `/knowledge-graph/{course_id}` | Teacher | Returns `{nodes[], edges[]}` formatted for Vis.js / Cytoscape. |
| `PATCH`| `/knowledge-graph/{course_id}/concept` | Teacher | Human-in-the-loop editing of category/prerequisite edges. |

#### 3. Student Adaptive Learning (`/api/v1/student`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/courses` | Student | Lists courses with completed knowledge graphs. |
| `GET` | `/learning-path/{course_id}` | Student | Returns topologically ordered concepts with `Mastered`, `In Progress`, `Ready to Learn`, or `Locked` status. |
| `GET` | `/quiz/next-question/{course_id}` | Student | Cognitive-RAG selects next optimal concept and returns grounded 4-option MCQ. |
| `POST`| `/quiz/submit-answer` | Student | Submits `{question_id, concept_name, selected_option}`. Executes BKT update and returns updated $P(L)$. |
| `GET` | `/mastery/{course_id}` | Student | Returns per-concept mastery percentages and counts for heatmaps. |

#### 4. Graph Export (`/api/v1/graph`)
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/{course_id}` | Bearer | Returns graph nodes and edges. |
| `GET` | `/{course_id}/export/gml` | Bearer | Streams graph in standard GML format. |

---

## 6. Data Artifacts, Schemas & Lifecycle Management

All pipeline execution artifacts are persisted to `outputs/data/` as well as MongoDB:

```
PDF Document ──► content_chunks.json ──► chunk_embeddings.npy
                       │
                       ▼
                 concepts.json ──► clean_concepts.json
                                          │
                                          ▼
                               concept_chunk_map.json ──► mapped_concepts.json
                                                                 │
                                                                 ▼
                                                      enriched_concepts.json
                                                                 │
                                                                 ▼
                                                      knowledge_graph.gml
```

### Artifact Schema Definitions:

#### 1. `content_chunks.json`
```json
[
  {
    "chunk_id": "Compiler_book_p12_c0",
    "book_name": "Compiler_book.pdf",
    "page_number": 12,
    "text": "A compiler is a program that can read a program in one language..."
  }
]
```

#### 2. `clean_concepts.json`
```json
{
  "concepts": [
    "Abstract Syntax Tree",
    "Activation Record",
    "Code Generation",
    "Control Flow Graph",
    "Dead Code Elimination",
    "Lexical Analysis"
  ]
}
```

#### 3. `concept_chunk_map.json`
```json
{
  "Abstract Syntax Tree": [
    "Compiler_book_p117_c0",
    "Compiler_book_p94_c2",
    "Compiler_book_p122_c0"
  ]
}
```

#### 4. `enriched_concepts.json`
```json
[
  {
    "concept": "Abstract Syntax Tree",
    "node_type": "fine_grained_concept",
    "coarse_grained_category": ["Syntax Tree"],
    "parent_concept": ["Syntax Tree"],
    "category_edge": {
      "concept": "Syntax Tree",
      "confidence": 0.95,
      "evidence_chunk": "Compiler_book_p117_c0",
      "evidence_text": "Abstract-syntax trees, or simply syntax trees, were introduced in Section..."
    },
    "prerequisites": ["Parse Tree"],
    "prerequisite_edges": [
      {
        "prerequisite": "Parse Tree",
        "confidence": 0.85,
        "evidence_chunk": "Compiler_book_p94_c2",
        "evidence_text": "Abstract syntax trees, or simply syntax trees, resemble parse trees to an extent."
      }
    ]
  }
]
```

---

## 7. LLM Prompt Engineering Specifications

### 1. Hierarchy & Prerequisite Enrichment Prompt
```text
You are an educational Knowledge Graph expert.
Structure: Coarse-Grained Category Node -> CONTAINS -> Fine-Grained Concept Node

CURRENT CONCEPT: {concept}
CANDIDATE CONCEPTS: {all_concepts}

SOURCE CHUNKS:
{source_chunks}

TASK:
1. Identify 1 coarse-grained category (that CONTAINS the current concept) from CANDIDATE CONCEPTS using ONLY the provided SOURCE CHUNKS.
2. Identify strong prerequisite concepts from CANDIDATE CONCEPTS using ONLY the provided SOURCE CHUNKS.
3. Every category or prerequisite relationship MUST cite a valid evidence chunk ID and short supporting evidence text.
4. If source evidence is weak or missing, do NOT create that relationship.
5. Return ONLY valid JSON. No explanations.

OUTPUT JSON SCHEMA:
{
  "concept": "{concept}",
  "node_type": "fine_grained_concept",
  "coarse_grained_category": {
    "concept": "Parent Category Name",
    "confidence": 0.90,
    "evidence_chunk": "chunk_id",
    "evidence_text": "verbatim citation text"
  },
  "prerequisite_edges": [
    {
      "prerequisite": "Prerequisite Concept Name",
      "confidence": 0.85,
      "evidence_chunk": "chunk_id",
      "evidence_text": "verbatim citation text"
    }
  ]
}
```

---

### 2. Cognitive-RAG Assessment Generation Prompt
```text
You are an expert educational assessment designer.
Generate an educational Multiple-Choice Question (MCQ) testing comprehension of the concept: "{concept_name}".

STRICT CONSTRAINTS:
1. Base the question and options EXCLUSIVELY on the provided SOURCE TEXT CHUNKS below.
2. Do NOT invent facts or cite external information not grounded in the chunks.
3. Formulate exactly 4 distinct answer choices (A, B, C, D).
4. Exactly ONE choice must be clearly correct; the other three must be plausible distractors.
5. Provide a concise explanation justifying why the correct answer is true, referencing the source text.
6. Output MUST be valid JSON only.

CONCEPT:
{concept_name}

CATEGORY / CONTEXT:
{category_info}

SOURCE TEXT CHUNKS:
{source_chunks_text}

OUTPUT JSON SCHEMA:
{
  "question": "The question text here...",
  "options": [
    "Option text 1",
    "Option text 2",
    "Option text 3",
    "Option text 4"
  ],
  "correct_answer": "Exact text matching one of the 4 options above",
  "explanation": "Clear explanation referencing chunk evidence..."
}
```

---

## 8. Frontend Visualization & Client Integration Protocols

### 1. Vis.js Network Graph Integration
The server's `/api/v1/teacher/knowledge-graph/{course_id}` endpoint outputs visualization-ready nodes and edges:

```javascript
import { Network } from "vis-network";

const response = await fetch(`/api/v1/teacher/knowledge-graph/${courseId}`, {
  headers: { Authorization: `Bearer ${jwtToken}` }
});
const { nodes, edges } = await response.json();

const container = document.getElementById("knowledge-graph");
const data = {
  nodes: nodes.map(n => ({
    id: n.id,
    label: n.label,
    shape: n.type === "coarse_grained_category" ? "box" : "ellipse",
    color: n.type === "coarse_grained_category" ? "#4F46E5" : "#10B981",
    font: { color: "#ffffff", size: 14 }
  })),
  edges: edges.map(e => ({
    from: e.source,
    to: e.target,
    label: e.relation,
    arrows: "to",
    dashes: e.relation === "CONTAINS",
    color: { color: e.relation === "CONTAINS" ? "#9CA3AF" : "#3B82F6" },
    title: `Confidence: ${e.confidence}`
  }))
};

new Network(container, data, {
  layout: { hierarchical: { direction: "UD", sortMethod: "directed", levelSeparation: 120 } },
  physics: { hierarchicalRepulsion: { nodeDistance: 160 } }
});
```

### 2. Student Learning Path Status Rendering
When consuming `/api/v1/student/learning-path/{course_id}`, client UIs should map states as follows:
- **`Mastered`** ($P(L) \ge 0.85$): Green card with completed badge.
- **`In Progress`** ($0.10 < P(L) < 0.85$, prerequisites met): Blue card showing progress bar: `width = mastery_percentage%`.
- **`Ready to Learn`** ($P(L) \le 0.10$, prerequisites met): Amber card with active "Practice" CTA button.
- **`Locked`** (Prerequisites unsatisfied): Gray card with padlock icon and list of missing prerequisite concepts.

---

## 9. Environment Configuration, Installation & Execution

### 1. Environment Configuration (`.env`)
Create a `.env` file in the workspace root:

```env
# ── MongoDB Connection ─────────────────────────────────────────────
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=mega_project

# ── JWT Authentication ────────────────────────────────────────────
JWT_SECRET_KEY=replace-with-a-secure-random-secret-key-for-jwt-signing
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── LLM Configuration ─────────────────────────────────────────────
LLM_PROVIDER=gemini
GEMINI_API_KEY=primary_gemini_api_key
GEMINI_API_KEYS=key1,key2,key3
LLM_MODEL=gemini-1.5-flash

# ── Local Ollama Fallback ─────────────────────────────────────────
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
OLLAMA_BASE_URL=http://localhost:11434

# ── Dense Vector Embedding ────────────────────────────────────────
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_BATCH_SIZE=32
```

### 2. Dependency Installation
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Running the Complete System

#### Option A: FastAPI Server (Teacher + Student Interactive Workflows)
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be accessible at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Option B: Standalone Pipeline Execution (CLI Mode)
To run the AutoHKG pipeline sequentially on a textbook placed in `Main/books/`:
```bash
# Step 1: Text extraction and chunking
python Main/AutoHKG/extract_and_chunk.py

# Step 2: Multi-signal statistical NLP concept candidate extraction
python Main/AutoHKG/extract_concepts.py --top-k 1000 --min-score 3.0

# Step 3: LLM concept canonicalization and noise cleaning
python Main/AutoHKG/clean_concepts.py

# Step 4: Dense vector chunk embeddings generation
python Main/AutoHKG/embed_chunks.py

# Step 5: Adaptive knee/elbow cosine similarity grounding
python Main/AutoHKG/map_concepts.py

# Step 6: Grounded hierarchy and prerequisite enrichment
python Main/AutoHKG/enrich_concepts.py

# Step 7: NetworkX cycle elimination and DAG assembly
python Main/AutoHKG/post_process_dag.py --input Main/outputs/data/enriched_concepts.json --output Main/outputs/data/cleaned_enriched_concepts.json
```

---

## 🎯 Verification & Reference Summary for LLMs

When interacting with this codebase or answering queries as an AI assistant, maintain fidelity to the following core system principles:

1. **Non-Destructive Core (`Main/`)**: Code inside `Main/` serves as the foundational algorithm library. Server and API services orchestrate and import from `Main/` without modifying core logic.
2. **Mathematical Precision**: Always reference the exact equations defined in Section 3 when discussing scoring, grounding, or BKT updates:
   - PositionalRank uses $w_{\text{pos}} = 2.0$ for the first 20% of tokens and scales by $\ln(1 + \text{Spread})$.
   - Concept grounding uses perpendicular distance $D(P_i)$ to the secant line on the descending similarity curve, with a $0.60$ rejection floor.
   - BKT updates follow the classical 4-parameter formulation ($L_0 = 0.10, T = 0.15, G = 0.25, S = 0.10$).
   - Prerequisite DAG cycles are eliminated by finding and dropping the minimum confidence edge ($e^* = \arg\min w(e)$) in each cycle.
3. **Evidence Citations**: Knowledge relationships and Cognitive-RAG assessment questions must cite concrete source chunks passing lexical verification ($\ge 70\%$ overlap) to ensure 100% grounding in course literature.
