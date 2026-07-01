# AtlasIQ — Decision Log

Every significant architectural, engineering, or implementation decision is recorded here in chronological order. Each entry explains **what** was decided, **why**, and **what the consequences are**.

> **Rule:** Update this file whenever a non-trivial decision is made. Future sessions should read this before proposing changes.

---

## DL-001: No LangChain or LlamaIndex

**Date:** 27 June 2026
**Phase:** Milestone 0 — Project Setup
**Status:** Active

### Context
RAG projects commonly default to LangChain or LlamaIndex for orchestration — they provide abstractions for chains, retrievers, vector stores, and prompt templates. Using one would speed up initial development.

### Decision
Build all pipeline stages, retrieval logic, and prompt construction by hand. Do not use LangChain, LlamaIndex, or any similar orchestration framework.

### Rationale
- The project must demonstrate **software engineering skill**, not framework usage.
- LangChain adds heavy abstractions and hides the retrieval mechanics that are the core product.
- Hand-rolled code is easier to debug, profile, and extend than framework internals.
- The V1 scope is small enough that framework overhead isn't justified.

### Consequences
- Every pipeline stage must be written from scratch — more code, but fully understood.
- Integration between stages is explicit (function calls, not magic chains).
- Easier to swap individual components (e.g., embedding model) without framework lock-in.

---

## DL-002: Pydantic Settings with YAML Base Configuration

**Date:** 27 June 2026
**Phase:** Milestone 0 — Config System
**Status:** Active

### Context
The application needs configuration for database connections, LLM providers, ingestion parameters, chunking parameters, and more. Values must differ between local development, Docker, and production.

### Decision
Use `pydantic-settings` with a layered config approach:
1. `configs/default.yaml` provides base defaults.
2. Environment variables prefixed with `ATLASIQ_` override any YAML value.
3. Nested config objects (`IngestionConfig`, `ChunkingConfig`, `DatabaseConfig`, etc.) are accessed through a root `Settings` class.

### Rationale
- Pydantic gives type validation, casting, and documentation for free.
- YAML is human-readable for defaults; env vars are standard for deployment.
- Nested config objects prevent a flat namespace collision (e.g., `database.host` vs `qdrant.host`).

### Consequences
- Config changes for Docker are done via `docker-compose.yml` environment section.
- No hardcoded values anywhere in implementation code.
- Config parsing is tested implicitly via every module that depends on it.

---

## DL-003: Qdrant Healthcheck via /proc/net/tcp

**Date:** 27 June 2026
**Phase:** Milestone 0 — Docker Compose
**Status:** Active

### Context
Docker Compose requires a healthcheck for dependent service ordering. The official Qdrant image is minimal — it contains no `curl`, `wget`, or any HTTP client binary.

### Decision
Use `grep -q ':18BD' /proc/net/tcp` as the Qdrant healthcheck. `18BD` is the hex representation of port `6333`.

### Rationale
- Zero external dependencies — no custom image, no extra binary.
- Checks that Qdrant is actually listening on the correct port, not just that the container is running.
- Simpler than building a custom Qdrant image with curl installed.

### Consequences
- Linux-specific; works in Docker containers but not on macOS/Windows directly (irrelevant since Qdrant always runs in a container).
- If Qdrant ever changes its default port, the hex value must be updated.

---

## DL-004: Fail-Fast Startup Validation

**Date:** 27 June 2026
**Phase:** Milestone 0 — Application Lifecycle
**Status:** Active

### Context
The backend depends on PostgreSQL, Qdrant, prompt templates, and valid configuration. If any is missing, the application would produce confusing runtime errors on the first user request.

### Decision
Run all dependency checks (database connections, vector store health, prompt file existence, config validation) during FastAPI's startup lifespan — before accepting any requests. If any check fails, raise `StartupError` and abort.

### Rationale
- Fail-fast reveals deployment mistakes immediately (wrong DB password, missing prompt file, Qdrant unreachable).
- Better than silently starting and failing on the first query 5 minutes later.
- Matches production best practices.

### Consequences
- `startup.py` is a dedicated module with explicit health checks.
- The app takes a few hundred milliseconds longer to start (connection checks), but this is negligible.
- Adds a clear startup log trail showing exactly which checks passed.

---

## DL-005: Upload API as Primary Ingestion Entry Point

**Date:** 30 June 2026
**Phase:** Architecture Refinement (pre–Step 3)
**Status:** Active

