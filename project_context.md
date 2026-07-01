# AtlasIQ — Project Context

> **Purpose of this file:** A single source of truth for any new contributor, mentor, or AI session to understand the project's architecture, what has been built, how it was built, and what comes next — without re-reading the entire conversation history.

---

## Current Status

**Completed**
- ✅ Milestone 0 — Foundation & Infrastructure
- ✅ Step 1: Document Validator
- ✅ Step 2: Document Parser
- ✅ Step 3: Metadata Extractor & Change Detector
- ✅ Step 4: Text Chunker

**Current branch**
- `main`

**Tests**
- 82/82 passing (0.77s)

**Next task**
- Step 5: Embedder (`atlasiq/ingestion/embedder.py`) using `nomic-embed-text-v1.5` (768 dimensions)

> [!IMPORTANT]
> Do not reimplement completed modules unless explicitly requested.

---

## 1. What Is AtlasIQ?

AtlasIQ is an **Enterprise Knowledge Platform** built for the I2 problem statement (Document Q&A — RAG over a Focused Corpus). It continuously ingests documents, generates embeddings, stores them in a hybrid vector database, and produces evidence-backed answers with citation references and confidence scores.

**Author:** Verdhan Yash
**Segment:** Foundations of Applied Machine Learning (B.Tech CSE-AIDE, 2nd Year)
**Duration:** 22 June 2026 → 26 July 2026 (5 weeks)

---

## 2. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend API | FastAPI + Uvicorn | Async-native, auto-generated OpenAPI docs |
| Configuration | Pydantic Settings + YAML | Type-safe config with env var overrides |
| Relational DB | PostgreSQL 16 (asyncpg) | Document metadata, chunk logs, analytics |
| Vector DB | Qdrant | Purpose-built for dense vector search |
| Document Parsing | IBM Docling | Structural layout extraction from PDF/DOCX |
| Embeddings | `nomic-embed-text-v1.5` (768d) | Open-weight, high quality, runs locally |
| Reranker | BGE Reranker (cross-encoder) | Cross-encoder precision for final ranking |
| BM25 | `rank-bm25` | Pure-Python keyword search |
| LLM Providers | Ollama (default), NVIDIA Build, OpenAI | Provider-agnostic via unified interface |
| Frontend | Streamlit | Rapid prototyping for Q&A and analytics UI |
| Folder Watcher | `watchdog` | Optional local/enterprise file monitoring |
| Containerization | Docker + Docker Compose | Reproducible deployments |
| Python | 3.12+ | Latest stable; type hints, dataclasses |
| Linting | Ruff + MyPy (strict) | Fast linting + strict static typing |
| Testing | pytest | Simple, fast, well-supported |

**Explicitly avoided:** LangChain, LlamaIndex, or any heavy abstraction framework.

---

## 3. Architecture Overview

```
                              ┌────────────────────────────┐
                              │           User             │
                              └─────────────┬──────────────┘
                                            │
                                   Query or Document Upload
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
    ┌────┴────┐                                ┌─────────┴─────────┐
    │         │                                │                   │
    ▼         ▼                                ▼                   ▼
Upload API  Folder Watcher            Hybrid Retrieval        Query Logger
(Primary)   (Optional)               (Dense + BM25)               │
    │         │                                │                   ▼
    └────┬────┘                                ▼             PostgreSQL
         │                                Reranker           (Analytics)
         ▼                                     │
Shared Ingestion Pipeline                      ▼
         │                              Prompt Builder
    ┌────┴──────────┐                          │
    │               │                          ▼
    ▼               ▼                 LLM Provider Interface
Validator    Change Detector                   │
    │               │                          ▼
    ▼               │           Answer + Citations + Confidence
  Parser            │
    │               │
    ▼               │
Chunking Engine     │
    │               │
    ▼               │
Embedding Model     │
    │               │
    ▼               ▼
  Qdrant      Metadata Engine
  Vector DB   (SHA-256 Hash → PostgreSQL)
```

### Ingestion Architecture Decision

The **Upload API** (`POST /ingest/upload`) is the primary ingestion entry point. Files are saved to `document_storage/`. The **folder watcher** monitors `watched_documents/` as an optional enterprise/local convenience. Both sources invoke the **exact same shared ingestion pipeline** — no duplicated logic.

---

## 4. Folder Structure

