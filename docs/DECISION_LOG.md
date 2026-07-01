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

## DL-017: Domain Records as Dataclasses in `backend/domain/`

**Date:** 2 July 2026
**Phase:** Milestone 1, Step 6A
**Status:** Active

### Context
Steps 6B–7 need a shared vocabulary to describe a document and a chunk as they move between the pipeline and the storage layer. The obvious place was `backend/models/`, and the obvious mechanism (given the SQLAlchemy + Qdrant stack) might have been ORM-mapped classes or Pydantic schemas.

### Decision
Create a new package `atlasiq/backend/domain/` containing plain, framework-independent dataclasses:
- `DocumentStatus` — enum of lifecycle states (`pending`/`processing`/`completed`/`failed`).
- `DocumentRecord` — mutable `@dataclass(slots=True)` mirroring the `documents` table.
- `ChunkRecord` — frozen `@dataclass(frozen=True, slots=True)` mirroring the `chunks` table.

These carry **no** ORM metadata, no persistence behaviour, and no knowledge of any store. The pre-existing empty `backend/models/` package was left untouched (reserved for future Pydantic API request/response schemas, which is what `models` conventionally means in a FastAPI codebase).

### Rationale
- `models` is an overloaded name that implies ORM tables or Pydantic schemas — these records are neither.
- `backend/domain/` names the responsibility explicitly: the shared language repositories, the pipeline, and (later) the API all speak.
- Keeping the domain layer framework-free means repositories own the raw SQL translation, consistent with DL-001 (no heavy abstractions).
- `DocumentRecord` is mutable because `status`/`updated_at` change during ingestion; `ChunkRecord` is frozen because a chunk is an immutable artifact of one ingestion (extends the DL-010 frozen-dataclass pattern).

### Consequences
- Two clean boundaries: domain records (pure) and repositories (SQL/driver).
- No test needs a database to exercise the domain layer.
- Both `backend/domain/` and `backend/models/` now exist; contributors must not confuse them.

---

## DL-018: Index-Based Deterministic Chunk ID as the PostgreSQL↔Qdrant Join Key

**Date:** 2 July 2026
**Phase:** Milestone 1, Step 6A (correctness depends on Step 7B)
**Status:** Active

### Context
A chunk is stored in two places: its text/metadata in PostgreSQL (`chunks` table) and its vector in Qdrant. The two records need a shared identifier so they can be correlated, deleted, and re-indexed together. That id also determines whether re-ingesting a document duplicates chunks or overwrites them.

### Decision
Generate the chunk id deterministically from position:
```
chunk_id = uuid5(_CHUNK_ID_NAMESPACE, f"{document_id}:{chunk_index}")
```
The same `(document_id, chunk_index)` pair always maps to the same id. This id is written to both `chunks.id` (PostgreSQL) and the Qdrant point id. The namespace UUID is a pinned module constant.

### Rationale
- Identity is **positional** (by `chunk_index`), which makes upserts idempotent: chunk `#3` always overwrites the previous chunk `#3` rather than creating a duplicate.
- A single shared id is the simplest possible join key between the two stores.
- Content-addressed ids (hash of chunk text) were considered and rejected for V1 — they would avoid orphans automatically but break the simple index-based join and add complexity with no M1 benefit (YAGNI).

### Consequences / Documented Limitations
- **Assumption:** `document_id` is stable across re-ingestions of the same file (looked up by hash in the repository, not regenerated per run).
- **Chunking-config-change limitation:** if `ChunkingConfig` changes and a document produces *fewer* chunks than before, a naive upsert-without-delete would leave **orphaned tail chunks** (e.g. old had 10, new has 7 → chunks 7,8,9 stale). Correctness therefore depends on the Step 7B re-index path deleting all existing chunks (both stores) before re-inserting. This makes delete-then-insert mandatory, not optional.
- Changing `_CHUNK_ID_NAMESPACE` would orphan every existing chunk id — it must never change.

---

## DL-019: PostgreSQL Repository — Raw-SQL Boundary with Bound Params and Exception Wrapping

**Date:** 2 July 2026
**Phase:** Milestone 1, Step 6B
**Status:** Active

### Context
The pipeline needs to persist and query documents/chunks, and to decide NEW/MODIFIED/UNCHANGED. The in-memory hash registry from DL-007 was always meant to migrate to the database.

### Decision
Add `atlasiq/backend/repositories/document_repository.py` — an async `DocumentRepository` that is the **only** place raw SQL for the `documents` and `chunks` tables lives. It exposes `upsert_document`, `get_document_by_id`, `get_document_by_hash`, `update_status`, `insert_chunks`, `delete_chunks_for_document`, and `list_documents`. It consumes/returns DL-017 domain records.