### Context
The original architecture treated the folder watcher (`watched_documents/`) as the primary document ingestion path. However, a folder watcher is a local-only mechanism — it doesn't work in cloud deployments, serverless environments, or multi-user production setups.

### Decision
Restructure the ingestion architecture:
- **Upload API** (`POST /ingest/upload`) becomes the **primary** ingestion entry point. Files are saved to `document_storage/`.
- **Folder Watcher** (`watched_documents/`) is demoted to an **optional** ingestion source for local/enterprise convenience.
- Both sources invoke the **exact same shared ingestion pipeline** — no duplicated logic.

### Rationale
- A REST API is universally deployable: cloud, on-prem, Kubernetes, serverless.
- A folder watcher requires the application and filesystem to be co-located — fragile assumption.
- Making the watcher optional means it can be disabled entirely in production with zero impact.
- Sharing one pipeline guarantees identical behavior regardless of entry point.

### Changes Made
- Updated `docs/design_doc.md` — architecture diagram and data flow descriptions.
- Updated `docs/PROJECT_CONTEXT.md` — ingestion pipeline section.
- Updated `docs/WORKFLOW.md` — watcher references demoted.
- Updated `docs/KNOWN_CHALLENGES.md` — watcher-specific challenges reframed.
- Added `document_storage/` to `.gitignore`.
- Docker Compose volumes now mount both `document_storage/` and `watched_documents/`.

### Consequences
- All future pipeline implementation flows through a single code path.
- Watcher becomes a thin adapter that calls the pipeline on file events — not a separate pipeline.
- Frontend upload and watcher are interchangeable ingestion triggers.

---

## DL-006: Separate metadata.py from change_detector.py

**Date:** 30 June 2026
**Phase:** Milestone 1, Step 3
**Status:** Active

### Context
The initial implementation plan combined metadata extraction and hash computation into a single `metadata.py` module with a `content_hash` field on the `DocumentMetadata` dataclass.

### Decision
Split into two strictly independent modules:
- **`metadata.py`** — pure file-system metadata only (`file_name`, `file_path`, `file_extension`, `file_size_bytes`, `ingested_at`). Does **not** compute hashes.
- **`change_detector.py`** — owns SHA-256 computation, hash registry, and `ChangeStatus` enum.

### Rationale
- **Single Responsibility Principle**: metadata extraction and change detection are conceptually different operations.
- Metadata is always needed (for logging, citations, display). Change detection is conditional (only matters if you're checking for duplicates).
- Separating them means either can evolve independently — e.g., metadata might later pull creation dates from file headers, while change detection might switch to xxHash.

### Consequences
- Two modules, two test files — slightly more files, but much cleaner boundaries.
- The pipeline orchestrator calls them independently and can use metadata even when change detection is skipped.

---

## DL-007: In-Memory Hash Registry (V1) with Database-Ready Interface

**Date:** 30 June 2026
**Phase:** Milestone 1, Step 3
**Status:** Active (will evolve in Step 6)

### Context
The `ChangeDetector` needs to remember which files it has already ingested and their content hashes. In production, this should be PostgreSQL. But the database repository layer isn't built yet (that's Step 6).

### Decision
Use a simple `dict[str, str]` (resolved file path → SHA-256 hash) as the V1 backing store. Design the public API (`check()` and `register()`) so that swapping to PostgreSQL later changes only the internal implementation — not the interface.

### Rationale
- Allows building and testing the change detection logic now, without waiting for database infrastructure.
- The public API is intentionally database-agnostic: `check(file_path) → ChangeStatus` and `register(file_path) → str`.
- When `repositories/` is implemented, we inject a repository object instead of the internal dict.

### Consequences
- In V1, the hash registry resets on every application restart (acceptable for development).
- No database dependency for unit tests — fast, isolated testing.
- The migration to PostgreSQL will be a minimal internal change.

---

## DL-008: Memory-Safe SHA-256 Hashing (64 KB Chunks)

**Date:** 30 June 2026
**Phase:** Milestone 1, Step 3
**Status:** Active

### Context
The validator allows files up to 50 MB. Reading an entire 50 MB file into memory just to hash it would spike memory usage unnecessarily, especially if multiple files are being ingested concurrently.

### Decision
Read files in fixed **64 KB chunks** (`_HASH_CHUNK_SIZE = 65_536`) and feed each chunk to `hashlib.sha256().update()`. Memory usage stays constant regardless of file size.

