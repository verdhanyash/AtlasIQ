# Design Document: AtlasIQ (I2 - Document Q&A)

**Author:** Verdhan Yash  
**Segment:** Foundations of Applied Machine Learning  
**Problem Statement Code:** I2 (Document Q&A — RAG over a Focused Corpus)  

---

## 1. System Overview

AtlasIQ is a continuous knowledge platform that ingestion-monitors a designated folder, extracts structural text from multi-format documents, generates embeddings, stores them in a hybrid vector database, and generates evidence-backed answers with citation references and confidence scores.

### Target Objectives
- **Continuous Ingestion:** Watch folders, run incremental change detection using SHA-256 hashes, and re-index only changed/new documents.
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
           Ingestion Pipeline                        Query Processing
                     │                                         │
       ┌─────────────┴──────────────┐               ┌──────────┴──────────┐
       │                            │               │                     │
       ▼                            ▼               ▼                     ▼
Document Parser             Metadata Engine   Hybrid Retrieval      Query Logger
(Docling)                   (SHA-256 Hash)     (Dense + BM25)              │
       │                            │               │                    ▼
       ▼                            │               ▼              PostgreSQL
Chunking Engine                    │          Reranker             (Analytics)
(Recursive Split)                   │               │
       │                            │               ▼
       ▼                            │        Prompt Builder
Embedding Model                     │               │
(Nomic Embed)                       │               ▼
       │                            └────────► Prompt Builder
       ▼                                            │
    Qdrant Vector DB                                ▼
                                          LLM Provider Interface
                                                    │
                                                    ▼
                                    Answer + Citations + Confidence
```

---

## 3. Data Flow

### Ingestion Flow
1. **Watcher:** `watchdog` notices file events in the monitored folder.
2. **Validator:** Verifies file extension (.pdf, .docx, .md, .txt) and file size (<50MB).
3. **Change Detector:** Calculates SHA-256 hash. If hash matches existing document in PostgreSQL, ingestion is skipped. If modified, old vector coordinates are removed from Qdrant, and old chunks are removed from PostgreSQL.
4. **Parser:** IBM's `Docling` parses structural layout.
5. **Chunker:** Recursively splits document text into ~512 token chunks, preserving metadata (document ID, page ranges, chunk index).
6. **Embedder:** Generates dense vector representations (768 dimensions) via `nomic-embed-text-v1.5`.
7. **Storage:** Saves vector coordinates in Qdrant; logs metadata, hashes, and chunks in PostgreSQL.

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

- **No LangChain:** Hand-rolled retrieval, prompts, and provider abstraction to keep the codebase simple, fast, and free of library overhead.
- **Standardized Repository Pattern:** Decouples business logic (`services/`) from storage layers (`repositories/`) for clean testing.
- **Fail-Fast Startup Validation:** Checks connection health, prompt file presence, and necessary API keys before launching FastAPI.