### Rationale
- Every query uses SQLAlchemy `text()` with **bound parameters** (never string interpolation) → SQL-injection safe.
- Every `SQLAlchemyError` is caught and re-raised as `DatabaseQueryError` (DL-012) → no driver exception leaks past the repository boundary.
- `get_document_by_hash` is the hook that will let change detection migrate off the in-memory dict (DL-007) without changing its public behaviour.
- Vector search is intentionally **not** here — this repository is ingestion-focused; retrieval is Milestone 2 (YAGNI).

### Consequences
- Table/column names live as module constants; JSON chunk metadata is serialized and cast to `JSONB`.
- Tests mock `PostgresClient`/`AsyncSession` with `AsyncMock` — no real database, honouring DL-014.
- This step made async unit tests necessary for the first time (see DL-021).

---

## DL-020: Explicit setuptools Package Discovery (Flat-Layout Packaging Fix)

**Date:** 2 July 2026
**Phase:** Milestone 1 — Packaging / Environment
**Status:** Active

### Context
Creating a virtual environment and running `pip install -e ".[dev]"` failed:
```
error: Multiple top-level packages discovered in a flat-layout:
['atlasiq', 'configs', 'prompts', 'watched_documents'].
```
The project uses a flat layout (packages at the repo root) and `pyproject.toml` had no `[tool.setuptools]` section, so setuptools' automatic discovery saw sibling resource directories (`configs/`, `prompts/`, `watched_documents/`) as candidate packages and refused to guess.

### Decision
Add explicit discovery scoped to the application package only:
```toml
[tool.setuptools.packages.find]
include = ["atlasiq*"]
```

### Rationale
- Installs only `atlasiq` and its subpackages; excludes resource/doc/test directories that are not importable packages.
- Standard best-practice fix for a flat-layout project with sibling non-package directories.
- Avoids restructuring into a `src/` layout — no file moves, existing architecture preserved.

### Consequences
- `pip install -e ".[dev]"` now builds the `atlasiq` editable wheel successfully.
- Adding a new top-level application package in future requires it to match `atlasiq*` or be added to `include`.

---

## DL-021: Editable-Install Baseline on Python 3.13 venv; Async Test Tooling

**Date:** 2 July 2026
**Phase:** Milestone 1 — Environment / Testing
**Status:** Active

### Context
Early steps (6A/6B) were developed against a system Python 3.10 interpreter, but `pyproject.toml` declares `requires-python >=3.12`. A dedicated virtual environment was created running **Python 3.13.7** to align with the declared target. During install, `pytest-asyncio`, `sqlalchemy`, and `types-PyYAML` were found to be declared but not present, and the async repository (Step 6B) needed them.

### Decision
- Standardise development on the `.venv` (Python 3.13) with `atlasiq` installed editable (`pip install -e ".[dev]"`).
- Ensure the async/test toolchain declared in `pyproject.toml` is actually installed: `pytest-asyncio` (config already had `asyncio_mode = "auto"`), `sqlalchemy` (core dep, needed at runtime by the repository), and `types-PyYAML` (added to dev deps for mypy stubs).

### Rationale
- Testing and type-checking must run on the same interpreter the project targets (3.12+), not an incidental 3.10.
- The repository's async methods require real `async` test execution (`pytest-asyncio`), and `sqlalchemy.text`/`SQLAlchemyError` are core runtime imports that cannot be lazy-loaded like the ML models.

### Consequences
- Because the project now runs on 3.12+, `datetime.UTC` and `enum.StrEnum` (both 3.11+) are available; earlier `# noqa: UP017`/`# noqa: UP042` shims added for the old 3.10 machine were removed (see DL-023).
- **Environmental note:** on Windows, `pip install -e ".[dev]"` intermittently hit `WinError 32` file locks while writing large binaries (torch, mpmath) — caused by antivirus/IDE indexing scanning `.venv`, **not** a packaging defect. It resolves on retry; the `atlasiq` editable wheel builds cleanly every time.

---

## DL-022: Offline Test Isolation — Simulate a Missing Package via a `None` Entry in `sys.modules`

**Date:** 2 July 2026
**Phase:** Milestone 1 — Debugging Session (Testing)
**Status:** Active

### Context — The Bug
After moving to the Python 3.13 venv (DL-021) where `sentence-transformers` is actually installed, the full suite went from ~0.7s to **90 seconds** and one test failed:
`tests/test_embedder.py::TestLazyLoading::test_import_error_raises`.

The test verifies that a missing `sentence-transformers` package raises `EmbeddingError`. It simulated absence with:
```python
del sys.modules["sentence_transformers"]
```
- On the old 3.10 machine the package was **not installed**, so the subsequent real `import sentence_transformers` failed → `EmbeddingError` raised → test passed.
- On the 3.13 venv the package **is** installed, so deleting the cached entry made Python re-import the **real** package, which then tried to load the `nomic-embed-text-v1.5` model — sending unauthenticated requests to the Hugging Face Hub (the 90s delay and network warnings) and never raising `ImportError`. The test failed and, worse, the suite now hit the network, violating DL-014.