```
AtlasIQ/
├── atlasiq/
│   ├── backend/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings (IngestionConfig, ChunkingConfig, etc.)
│   │   │   ├── exceptions.py # Custom exception hierarchy (AtlasIQError base)
│   │   │   ├── logging.py    # JSON structured logging setup
│   │   │   └── startup.py    # Fail-fast health checks at boot
│   │   └── main.py           # FastAPI app entry point
│   ├── ingestion/
│   │   ├── validator.py      # ✅ Step 1 — Format & size gatekeeper
│   │   ├── parser.py         # ✅ Step 2 — Markdown extraction (Docling + direct read)
│   │   ├── metadata.py       # ✅ Step 3a — DocumentMetadata dataclass
│   │   ├── change_detector.py# ✅ Step 3b — SHA-256 hashing & change detection
│   │   ├── chunker.py        # ✅ Step 4 — Recursive text splitting with overlap
│   │   ├── embedder.py       # ⬜ Step 5 — (next)
│   │   ├── pipeline.py       # ⬜ Step 7 — Orchestrator
│   │   └── watcher.py        # ⬜ Step 8 — watchdog-based folder monitor
│   ├── database/
│   │   ├── postgres_client.py# PostgreSQL connection pool & schema init
│   │   └── qdrant_client.py  # Qdrant collection management
│   ├── retrieval/            # ⬜ Milestone 2 — Hybrid search & reranking
│   └── analytics/            # ⬜ Milestone 3 — Query analytics
├── tests/
│   ├── test_validator.py     # 14 tests
│   ├── test_parser.py        # 14 tests
│   ├── test_metadata.py      # 12 tests
│   ├── test_change_detector.py # 17 tests
│   └── test_chunker.py       # 25 tests
├── configs/
│   └── default.yaml          # Default configuration values
├── docs/
│   ├── design_doc.md         # System design document
│   ├── MILESTONES.md         # Course deliverables spec
│   ├── ENGINEERING_GUIDELINES.md # Coding standards & rules
│   └── ...                   # Other documentation
├── prompts/
│   └── citation_prompt.txt   # LLM prompt templates
├── docker-compose.yml        # PostgreSQL + Qdrant + App
├── Dockerfile                # FastAPI container image
├── pyproject.toml            # Dependencies, linting, testing config
└── CODE_REVIEW_CHECKLIST.md  # 10-section quality audit checklist
```

---

## 5. Completed Modules — Detail

### Milestone 0: Foundation & Infrastructure

| What | Detail |
|------|--------|
| Config system | `config.py` — Pydantic Settings parsing `ATLASIQ_*` env vars merged over `configs/default.yaml` |
| Exception hierarchy | `exceptions.py` — `AtlasIQError` base with domain-specific subclasses |
| Docker stack | FastAPI (`:8000`), PostgreSQL (`:5432`), Qdrant (`:6333`) |
| Startup checks | Connection health, prompt validation, schema init — fail-fast before serving |
| Qdrant healthcheck | Zero-dependency: inspects `/proc/net/tcp` for port `6333` in listen mode |

### Step 1: Document Validator (`validator.py`)

- Checks file existence, supported extension (`.pdf`, `.docx`, `.md`, `.txt`), and size limit.
- All thresholds from `IngestionConfig` — no hardcoded values.
- Case-insensitive extension matching.
- Raises `DocumentValidationError` on failure.
- **14 tests** covering valid files, missing files, directories, unsupported formats, oversized files, and custom config.

### Step 2: Document Parser (`parser.py`)

- Plain-text files (`.md`, `.txt`) → direct `Path.read_text()`.
- Rich formats (`.pdf`, `.docx`) → IBM Docling `DocumentConverter.convert()` → Markdown export.
- **Lazy initialization**: Docling is imported and loaded only on first rich-format encounter.
- Empty results rejected with `DocumentParsingError`.
- **14 tests** — all Docling interactions mocked via `MagicMock` (no ML model downloads needed locally).

### Step 3a: Metadata Extractor (`metadata.py`)

- Frozen dataclass `DocumentMetadata` with fields: `file_name`, `file_path`, `file_extension`, `file_size_bytes`, `ingested_at`.
- Pure metadata extraction — does **not** compute hashes, validate, or parse.
- Raises `DocumentNotFoundError` if file doesn't exist.
- **12 tests** covering all fields, edge cases, and error paths.

### Step 3b: Change Detector (`change_detector.py`)

- Computes SHA-256 hash of file bytes in fixed **64 KB chunks** (memory-safe for large files).
- Compares hash against an in-memory registry (`dict[str, str]` mapping resolved path → hash).
- Returns `ChangeStatus` enum: `NEW`, `MODIFIED`, or `UNCHANGED`.
- Public API (`check()` / `register()`) designed to swap to PostgreSQL without interface changes.
- **17 tests** covering all change states, hash determinism, multi-file tracking, and re-registration.

### Step 4: Text Chunker (`chunker.py`)

- Recursive character splitting using separator hierarchy: `\n\n` → `\n` → `. ` → ` ` → characters.
- Falls back to character-level splits when no separator can break text below `chunk_size`.
- Merges small pieces into overlapping chunks using configurable `chunk_overlap`.
- All parameters from `ChunkingConfig` (default: `chunk_size=512`, `chunk_overlap=50`).
- Raises `ChunkingError` for empty text or invalid config.
- **25 tests** covering recursive splitting, overlap merging, boundary conditions, unicode, and config validation.

