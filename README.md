# AtlasIQ

> **A continuous knowledge platform for intelligent document discovery, retrieval, and evidence-backed search.**

---

## 📋 Week 1 Submission Info

- **Student Name:** Yash Verdhan Parihar
- **Segment:** Foundations of Applied Machine Learning
- **Problem Statement Code:** I2 (Document Q&A — RAG over a Focused Corpus)
- **Status:** Milestone 0 (Foundation) Completed & Deployed locally
- **GitHub Repository:** [verdhanyash/AtlasIQ](https://github.com/verdhanyash/AtlasIQ)
- **Initial Design Doc:** [docs/design_doc.md](docs/design_doc.md)

---

## 🔍 Week 1 Submission Checklist

- [x] **Repo created and public:** [verdhanyash/AtlasIQ](https://github.com/verdhanyash/AtlasIQ)
- [x] **README.md configured** with project name, tagline, metadata, and learnings.
- [x] **Initial Design Doc (1 page):** Embedded/linked as [docs/design_doc.md](docs/design_doc.md).
- [x] **Tech stack table:** Completed with `Component | Choice | Why (one line)` (see below).
- [x] **Data layer working:** Verified via postgres/qdrant startup logs and health status checks (see below).
- [x] **At least 5 GitHub commits** on the main branch.
- [x] **A "What I learned" note** (3-5 bullet points) included in README.

---

## 📈 Week 1 Status One-Pager

### What's Done
- Scaffolded modular repository structure, configured Pydantic settings loading from `configs/default.yaml` with environment variable overrides.
- Implemented robust structured JSON logging, custom domain exception handlers, and fail-fast startup checks.
- Implemented async PostgreSQL client and database schema initialization (`schema.sql`).
- Implemented async Qdrant client with automatic collection creation (768-dim, cosine distance).
- Created multi-stage Docker environment running FastAPI, PostgreSQL, and Qdrant.
- Verified system status with a functional `/health` check endpoint.

### What's Stuck
- None. All Milestone 0 foundation tasks are complete and running successfully.

### 3 Goals for Next Week
1. Build `validator.py` and `parser.py` (IBM Docling integration) to convert raw files into structured Markdown.
2. Implement hash-based `change_detector.py` for incremental indexing to prevent duplicate processing.
3. Build the Upload API (`POST /ingest/upload`) as the primary ingestion entry point and orchestrate the full ingestion pipeline. Folder watcher is optional for local/enterprise use.

### One thing I'd like help from my mentor on
- Best practices for chunking strategies (handling tables and headings in Docling) and optimizing inference batch sizes when running sentence-transformers locally.

---

## 🧠 What I Learned This Week (Week 1)

1. **Pydantic Settings Precedence Gotcha**: Instantiating nested Pydantic settings using explicit constructor arguments (like `config_cls(**yaml_dict)`) overrides environmental variables in Pydantic v2. To preserve env var overrides, I had to clean the incoming YAML dictionary by checking if the matching environment variable (`ATLASIQ_<SECTION>__<KEY>`) was present in `os.environ` and filtering out those keys before instantiation.
2. **Container Healthcheck Limitations**: Minimal Docker images like `qdrant/qdrant` often strip utilities like `curl` or `wget`. Rather than introducing wrapper builds, a robust and zero-dependency alternative is to check `/proc/net/tcp` for the hexadecimal representation of the port (`18BD` for `6333`) in listening state (`0A`).
3. **Clean Architecture in FastAPI**: Enforcing strict inward-pointing dependencies (routers only handle routing, services handle business logic, repositories handle DB/Qdrant clients) makes the backend extremely modular and testable, avoiding the spaghetti imports common in simple RAG tutorials.
4. **Multi-Stage Docker Builds**: Separating the build stage (compiling packages, installing heavy ML libraries) from the runtime stage shrinks the final image footprint significantly and prevents unnecessary build utilities from cluttering the production container.

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
    │                     │
    ▼                     │
Embedding Model           │
    │                     │
    ▼                     ▼
  Qdrant            Metadata Engine
  Vector DB         (SHA-256 Hash → PostgreSQL)
```

---

# Project Structure

```text
atlasiq/

├── backend/
├── frontend/
├── ingestion/
├── retrieval/
├── evaluation/
├── analytics/
├── database/
├── tests/
├── docs/
│   ├── architecture.md
│   ├── srs.md
│   ├── api-design.md
│   ├── roadmap.md
│   └── decisions.md
├── docker-compose.yml
├── .env.example
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
| Milestone 2 — Retrieval Pipeline          | ⏳ Planned      |
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

## Latest Implementation

### Step 7A/7B — Ingestion Pipeline Orchestrator + Incremental Re-Indexing

Implemented the conductor that wires every ingestion stage into a single `async ingest(path)` flow: **Validator → Change Detector → Parser → Chunker → Embedder → PostgreSQL + Qdrant repositories**, including safe re-indexing of modified documents.

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