### Decision
Simulate an absent package without deleting the entry:
```python
sys.modules["sentence_transformers"] = None  # forces ImportError on import
```
A `None` entry in `sys.modules` makes `import sentence_transformers` raise `ImportError` directly — Python never imports the real package and never touches the network. The original mock is restored in a `finally` block.

### Rationale
- Reproduces the exact condition under test (package unavailable) deterministically, regardless of whether the package is installed.
- Restores DL-014 compliance: the suite is fully offline again.
- Minimal, one-line change; no application code touched; test intent preserved.

### Consequences
- Suite returned to green and fast: **153 passed in ~1s** (from 90s).
- General lesson recorded: tests must not rely on a package being *absent from the environment* to simulate failure — the absence must be simulated explicitly.

---

## DL-023: Project-Wide Ruff/MyPy Baseline Hardening (incl. a Real Qdrant Runtime Bug)

**Date:** 2 July 2026
**Phase:** Milestone 1 — Debugging / Baseline Verification (pre–Step 6C)
**Status:** Active

### Context
A pre-Step-6C baseline audit ran `ruff check .` and `mypy .` across the **whole** project for the first time (earlier runs were scoped to individual new files). This surfaced accumulated debt that had been masked: 46 ruff findings and 14 mypy errors across completed modules and tests. All were pre-existing, but the baseline gate required a clean project.

### Decisions & Fixes

**1. Real runtime bug — Qdrant `.search()` removed in qdrant-client 1.18.**
`mypy` flagged `QdrantClient has no attribute "search"`; verified at runtime (`hasattr(QdrantClient, 'search') == False`). The API was replaced by `query_points()`. Fixed `qdrant_client.py` to call `self.client.query_points(query=…, …).points`. This was a latent `AttributeError` that would have broken Milestone 2 retrieval.

**2. `async_sessionmaker` in `postgres_client.py`.**
`sessionmaker(..., class_=AsyncSession)` failed mypy's overload check and returned `Any`. Switched to `async_sessionmaker[AsyncSession]` (the SQLAlchemy 2.0 async idiom), fixing both the overload error and the `get_session` `Any`-return.

**3. FastAPI-aware ruff configuration.**
- `flake8-bugbear.extend-immutable-calls = ["fastapi.Depends", "fastapi.Query", "fastapi.Path", "fastapi.Body", "fastapi.Header"]` — silences B008 false positives (`Depends()` in argument defaults is the intended FastAPI idiom).
- `per-file-ignores` for `atlasiq/backend/api/*` and `main.py` on `TC001/TC002/TC003` — because **FastAPI resolves annotations at runtime** (`get_type_hints`), so route-signature imports must stay at runtime scope. Moving them into a `TYPE_CHECKING` block (which ruff otherwise wanted) would break dependency injection.

**4. `DocumentStatus` → `enum.StrEnum`.**
Now that the project runs on 3.12+, converted from `class DocumentStatus(str, enum.Enum)` to `enum.StrEnum` and removed the obsolete `# noqa: UP042`. Also switched timestamps to `datetime.UTC` (removing `# noqa: UP017`). Where mypy still flagged an enum-vs-str `comparison-overlap` in tests, the assertion was rewritten to `isinstance(..., str)` plus a `str`-typed comparison (stronger and type-clean).

**5. Type-argument and misc fixes.**
- `dict` → `dict[str, Any]` in `qdrant_client.py` and `routes_health.py`.
- `parser.py`: typed the lazily-loaded Docling converter as `Any`, removed a stale `# type: ignore`, and wrapped the markdown result in `str(...)` to avoid an `Any`-return.
- Removed dead imports (`Settings` in `main.py`, `DatabaseConnectionError` in `qdrant_client.py`) and a dead `parser` variable in `test_parser.py`.
- `types-PyYAML` added to dev deps to resolve the `yaml` stub error under mypy strict.
- Auto-fixed pervasive stylistic debt (UP017 `datetime.UTC`, UP006/UP035 `list`, I001 import order, W293 whitespace, safe TC import moves in non-FastAPI modules).

### Rationale
- The baseline gate demands `ruff` and `mypy --strict` clean project-wide, not just on new files.
- Several findings were genuine (the Qdrant bug, dead code, wrong `dict` generics); the rest were consistency/idiom fixes appropriate for the 3.12+ target.
- FastAPI-specific rules (B008, TC) are false positives and were configured away rather than worked around per-line.