---

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No LangChain/LlamaIndex** | Hand-rolled pipeline keeps codebase simple, fast, and fully understood |
| **Lazy Docling loading** | Avoids ML model downloads when processing plain-text only |
| **Memory-safe hashing** | 64 KB chunk reads prevent loading 50 MB files into memory at once |
| **In-memory change registry (V1)** | Simple dict; will swap to PostgreSQL queries without API changes |
| **Recursive splitter** | Guarantees no chunk exceeds size limit while preserving semantic boundaries |
| **Upload API as primary** | Production-first — deployable anywhere; watcher is optional for local use |
| **Frozen dataclass for metadata** | Immutability prevents accidental mutation after extraction |
| **Domain exception hierarchy** | All errors inherit from `AtlasIQError` — single catch point for API error handlers |
| **Fail-fast startup** | Validates databases, prompts, and config before accepting requests |

---

## 7. Conventions & Constraints

### Coding Standards
- **Python 3.12+** with strict type hints on every function
- **Docstrings** (Google style) on every public class and method
- **Logging** via `logging.getLogger(__name__)` — structured JSON in production
- **Dependency injection** via config objects — no hardcoded values
- **Single responsibility** — one module, one concern
- **No files over ~400 lines**

### Git Conventions
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Never commit broken code
- All tests must pass before committing

### Testing Standards
- Every module has comprehensive unit tests
- Use `MagicMock` for heavy external dependencies (Docling, databases)
- Tests run locally without Docker or network access
- Reviewed against `CODE_REVIEW_CHECKLIST.md` (10 sections) before merge

### V1 Boundaries
- No LangChain, LlamaIndex, or heavy abstraction frameworks
- No OCR, web scrapers, or agent logic
- No unnecessary packages

---

## 8. Infrastructure

| Service | Container | Port | Notes |
|---------|-----------|------|-------|
| FastAPI Backend | `atlasiq-app` | `8000` | Main application |
| PostgreSQL 16 | `atlasiq-postgres` | `5432` | User: `atlasiq`, DB: `atlasiq` |
| Qdrant | `atlasiq-qdrant` | `6333` / `6334` | Collection: `atlasiq_chunks` |
| Ollama (host) | — | `11434` | Default LLM provider, runs on host |

**Config precedence:** Environment variables (`ATLASIQ_*`) override `configs/default.yaml`.

---

## 9. Git History (Chronological)

```
735ac90 Initial commit
f9c57f8 Update README.md
9ffe589 feat: implement milestone 0 foundation structure and config
8fdd0f6 docs: update README with Week 1 details and add design document
2d1ba45 docs: align README with the full Week 1 deliverables specification
363037d Update student name in README.md
e80c3e2 feat: implement document validator and unit tests
ccb9ef5 feat: implement document parser and unit tests
b65415c Update README.md
7d77612 feat: implement metadata extraction and change detector with pipeline updates
f57b776 feat: implement document chunker and unit tests
```

---

## 10. Pipeline Flow (Where We Are)

```
📄 File on Disk
     │
     ▼
✅ Step 1: Validator           — checks format & size
     │
     ▼
✅ Step 3: Change Detector     — computes SHA-256, decides NEW/MODIFIED/UNCHANGED
     │
     ├── UNCHANGED → skip
     │
     ├── NEW or MODIFIED ──▼
     │
✅ Step 2: Parser              — extracts Markdown text
     │
     ▼
✅ Step 4: Chunker             — recursive split with overlap
     │
     ▼
⬜ Step 5: Embedder            — nomic-embed-text-v1.5 (768d)      ← NEXT
     │
     ▼
⬜ Step 6: Repositories        — PostgreSQL + Qdrant storage
     │
     ▼
⬜ Step 7: Pipeline            — orchestrates all stages
     │
     ▼
⬜ Step 8: Upload API          — FastAPI endpoints + optional watcher
```

---

## 11. Remaining Milestone 1 Steps

| Step | Module | Description |
|------|--------|-------------|
| 5 | `ingestion/embedder.py` | Batch embedding with `nomic-embed-text-v1.5` via `sentence-transformers` |
| 6 | `database/repositories/` | Repository layer for document metadata, chunk text, and embeddings |
| 7 | `ingestion/pipeline.py` | Orchestrator: Validate → Detect → Parse → Chunk → Embed → Store |
| 8 | `backend/api/` + `watcher.py` | Upload endpoints (`/ingest/upload`, `/ingest/status`), optional folder watcher |

---

## 12. Exception Hierarchy

```
AtlasIQError (base)
├── ConfigurationError
├── StartupError
├── DocumentValidationError
├── DocumentParsingError
├── ChunkingError
├── DocumentNotFoundError
├── RetrievalError
├── LLMProviderError
├── PromptTemplateError
├── DatabaseConnectionError
└── DatabaseQueryError
```

---

## 13. Running the Project

```bash
# Run tests locally (no Docker needed)
python -m pytest tests/ -v

# Start the full stack
docker-compose up

# Health check
curl http://localhost:8000/health
```

---

*Last updated: 30 June 2026*