### Rationale
- 64 KB is a well-established I/O buffer size — aligned with filesystem block sizes on most operating systems.
- `hashlib.sha256()` supports streaming via `.update()` natively.
- Keeps memory usage at O(1) instead of O(file_size).

### Consequences
- Hashing a 50 MB file uses ~64 KB of buffer, not 50 MB.
- Slightly more code than `hashlib.sha256(path.read_bytes()).hexdigest()`, but much safer.
- The chunk size is a module-level constant, not configurable — it's an implementation detail, not a user setting.

---

## DL-009: Lazy Docling Initialization

**Date:** 29 June 2026
**Phase:** Milestone 1, Step 2
**Status:** Active

### Context
IBM Docling's `DocumentConverter` downloads ML models on first instantiation and consumes significant memory. If the user is only ingesting `.md` or `.txt` files, loading Docling is pure waste.

### Decision
Lazily import and instantiate `DocumentConverter` inside `_get_converter()` — called only when the first `.pdf` or `.docx` file is encountered. Plain-text files bypass Docling entirely via `Path.read_text()`.

### Rationale
- Application startup stays instant even when Docling is installed.
- If a session only processes plain-text documents, Docling is never loaded.
- The converter is cached after first use (`self._converter`) — subsequent PDF/DOCX files reuse it.

### Consequences
- The first PDF/DOCX parse has a cold-start delay (model loading).
- Tests can mock Docling without installing the heavy package locally.
- Two distinct code paths for parsing (plain-text vs. rich) — but both are simple.

---

## DL-010: Frozen Dataclass for DocumentMetadata

**Date:** 30 June 2026
**Phase:** Milestone 1, Step 3
**Status:** Active

### Context
`DocumentMetadata` captures file-system information at a point in time. Once extracted, this data should not change — the file name shouldn't silently mutate mid-pipeline.

### Decision
Use `@dataclass(frozen=True, slots=True)` for `DocumentMetadata`.

### Rationale
- **Immutability** prevents accidental mutation after extraction.
- **Slots** reduce memory footprint (no `__dict__` per instance).
- Makes the object hashable — can be used as a dict key or set member if needed.
- Signals intent: "this is a snapshot, not a mutable state object."

### Consequences
- Creating a modified version requires `dataclasses.replace()` — slightly more verbose than direct assignment.
- Fields cannot be set after construction — any computed fields must be passed to the constructor.

---

## DL-011: Hand-Rolled Recursive Text Chunker

**Date:** 30 June 2026
**Phase:** Milestone 1, Step 4
**Status:** Active

### Context
Text chunking is critical for retrieval quality. Pre-built chunkers (e.g., from LangChain) exist but are rejected per DL-001. The chunker must split text into overlapping pieces that fit within a size limit while preserving semantic boundaries.

### Decision
Implement a recursive character-splitting algorithm with a configurable separator hierarchy:
1. Paragraphs (`\n\n`)
2. Lines (`\n`)
3. Sentences (`. `)
4. Words (` `)
5. Characters (last resort)

If splitting by the current separator produces pieces that still exceed `chunk_size`, the algorithm recurses with the next separator. After splitting, small pieces are merged back into chunks with configurable overlap.

### Rationale
- Preserves semantic boundaries as much as possible — paragraphs > lines > sentences > words > characters.
- **Guarantees** no chunk exceeds the size limit (character split is the absolute fallback).
- Overlap ensures context continuity across chunk boundaries for better retrieval.
- Fully configurable via `ChunkingConfig` — no hardcoded separator lists or sizes.

### Consequences
- More complex than a simple `text[i:i+n]` split, but significantly better retrieval quality.
- The separator hierarchy is ordered by "desirability" — the algorithm always prefers the cleanest possible split point.
- Added `ChunkingError` to the exception hierarchy for invalid config or empty text.

---

## DL-012: Domain Exception Hierarchy

**Date:** 27 June 2026
**Phase:** Milestone 0 — Exception Design
**Status:** Active (extended in Steps 1–4)

### Context
The application needs structured error handling. Generic `ValueError` and `RuntimeError` don't tell API error handlers what kind of failure occurred or what HTTP status to return.