### Consequences
- Project-wide baseline is now clean: **`pytest` 153 passed, `ruff check .` all passed, `mypy .` 0 issues in 40 files, `pip check` clean, editable install intact.**
- Completed modules were modified — but only to fix verified errors (a runtime bug, type errors, dead code), never for stylistic preference beyond what the linters required.
- Established the convention: FastAPI route modules are exempt from TYPE_CHECKING-move rules, and `Depends`/`Query`/etc. are treated as immutable calls.

---

*Last updated: 2 July 2026*


## DL-023: PostgreSQL Repository Implementation Debugging Session

**Date:** 2 July 2026  
**Phase:** Milestone 1, Step 6B — Debugging Session  
**Status:** Active

### Context — The Multi-Stage Debugging Journey
Step 6B (PostgreSQL Repository) involved implementing `DocumentRepository` with proper SQLAlchemy async patterns. This triggered a cascade of issues that required methodical debugging across several hours:

1. **Environment setup issues** — transitioning from system Python 3.10 to declared target Python 3.13.7
2. **Packaging problems** — setuptools failing with "Multiple top-level packages" error
3. **Type-checking failures** — 14 mypy errors across 6 files
4. **Test failures** — offline test isolation broken when `sentence-transformers` was actually installed
5. **Runtime bugs discovered** — Qdrant API changed in version 1.18

### Decision: Systematic Multi-Layer Fixes
Instead of piecemeal fixes, we implemented a comprehensive debugging approach:

1. **Environment Layer**: Created fresh Python 3.13.7 `.venv` and validated `pip install -e ".[dev]"` works
2. **Packaging Layer**: Added explicit `[tool.setuptools.packages.find]` to exclude non-package directories
3. **Type-Safety Layer**: Addressed all 14 mypy errors with specific fixes for each category
4. **Testing Layer**: Fixed offline test isolation with `sys.modules["sentence_transformers"] = None` pattern
5. **Runtime Layer**: Updated Qdrant client from deprecated `.search()` to `.query_points()`

### Key Debugging Insights and Fixes

**Packaging Fix (DL-020)**:
```
[tool.setuptools.packages.find]
include = ["atlasiq*"]
```
This excluded `configs/`, `prompts/`, `watched_documents/` directories from being mistaken as Python packages.

**Async SQLAlchemy Pattern Fix**:
- Changed `sessionmaker(bind=engine, class_=AsyncSession)` to `async_sessionmaker[AsyncSession]`
- This fixed mypy overload errors and ensured proper async session handling

**Qdrant API Migration**:
- Discovered `QdrantClient().search()` removed in qdrant-client 1.18
- Migrated to `client.query_points(query=..., ...).points`
- **This was a latent runtime bug** that would have broken retrieval in Milestone 2

**Offline Test Isolation Fix**:
Original (failing when package installed):
```python
del sys.modules["sentence_transformers"]
```
Fixed:
```python
sys.modules["sentence_transformers"] = None  # forces ImportError
```
This ensures offline testing compliance (DL-014) regardless of package installation status.

**FastAPI Ruff Configuration**:
Added specialized rules for FastAPI's runtime annotation resolution:
- `flake8-bugbear.extend-immutable-calls` for FastAPI dependency injection
- `per-file-ignores` for `TYPE_CHECKING` imports in API routes

**Python 3.12+ Language Features**:
- Migrated from `# noqa: UP017` to `datetime.UTC`
- Converted `DocumentStatus` from `class DocumentStatus(str, enum.Enum)` to `enum.StrEnum`
- Removed compatibility shims now that we're on Python ≥3.12

### Rationale
The debugging session revealed that several "minor" issues were actually:
1. **Critical runtime bugs** (Qdrant API break)
2. **Broken conventions** (async session patterns)
3. **Environmental assumptions** (3.10 vs 3.13 Python features)
4. **Testing fragility** (package installation state affecting offline tests)

By systematically addressing each layer, we:
- Fixed actual bugs before they became production issues
- Established a clean baseline for Step 6C
- Maintained the "all tests pass offline" principle
- Achieved strict mypy compliance across the entire codebase

### Consequences
- **Project health restored**: All 153 tests pass, ruff clean, mypy strict clean
- **Environment standardized**: All development now uses Python 3.13.7 venv
- **Latent bugs fixed**: Qdrant retrieval will work in Milestone 2
- **Stronger foundations**: Clean slate for implementing Step 6C (Qdrant Repository)
- **Less technical debt**: Removed Python 3.10 compatibility shims, using modern language features

### Lesson Learned
Debugging complex projects requires a **systematic, layer-by-layer approach**. Surface errors often mask deeper architectural issues. The most valuable discovery was the Qdrant API breakage — found during type-checking, not runtime testing, demonstrating the value of strict static analysis even for dynamic Python projects.

---

*Decision Log extended to document debugging session insights*

