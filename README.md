# AtlasIQ

> **A continuous knowledge platform for intelligent document discovery, retrieval, and evidence-backed search.**

---

## 📋 Project Info

- **Student Name:** Yash Verdhan Parihar
- **Segment:** Foundations of Applied Machine Learning
- **Problem Statement Code:** I2 (Document Q&A — RAG over a Focused Corpus)
- **Status:** Milestone 1 complete; Milestone 2 (Retrieval & Generation) in progress
- **GitHub Repository:** [verdhanyash/AtlasIQ](https://github.com/verdhanyash/AtlasIQ)

---

AtlasIQ is an enterprise-inspired knowledge platform designed to solve a common problem: **organizational knowledge is constantly growing, changing, and becoming difficult to search.**

Instead of acting as another document chatbot, AtlasIQ continuously builds and maintains a searchable knowledge layer from documents, allowing users to ask natural language questions and receive answers backed by relevant evidence.

---

## Why AtlasIQ?

Most document search systems require users to manually upload files and rely solely on vector search.

AtlasIQ focuses on the **entire knowledge lifecycle**:

* Continuous document ingestion
* Incremental indexing
* Intelligent retrieval
* Evidence-backed responses
* Knowledge analytics
* Evaluation and monitoring

The goal is to build a platform that can evolve into an enterprise knowledge system rather than a single-purpose chatbot.

---

# Core Capabilities

### Knowledge Ingestion

* Multi-format document support (PDF, DOCX, Markdown, TXT)
* Automatic document parsing
* Metadata extraction
* Continuous folder monitoring
* Incremental indexing

---

### Knowledge Retrieval

* Hybrid Retrieval (Semantic + Keyword)
* Context-aware search
* Intelligent reranking
* Metadata filtering
* Multi-document reasoning

---

### Knowledge Exploration

* Natural language search
* Source citations
* Confidence scoring
* Document comparison
* Explainable retrieval

---

### Platform Observability

* Query analytics
* Retrieval evaluation
* Structured logging
* Health monitoring

---

# System Architecture

> Legend: 🟢 implemented · 🟡 in progress · 🔴 planned · 🔵 storage

```mermaid
flowchart TB
    User([User])

    subgraph EntryPoints["Ingestion Sources"]
        UploadAPI["POST /ingest/upload"]
        FolderWatcher["Folder Watcher<br/>(watched_documents/)"]
    end

    subgraph QueryEntry["Query Interface"]
        StreamlitUI["Streamlit UI (M2-13)"]
        QueryAPI["POST /query (M2-12)"]
    end

    User -->|upload / drop| EntryPoints
    User -->|ask question| StreamlitUI --> QueryAPI

    subgraph Ingestion["Ingestion Pipeline — Milestone 1"]
        direction TB
        Validator["1 Validator"] --> Metadata["2 Metadata"]
        Metadata --> ChangeDetect["3 Change Detector<br/>(SHA-256)"]
        ChangeDetect -->|NEW / MODIFIED| Parser["4 Parser (Docling)"]
        ChangeDetect -->|UNCHANGED| Skip([skip])
        Parser --> Chunker["5 Chunker"] --> Embedder["6 Embedder<br/>(nomic-embed)"]
    end

    UploadAPI --> Validator
    FolderWatcher -->|debounced| Validator

    subgraph Storage["Storage Layer"]
        direction LR
        PostgreSQL[("PostgreSQL<br/>documents · chunks")]
        Qdrant[("Qdrant<br/>768-dim vectors")]
    end

    Embedder -->|text + metadata| PostgreSQL
    Embedder -->|vectors| Qdrant

    subgraph Retrieval["Retrieval &amp; Generation — Milestone 2"]
        direction TB
        QEmbed["Query Embed"] --> Dense["Dense Retriever"] & BM25["BM25 Retriever"]
        Dense --> Hybrid["Hybrid Retriever (RRF)"]
        BM25 --> Hybrid
        Hybrid --> Hydrate["Hydrate from PostgreSQL"]
        Hydrate --> Prompt["Prompt Builder (M2-6)"]
        Prompt --> LLM["LLM Provider<br/>Ollama / NVIDIA (M2-7)"]
        LLM --> Gen["Answer Generator (M2-8)"]
        Gen --> Cite["Citation Builder (M2-9)"]
        Cite --> Guard["Guardrails (M2-10)"]
    end

    QueryAPI --> QEmbed
    Dense -.->|vector search| Qdrant
    BM25 -.->|corpus at startup| PostgreSQL
    Hydrate -.->|get_chunks_by_ids| PostgreSQL
    Guard -->|answer + citations + confidence| StreamlitUI
    Guard -->|weak evidence| Refusal["'I don't know'"] --> StreamlitUI

    classDef done fill:#d4edda,stroke:#28a745,color:#000
    classDef wip fill:#fff3cd,stroke:#ffc107,color:#000
    classDef planned fill:#f8d7da,stroke:#dc3545,color:#000
    classDef store fill:#cce5ff,stroke:#004085,color:#000

    class Validator,Metadata,ChangeDetect,Parser,Chunker,Embedder,QEmbed,Dense,BM25,Hybrid done
    class Hydrate,Prompt,LLM,Gen,Cite,Guard,QueryAPI,StreamlitUI wip
    class Refusal planned
    class PostgreSQL,Qdrant store
```

---

# Project Structure

```text
AtlasIQ/
├── atlasiq/
│   ├── backend/
│   │   ├── api/            # FastAPI routes (health, ingestion, query)
│   │   ├── core/           # config, dependencies, exceptions, logging, startup
│   │   ├── domain/         # framework-independent records (DocumentRecord, ChunkRecord)
│   │   └── repositories/   # DocumentRepository (PostgreSQL), ChunkVectorRepository (Qdrant)
│   ├── ingestion/          # validator, parser, chunker, embedder, change_detector,
│   │                       #   metadata, pipeline, watcher
│   ├── retrieval/          # models, protocols, dense / BM25 / hybrid retrievers
│   ├── evaluation/         # evaluation framework (planned)
│   ├── analytics/          # query analytics (planned)
│   └── database/           # PostgresClient, QdrantVectorClient, schema.sql
├── tests/                  # offline unit + integration tests (mocked I/O)
├── scripts/                # dev tools (smoke_retrieval, run_watcher)
├── configs/                # default.yaml
├── prompts/                # qa / citation / system prompt templates
├── docker-compose.yml      # PostgreSQL + Qdrant + app
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

# Technology Stack

| Layer            | Technology                      | Why (one line) |
| ---------------- | ------------------------------- | -------------- |
| Backend          | FastAPI                         | Async, fast, supports automatic OpenAPI docs and dependency injection. |
| Frontend         | Streamlit                       | Lightweight UI engine for building search, analytics, and evaluation dashboards. |
| Database         | PostgreSQL                      | Stores structured document metadata, query logs, analytics, and evaluations. |
| Vector Database  | Qdrant                          | High-performance vector search engine supporting payload filters for dense retrieval. |
| Retrieval        | Hybrid Retrieval (Dense + BM25) | Combines semantic vector matching with term-based keyword search for high recall. |
| Reranking        | BGE Reranker                    | Re-scores candidate documents using cross-attention context for precise rank ordering. |
| Embeddings       | Nomic Embed                     | 768-dimensional open-source embedding model optimized for short/long text retrieval. |
| Document Parsing | Docling                         | Advanced layout-aware document parser preserving structure (tables, headings). |
| Containerization | Docker                          | Multi-container orchestration to isolate the API, PostgreSQL, and Qdrant layers. |
| CI/CD            | GitHub Actions                  | Automatic formatting (Ruff), type verification (Mypy), and test runs (Pytest). |
| Deployment       | Render                          | Fully Docker-based cloud container hosting provider. |

---

## 💾 Data Layer Verification (Working Data Layer)

To verify that the database data layers (PostgreSQL and Qdrant) are correctly set up and connected to the FastAPI application, the startup pipeline validates connectivity, executes the schema tables creation script, ensures Qdrant collection presence, and exposes a `/health` check.

### Service Containers Check
```bash
# Verify all container services are up and healthy
docker compose ps
```

**Output:**
```text
NAME                 IMAGE               COMMAND                  SERVICE             CREATED             STATUS              PORTS
atlasiq-postgres-1   postgres:16-alpine  "docker-entrypoint.s…"   postgres            1 hour ago          Up 1 hour (healthy) 0.0.0.0:5432->5432/tcp
atlasiq-qdrant-1     qdrant/qdrant:v1.11.0 "./entrypoint.sh"       qdrant              1 hour ago          Up 1 hour (healthy) 0.0.0.0:6333->6333/tcp
atlasiq-web-1        atlasiq-app         "uvicorn atlasiq.bac…"   web                 1 hour ago          Up 1 hour           0.0.0.0:8000->8000/tcp
```

### Health Check Endpoint Response (`GET /health`)
Querying the API gateway status reports the active connection health of the underlying databases:
```bash
curl http://localhost:8000/health
```

**Response JSON:**
```json
{
  "status": "healthy",
  "checks": {
    "fastapi": true,
    "postgresql": true,
    "qdrant": true,
    "llm_provider": "ollama",
    "llm_model": "gemma3:4b",
    "config_valid": true
  },
  "timestamp": "2026-06-28T01:00:00.000000+00:00"
}
```

---
# 🚧 Development Progress

| Milestone                                 | Status         |
| ----------------------------------------- | -------------- |
| Milestone 0 — Foundation                  | ✅ Completed    |
| Milestone 1 — Document Ingestion Pipeline | ✅ Completed    |
| Milestone 2 — Retrieval & Generation      | 🚧 In Progress |
| Milestone 3 — Generation Pipeline         | ⏳ Planned      |
| Milestone 4 — Evaluation & Analytics      | ⏳ Planned      |

---

## ✅ Milestone 0 — Foundation

Completed infrastructure includes:

* Clean modular project architecture
* FastAPI backend
* Configuration management (YAML + Environment Variables)
* Async PostgreSQL client
* Qdrant vector database integration
* Docker & Docker Compose
* Health check API
* Structured logging
* Database initialization
* CI/CD foundation

---

## 🚧 Milestone 1 — Document Ingestion Pipeline

### Completed

* ✅ Step 1: Document Validator
* ✅ Step 2: Document Parser (IBM Docling Integration)
* ✅ Step 3: Metadata Extraction & Change Detection
* ✅ Step 4: Text Chunker (Recursive Character Splitting)
* ✅ Step 5: Document Embedder (Lazy-Loaded sentence-transformers)
* ✅ Step 6A: Domain Records (framework-independent dataclasses)
* ✅ Step 6B: PostgreSQL Repository (documents + chunks)
* ✅ Step 6C: Qdrant Chunk Vector Repository
* ✅ Step 6D: Database Clients (reviewed — documented no-op)
* ✅ Step 7A: Ingestion Pipeline Orchestrator
* ✅ Step 7B: Incremental Update Logic (modified-document re-indexing)
* ✅ Step 8A: Upload API (`POST /ingest/upload`)
* ✅ Step 8B: Status API (`GET /ingest/status`, `GET /ingest/documents`)
* ✅ Step 8C: Optional Folder Watcher
* ✅ Step 9: End-to-End Integration

### Remaining

* None — Milestone 1 complete.

---

## 🚧 Milestone 2 — Retrieval & Generation Pipeline (AskMyBook)

### Completed

* ✅ M2-1: Retrieval Models & Repository Reads (`ScoredChunkRef`, `RetrievedChunk`, chunk hydration reads)
* ✅ M2-2: Query Embedding (reuses the existing embedder's `search_query:` path)
* ✅ M2-3: Dense Retriever (semantic search over Qdrant)
* ✅ M2-4: BM25 Sparse Retriever (in-memory lexical index)
* ✅ M2-5: Hybrid Retriever (Reciprocal Rank Fusion)

### Remaining

* ⏳ M2-6: Prompt Builder
* ⏳ M2-7: LLM Provider (Ollama + NVIDIA)
* ⏳ M2-8: Answer Generator
* ⏳ M2-9: Citation Builder
* ⏳ M2-10: Guardrails
* ⏳ M2-11: Query Pipeline
* ⏳ M2-12: Query API
* ⏳ M2-13: Streamlit UI
* ⏳ M2-14: Evaluation Framework
* ⏳ M2-15: Compare Two Documents

## Latest Implementation

### M2-5 — Hybrid Retriever (Reciprocal Rank Fusion)

Fuses the dense (semantic) and BM25 (lexical) retrievers into one ranked list, completing the retrieval stack (M2-1 → M2-5).

**Highlights**

* **Reciprocal Rank Fusion** combines results by rank position, not raw score — so incomparable scales (cosine similarity vs BM25) merge fairly: `rrf_score = Σ 1/(rrf_k + rank)`.
* Depends on a **`Retriever` protocol**, not concrete classes (Dependency Inversion). Accepts a `Sequence[Retriever]`, so future retrievers (reranking, ColBERT/SPLADE, ...) plug in without modifying the fusion engine.
* Fusion isolated in a dedicated `_fuse_rrf` helper; deterministic ordering by `(-rrf_score, document_id, chunk_index)`; deduplicates chunks across retrievers.
* Each retriever keeps its own candidate pool; the hybrid only fuses and applies the final `top_k`. Fail-fast on an empty retriever list.
* 11 offline unit tests (exact RRF scoring, dedup, overlap boosting, deterministic tie-breaks, N-retriever generalisation), plus the `scripts/smoke_retrieval.py` dev tool now printing DENSE / BM25 / HYBRID side by side.

**Status**

✅ Completed and tested — full suite: **241 tests passing**, `ruff` and `mypy --strict` clean.

**Verified end-to-end (live):** a real 813 KB PDF financial report was ingested via the folder-watcher drop → parse (Docling, OCR disabled) → chunk (470) → embed (nomic-embed-text-v1.5) → store (PostgreSQL + Qdrant), after which retrieval returned relevant, correctly-scored chunks from the live datastores.

---

### Milestone 1 recap — Ingestion Pipeline Orchestrator + Incremental Re-Indexing

The conductor wires every ingestion stage into a single `async ingest(path)` flow: **Validator → Change Detector → Parser → Chunker → Embedder → PostgreSQL + Qdrant repositories**, including safe re-indexing of modified documents.

**Highlights**

* Pure orchestration — no parsing/embedding/SQL logic of its own; all seven collaborators are constructor-injected.
* Database-backed change detection (NEW / MODIFIED / UNCHANGED) via a deterministic, path-derived document id — survives process restarts (no in-memory registry).
* Deterministic chunk ids shared as the PostgreSQL ↔ Qdrant join key (idempotent upserts).
* **Incremental updates:** a modified document is re-indexed with a mandatory delete-then-insert across both stores (no duplicate or orphaned chunks), keeping the document row and its `created_at` stable.
* Lifecycle contract: `PROCESSING` → `COMPLETED` (with final `word_count`), or `FAILED` on any error (then re-raised).
* 12 unit tests, fully mocked — no database, no network, no models.

**Supporting repository layer (Step 6A–6D)**

* Framework-independent domain records (`DocumentRecord`, `ChunkRecord`).
* `DocumentRepository` — the only home for raw SQL over `documents`/`chunks` (bound params, domain-exception wrapping).
* `ChunkVectorRepository` — ingestion-write-only wrapper over Qdrant (payload shaping + filtered deletes).

**Engineering Principles**

* Dependency Injection
* Separation of Concerns
* Single Responsibility
* Production-oriented modular design

**Status**

✅ Completed and tested — full suite: **190 tests passing**, `ruff` and `mypy --strict` clean.

### Known Limitations (V1)

* **Unauthenticated upload**: `POST /ingest/upload` has no auth layer — authentication is out of V1 scope per PROJECT_SCOPE.
* **Qdrant `vector_size` / embedding dimension**: these are independent config values; swapping the embedding model requires updating `qdrant.vector_size` in config (DL-026).


# Development Roadmap


## Version 1 — Internship Release

* Multi-format document ingestion
* Continuous folder monitoring
* Incremental indexing
* Hybrid retrieval
* Natural language search
* Source citations
* Confidence scoring
* Document comparison
* Analytics dashboard
* Evaluation dashboard
* Docker deployment

---

## Future Roadmap

* Google Drive connector
* GitHub repository indexing
* Website ingestion
* Authentication
* Knowledge graph
* Enterprise connectors
* Cloud-native deployment
* Advanced retrieval optimization

---

# Design Principles

AtlasIQ is built around four engineering principles:

* **Knowledge should stay up to date.**
* **Answers should be backed by evidence.**
* **Search should understand both keywords and meaning.**
* **The system should be modular and easy to extend.**

---

# Current Status

🚧 Active Development

AtlasIQ is currently being developed as part of a software engineering and machine learning internship, with a focus on building a production-inspired knowledge platform using modern information retrieval techniques.

---

# License

MIT License