### Decision
Create a single base exception `AtlasIQError` with domain-specific subclasses:
```
AtlasIQError
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

### Rationale
- A single `except AtlasIQError` clause catches all domain errors at the API boundary.
- Subclasses allow fine-grained handling (e.g., `DocumentValidationError` → HTTP 422, `DatabaseConnectionError` → HTTP 503).
- New exception types are added as new modules are built (e.g., `ChunkingError` was added in Step 4).

### Consequences
- Every module raises a specific domain exception — never generic Python exceptions.
- API error handlers can map exception types to HTTP responses cleanly.
- External library errors are caught and wrapped in domain exceptions at module boundaries.

---

## DL-013: Validator Reads Config, Not Hardcoded Values

**Date:** 29 June 2026
**Phase:** Milestone 1, Step 1
**Status:** Active

### Context
The document validator needs to know which file extensions are supported and what the maximum file size is. These could be hardcoded constants or read from configuration.

### Decision
Inject `IngestionConfig` into `DocumentValidator.__init__()`. The validator reads `supported_formats` and `max_file_size_mb` from the config object.

### Rationale
- Changing supported formats or size limits doesn't require code changes.
- Different deployments can have different limits (e.g., a demo with 10 MB limit vs. enterprise with 100 MB).
- Unit tests can inject custom configs to test edge cases without monkeypatching.

### Consequences
- The validator cannot be instantiated without a config object — intentional dependency.
- Config changes take effect on the next validator instantiation (not dynamically at runtime — acceptable for V1).

---

## DL-014: All Tests Run Without Docker or Network

**Date:** 29 June 2026
**Phase:** Milestone 1 — Testing Strategy
**Status:** Active

### Context
The test suite must be fast and runnable on any developer machine. Requiring Docker, database connections, or ML model downloads for unit tests would slow development and make CI fragile.

### Decision
- Use `MagicMock` to stub external dependencies (Docling, databases, network calls).
- Use `tmp_path` (pytest fixture) for filesystem-dependent tests.
- Never require Docker running for the `tests/` directory to pass.
- Heavy dependencies (Docling) are lazily loaded and fully mocked in tests.

### Rationale
- Tests run in under 1 second (currently 0.77s for 82 tests).
- No flaky tests from network timeouts or database state.
- New developers can run `pytest` immediately after cloning.

### Consequences
- Integration tests (requiring Docker) will be a separate test suite when needed.
- Mocked tests don't catch Docling API changes — but those are caught by Docker-based testing.

---

## DL-015: Conventional Commits

**Date:** 27 June 2026
**Phase:** Project-wide
**Status:** Active

### Context
The project needs a consistent commit message format for readability, changelog generation, and mentor review.

### Decision
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `refactor:` — code restructuring without behavior change
- `test:` — adding or fixing tests

### Rationale
- Commit history is scannable at a glance.
- Semantic prefixes make `git log --oneline` immediately informative.
- Required by the course deliverables specification.

### Consequences
- Every commit message must be prefixed — no exceptions.
- Commits should be atomic: one logical change per commit.

---

## DL-016: Lazy Sentence-Transformers Loading

**Date:** 1 July 2026
**Phase:** Milestone 1, Step 5
**Status:** Active

### Context
The nomic-embed-text-v1.5 model is ~550 MB and takes several seconds to load. If a user only ingests plain-text files (`.md`, `.txt`), loading the embedder wastes memory and startup time. Additionally, the model is only needed when generating embeddings, not during validation, parsing, or change detection.

### Decision
Lazily import and instantiate `SentenceTransformer` inside `_ensure_model_loaded()` — called only when the first `embed()` or `embed_query()` call occurs. The model is cached after first use in `self._model`. Use `TYPE_CHECKING` guard for the import to avoid runtime loading at module import time.

### Rationale
- Application startup stays instant even when sentence-transformers is installed.
- If a session only processes plain-text documents (which bypass embedding in V1), the model is never loaded.
- Consistent with the lazy Docling initialization in `parser.py` (DL-009).
- Memory footprint stays low until embeddings are actually needed.
- The model is cached after first use — subsequent embedding calls reuse the loaded model.

### Consequences
- The first `embed()` or `embed_query()` call has a one-time cold-start delay (model loading takes 2-5 seconds).
- Tests can mock `SentenceTransformer` without installing the ~550 MB package locally.
- The embedder's public API hides when the model loads — it's an implementation detail.
- Thread safety will need attention in Milestone 2 when concurrent requests are introduced (add lock around model loading).

---

*Last updated: 1 July 2026*
