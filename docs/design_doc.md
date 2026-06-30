# Design Document: AtlasIQ (I2 - Document Q&A)

**Author:** Verdhan Yash  
**Segment:** Foundations of Applied Machine Learning  
**Problem Statement Code:** I2 (Document Q&A — RAG over a Focused Corpus)  

---

## 1. System Overview

AtlasIQ is a continuous knowledge platform that ingests documents via a REST Upload API (primary) or an optional folder watcher (enterprise/local), extracts structural text from multi-format documents, generates embeddings, stores them in a hybrid vector database, and generates evidence-backed answers with citation references and confidence scores.

### Target Objectives
- **Dual Ingestion Sources:** A REST Upload API as the primary entry point for production deployments, and an optional `watchdog`-based folder watcher for local/enterprise use. Both invoke the same shared ingestion pipeline.
- **Incremental Indexing:** SHA-256 content hashing with change detection — only new or modified documents are processed.
- **Explainable Retrieval:** Show dense vector, BM25 keyword, hybrid fusion (RRF), and reranked scores to the user via a retrieval inspector.
- **Provider Agnosticism:** Allow running Ollama (local), NVIDIA Build, or OpenAI through a unified LLM service interface.

---

## 2. System Architecture

```text
                                  ┌────────────────────────────┐
                                  │           User             │
                                  └─────────────┬──────────────┘
                                                │
                                       Natural Language Query
                                          or Document Upload
                                                │
                                                ▼
                           ┌─────────────────────────────────────┐
                           │      Streamlit User Interface       │
                           │ Upload • Search • Analytics • Eval  │
                           └─────────────────┬───────────────────┘
                                             │
                                             ▼
                            ┌──────────────────────────────────┐
                            │         FastAPI Backend          │
                            └───────┬───────────┬──────────────┘
                                    │           │
                     ┌──────────────┘           └──────────────┐
                     ▼                                         ▼
      Ingestion Sources                              Query Processing
             │                                               │
    ┌────────┴────────┐                           ┌──────────┴──────────┐
    │                 │                           │                     │
    ▼                 ▼                           ▼                     ▼
Upload API     Folder Watcher             Hybrid Retrieval        Query Logger
(Primary)      (Optional)                 (Dense + BM25)                │
    │                 │                           │                    ▼
    └────────┬────────┘                           ▼              PostgreSQL
             │                               Reranker            (Analytics)
             ▼                                    │
   Shared Ingestion Pipeline                      ▼
             │                             Prompt Builder
    ┌────────┴────────────┐                       │
    │                     │                       ▼
    ▼                     ▼              LLM Provider Interface
Validator          Change Detector                │
    │                     │                       ▼
    ▼                     │        Answer + Citations + Confidence
  Parser                  │
    │                     │
    ▼                     │
Chunking Engine           │
(Recursive Split)         │
    │                     │
    ▼                     │
Embedding Model           │
(Nomic Embed)             │
    │                     │
    ▼                     ▼
  Qdrant            Metadata Engine
  Vector DB         (SHA-256 Hash → PostgreSQL)
```

---

## 3. Data Flow

### Ingestion Flow

Documents enter the system through one of two sources, both of which invoke the **same shared ingestion pipeline**:

**Source A — Upload API (Primary):**
The user uploads a document via the REST API (`POST /ingest/upload`). The backend saves the file to `document_storage/`, then invokes the pipeline.

**Source B — Folder Watcher (Optional):**
The `watchdog`-based watcher monitors `watched_documents/` for file events. On detecting a new or changed file, it invokes the same pipeline.

**Shared Pipeline:**
1. **Validator:** Verifies file extension (.pdf, .docx, .md, .txt) and file size (<50MB).
2. **Change Detector:** Calculates SHA-256 hash. If hash matches existing document in PostgreSQL, ingestion is skipped. If modified, old vector coordinates are removed from Qdrant, and old chunks are removed from PostgreSQL.
3. **Parser:** IBM's `Docling` parses structural layout.
4. **Chunker:** Recursively splits document text into ~512 token chunks, preserving metadata (document ID, page ranges, chunk index).
5. **Embedder:** Generates dense vector representations (768 dimensions) via `nomic-embed-text-v1.5`.
6. **Storage:** Saves vector coordinates in Qdrant; logs metadata, hashes, and chunks in PostgreSQL.

### Retrieval Flow
1. **Query Input:** User inputs natural language query.
2. **Cache Lookup:** Normalized query is checked in the in-memory LRU cache. On cache hit, return answer immediately.
3. **Dense Search:** Embedding model computes query vector; Qdrant retrieves top-N matches.
4. **Keyword Search:** Pure-Python `rank_bm25` retrieves top-N matching chunks from the conformed chunk store in PostgreSQL.
5. **Hybrid Fusion:** Reciprocal Rank Fusion (RRF) scores and merges both candidate sets.
6. **Reranker:** `BGE Reranker` (cross-encoder) scores and selects the top-K chunks.
7. **Synthesis:** System constructs prompt, calls LLM, computes confidence scoring, logs analytics, and returns answer to UI.

---

## 4. Key Design Decisions

- **Upload API as Primary Entry Point:** Production-first design. The Upload API is the default ingestion path, deployable on any cloud. The folder watcher is an optional convenience for local/enterprise setups.
- **Single Shared Pipeline:** Both ingestion sources invoke the exact same pipeline (validate → detect → parse → chunk → embed → store). No duplicated logic.
- **No LangChain:** Hand-rolled retrieval, prompts, and provider abstraction to keep the codebase simple, fast, and free of library overhead.
- **Standardized Repository Pattern:** Decouples business logic (`services/`) from storage layers (`repositories/`) for clean testing.
- **Fail-Fast Startup Validation:** Checks connection health, prompt file presence, and necessary API keys before launching FastAPI.
