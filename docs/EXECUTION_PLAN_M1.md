# AtlasIQ — Execution Plan: Milestone 1 Completion (Steps 6–9)

> **Purpose:** A single, reviewable blueprint for how Steps 6A → 9 will be
> implemented. This is written **before** any code, so the architecture,
> module boundaries, interfaces, and test strategy are agreed up front and
> we don't drift mid-build. Each step maps to a single atomic commit.

**Author:** Verdhan Yash
**Date:** 2 July 2026
**Scope:** Repository layer → Pipeline orchestration → Ingestion API → E2E integration
**Governing rules:** DL-001…DL-016, CODE_REVIEW_CHECKLIST.md, DEFINITION_OF_DONE.md

---

## 0. Guiding Principles (apply to every step)

These are non-negotiable and derived from the existing decision log:

| Principle | Source | How it applies here |
|-----------|--------|---------------------|
| Single Responsibility | DL-006, Checklist §1–2 | Each repository touches exactly one store. Pipeline orchestrates, never persists directly. |
| No hardcoded values | DL-002, DL-013, Checklist §3 | Table names, collection names, batch sizes all flow from config/constants. |
| Domain exceptions only | DL-012 | Wrap `sqlalchemy` / `qdrant` errors in `DatabaseQueryError` / `DatabaseConnectionError`. Never leak library exceptions. |
| Tests run offline | DL-014 | All DB clients, Qdrant, and the embedder are mocked. No Docker, no network, no model downloads. |
| Database-ready interfaces | DL-007 | `ChangeDetector` migrates from in-memory dict → PostgreSQL repository **without** changing its public API. |
| Lazy heavy deps | DL-009, DL-016 | Embedder already lazy. Watcher imports `watchdog` lazily. |
| Conventional Commits | DL-015 | One commit per sub-step, e.g. `feat: add domain models (step 6a)`. |
| Encapsulation | Checklist §2 | No module outside `database/` imports `sqlalchemy` or `qdrant_client` directly. |

**Definition of Done gate for every step:** unit tests + type hints + logging +
docstrings + externalized config + error handling + README/context update +
no TODOs + no hardcoded values + passes ruff + passes mypy strict.

---

## 1. Target End-State Architecture

```
                      IngestionPipeline (orchestrator, Step 7)
                                   │
        ┌──────────┬──────────┬────┴─────┬───────────┬──────────────┐
        ▼          ▼          ▼          ▼           ▼              ▼
   Validator    Change     Parser     Chunker    Embedder     Repositories
   (Step 1)    Detector   (Step 2)   (Step 4)    (Step 5)      (Step 6)
                (Step 3)                                            │
                                                    ┌───────────────┴───────────────┐
                                                    ▼                               ▼
                                        DocumentRepository (6B)        ChunkVectorRepository (6C)
                                                    │                               │
                                                    ▼                               ▼
                                          PostgresClient (6D)             QdrantVectorClient (6D)
                                          (documents, chunks)             (atlasiq_chunks vectors)

        Upload API (8A) ─┐
        Status API (8B) ─┼──►  IngestionPipeline  ──►  Repositories (6B/6C)
        Folder Watcher(8C)┘     (routes call pipeline directly)
```

**Key boundary decisions:**
- PostgreSQL stores **document metadata + chunk text** (source of truth, relational).
- Qdrant stores **chunk vectors + minimal payload** (`document_id`, `chunk_index`) for filtered deletes and retrieval.
- The **chunk `id` is shared** between PostgreSQL `chunks.id` and the Qdrant point id — this is the join key. Generated as a deterministic UUID.
- Repositories are the **only** async boundary that talks to a store. The pipeline calls repositories; it never touches `sqlalchemy`/`qdrant` types.

---

## 2. Step-by-Step Plan

### Step 6A — Domain Models
**Files:** `atlasiq/backend/domain/__init__.py`, `atlasiq/backend/domain/document.py`, `atlasiq/backend/domain/chunk.py`, `tests/test_domain_models.py`

**What:** Define framework-independent **domain records** that describe a document
and a chunk in AtlasIQ's own terms. They happen to mirror the columns in
`schema.sql`, but they are **not** ORM/database models — they carry no SQLAlchemy
metadata, no persistence behavior, and no knowledge of any store. They are plain
dataclasses (consistent with DL-001's "no heavy abstractions" spirit and DL-010's
frozen dataclass pattern).

**Package placement — why `backend/domain/`, not `backend/models/`:** the name
`models` is overloaded and, in a FastAPI/SQLAlchemy codebase, strongly implies
either Pydantic request/response schemas or ORM table classes. These records are
neither. Placing them in `backend/domain/` makes the responsibility explicit —
they are the shared vocabulary that repositories, the pipeline, and (later) the
API all speak. The empty `backend/models/` package is left untouched for now
(it may later hold Pydantic API request/response schemas, which is what `models`
conventionally means); no code depends on it, so nothing needs to move or break.

**Design:**
- `DocumentStatus(enum.Enum)` → `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` (matches the `valid_status` CHECK constraint in `schema.sql`).
- `@dataclass(slots=True)` `DocumentRecord` — fields mirror the `documents` table (`id`, `filename`, `file_hash`, `file_type`, `file_size_bytes`, `title`, `author`, `page_count`, `word_count`, `status`, timestamps). Mutable because `status` transitions during processing.
- `@dataclass(frozen=True, slots=True)` `ChunkRecord` — mirrors the `chunks` table (`id`, `document_id`, `chunk_index`, `content`, `token_count`, `start_page`, `end_page`, `metadata`). Frozen: a chunk never mutates once created.
- A helper to generate deterministic chunk ids: `chunk_id(document_id, chunk_index) -> str` (UUID5 over a fixed namespace) so re-ingesting the same doc yields stable ids for idempotent upserts.

**Shared deterministic chunk id — design, assumptions, and limitations:**
- **Design:** `chunk_id = uuid5(NAMESPACE, f"{document_id}:{chunk_index}")`. The
  same `(document_id, chunk_index)` pair always maps to the same id, so an upsert
  of chunk `#3` of a document overwrites the previous chunk `#3` rather than
  creating a duplicate. This id is written to both `chunks.id` (PostgreSQL) and
  the Qdrant point id, making it the join key between the two stores.
- **Assumption:** chunk identity is defined by *position within a document*
  (`chunk_index`), **not** by chunk content. Two different ingestions of the same
  document produce chunk ids that line up by index.
- **Limitation — chunking config changes:** if `ChunkingConfig` (chunk_size,
  overlap, separators) changes between ingestions, the *text* mapped to a given
  `chunk_index` changes, and the total chunk count may differ. Because ids are
  index-based, this is handled correctly **only** via the Step 7B re-index path:
  MODIFIED documents delete all existing chunks (both stores) before re-inserting.
  A naive upsert-without-delete would leave **orphaned tail chunks** if the new
  version produces fewer chunks than the old one (e.g. old doc had 10 chunks,
  new config yields 7 → chunks 7,8,9 would be stale). Step 7B's delete-then-insert
  is therefore not optional — it is what keeps the index-based id scheme correct.
- **Limitation — document_id stability:** the join key is only stable if
  `document_id` is stable across re-ingestions of the same file. `document_id`
  is derived from the file identity (see 6B: looked up by `file_hash`/path), not
  regenerated per run, so a modified file keeps its `document_id` and its chunks
  realign by index.
- **Non-goal:** content-addressed chunk ids (hash of chunk text) were considered
  and rejected for V1 — they would avoid orphans automatically but break the
  simple index-based join and add complexity with no M1 benefit (YAGNI). Recorded
  as DL-018.

**Why dataclasses, not ORM models:** keeps the domain layer pure and testable
with zero DB dependency; repositories translate between these records and raw
SQL. Avoids importing SQLAlchemy declarative base across the codebase.

**Tests:** field defaults, enum values match schema CHECK constraint, `chunk_id`
determinism (same input → same id, different index → different id), frozen
enforcement on `ChunkRecord`.

**Commit:** `feat: add document and chunk domain models (step 6a)`

---

### Step 6B — PostgreSQL Repository
**Files:** `atlasiq/backend/repositories/document_repository.py`, `tests/test_document_repository.py`

**What:** Async CRUD for `documents` and `chunks` tables, using the existing
`PostgresClient.session_factory`. This is the **only** place raw SQL for these
tables lives.

**Public interface (async):**
```
class DocumentRepository:
    def __init__(self, client: PostgresClient) -> None
    async def upsert_document(self, doc: DocumentRecord) -> None
    async def get_document_by_hash(self, file_hash: str) -> DocumentRecord | None
    async def get_document_by_id(self, document_id: str) -> DocumentRecord | None
    async def update_status(self, document_id: str, status: DocumentStatus) -> None
    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None
    async def delete_chunks_for_document(self, document_id: str) -> None
    async def list_documents(self, limit: int, offset: int) -> list[DocumentRecord]
```

**Design notes:**
- Uses `sqlalchemy.text()` with **bound parameters** (never string interpolation → SQL-injection safe, satisfies security guardrails).
- Wraps all `SQLAlchemyError` in `DatabaseQueryError` (DL-012). Never leaks driver exceptions.
- `get_document_by_hash` is what enables change detection to migrate off the in-memory dict (DL-007) — the pipeline will query by hash to decide NEW/MODIFIED/UNCHANGED.
- `insert_chunks` runs in a single transaction (all-or-nothing).
- Table/column names are module-level constants — no magic strings scattered around.

**Tests:** mock `PostgresClient` + `AsyncSession` with `AsyncMock`; assert correct
SQL params passed, correct record mapping, exception wrapping. No real DB.

**Commit:** `feat: add PostgreSQL document repository (step 6b)`

---

### Step 6C — Qdrant Repository
**Files:** `atlasiq/backend/repositories/vector_repository.py`, `tests/test_vector_repository.py`

**What:** Thin domain-facing wrapper over `QdrantVectorClient` that speaks in
`ChunkRecord` + embedding vectors, not Qdrant primitives. Keeps the pipeline
free of Qdrant payload-shaping logic.

**Public interface:**
```
class ChunkVectorRepository:
    def __init__(self, client: QdrantVectorClient) -> None
    def store(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> None
    def delete_for_document(self, document_id: str) -> None
```

**Design notes:**
- Builds the payload `{ "document_id", "chunk_index" }` from each `ChunkRecord`, zips with vectors (`strict=True`), delegates to `client.upsert_vectors`.
- Validates `len(chunks) == len(vectors)` → raises `DatabaseQueryError` on mismatch.
- `delete_for_document` delegates to the existing `delete_by_document_id`.
- **Retrieval/search stays out of scope** here — that's Milestone 2. This repo is ingestion-write-only for now (YAGNI, Checklist §4/§7).

**Tests:** mock `QdrantVectorClient`; assert payload shape, id alignment, length-mismatch error.

**Commit:** `feat: add Qdrant chunk vector repository (step 6c)`

---

### Step 6D — Database Clients (touch-ups only)
**Files:** `atlasiq/database/postgres_client.py`, `atlasiq/database/qdrant_client.py` (minimal), `tests/test_db_clients.py`

**What:** The clients already exist and are solid. This step is a **surgical
review + minimal hardening**, not a rewrite (respects "do not redesign existing
architecture", Checklist §1).

**Planned changes (only if needed):**
- `PostgresClient`: add a small `session()` async-context-manager helper if repositories need cleaner transaction scoping. Keep existing methods intact.
- `QdrantVectorClient`: verify `vector_size` is wired from `EmbeddingConfig.dimension` at composition time (dependencies), not hardcoded 768. If a mismatch risk exists, document it.
- No signature changes to existing public methods → no regression to startup/health.

**Tests:** light unit tests for any new helper; confirm existing behavior unchanged.

**Commit:** `refactor: harden database client session handling (step 6d)`
(or `chore:` if changes are trivial). If no change is required, this step is a
documented no-op in the decision log.

---

### Step 7A — Pipeline Orchestrator
**Files:** `atlasiq/ingestion/pipeline.py`, `tests/test_pipeline.py`

**What:** The conductor. Wires Validator → ChangeDetector → Parser → Chunker →
Embedder → Repositories into one linear flow. Contains **orchestration only** —
zero parsing/embedding/SQL logic of its own (Checklist §1–2).

**Public interface:**
```
@dataclass
class IngestionResult:
    document_id: str
    status: ChangeStatus            # NEW / MODIFIED / UNCHANGED
    chunks_created: int
    skipped: bool

class IngestionPipeline:
    def __init__(self, validator, change_detector, parser, chunker,
                 embedder, document_repo, vector_repo) -> None
    async def ingest(self, file_path: Path) -> IngestionResult
```

**Flow inside `ingest()`:**
1. `validator.validate(path)` — reject bad files early.
2. `extract_metadata(path)` + compute hash → check `document_repo.get_document_by_hash`.
3. Decide `ChangeStatus`:
   - UNCHANGED → return early, `skipped=True`.
   - MODIFIED → delete old chunks (both stores) before re-inserting (Step 7B).
   - NEW → proceed.
4. `document_repo.upsert_document(status=PROCESSING)`.
5. `parser.parse(path)` → text.
6. `chunker.chunk(text)` → `list[str]`.
7. Build `ChunkRecord`s (deterministic ids via 6A).
8. `embedder.embed(chunk_texts)` → vectors.
9. `document_repo.insert_chunks()` + `vector_repo.store()`.
10. `document_repo.update_status(COMPLETED)`.
11. On any failure → `update_status(FAILED)`, re-raise as domain error.

**Dependency injection:** all seven collaborators are constructor-injected — the
pipeline constructs nothing itself, making it trivially unit-testable with mocks.

**Tests:** mock all seven collaborators; assert call order, NEW/MODIFIED/UNCHANGED
branches, FAILED status on mid-pipeline exception, chunk-count in result.

**Commit:** `feat: add ingestion pipeline orchestrator (step 7a)`

---

### Step 7B — Incremental Update Logic
**Files:** `atlasiq/ingestion/pipeline.py` (extend), `tests/test_pipeline.py` (extend)

**What:** The MODIFIED-document path — safe re-indexing without duplicates or
orphaned vectors. This is called out as its own step because it's the subtle,
correctness-critical part.

**Design:**
- On MODIFIED: delete existing chunks from **both** stores first
  (`document_repo.delete_chunks_for_document` + `vector_repo.delete_for_document`),
  then re-insert fresh chunks/vectors. Order matters: delete-then-insert.
- Postgres `ON DELETE CASCADE` already handles chunk cleanup if a document row is
  removed, but we delete chunks explicitly (keeping the document row + id stable)
  to preserve `created_at` history and avoid FK churn.
- Idempotency: deterministic chunk ids (6A) mean a re-run overwrites rather than
  duplicates, even if a prior run half-failed.
- Update `documents.file_hash`, `updated_at`, `word_count` on modification.

**Tests:** MODIFIED triggers deletes before inserts (assert call order); re-ingest
of identical content is UNCHANGED and a no-op; partial-failure leaves status FAILED.

**Commit:** `feat: add incremental re-indexing for modified documents (step 7b)`

---

### Step 8A — Upload API
**Files:** `atlasiq/backend/api/routes_ingestion.py`, `tests/test_ingestion_api.py`

**What:** `POST /ingest/upload` — the primary ingestion entry point (DL-005).
Accepts a file, saves it under `ingestion.storage_dir`, invokes the pipeline.

**`IngestionService` — reviewed and dropped for M1:** the original plan put an
`IngestionService` between the route and the pipeline. On review, its only
responsibilities would be (a) saving the uploaded bytes to disk and (b) calling
`pipeline.ingest(path)`. That is a thin pass-through, and the pipeline already
*is* the orchestration boundary — a service wrapping it adds an indirection layer
with no behavior of its own (violates YAGNI / Checklist §4 "no unnecessary
abstractions"). **Decision: no `IngestionService` in M1.** Instead:
- **File saving** (stream upload → sanitized path under `storage_dir`) is a small,
  well-scoped helper: `save_upload(upload, storage_dir) -> Path` in
  `routes_ingestion.py` (or a tiny `ingestion/upload_storage.py` if it needs
  reuse by the watcher — but the watcher reads files already on disk, so reuse is
  not required; keep it local to the route until a second caller appears).
- **Orchestration** is the pipeline's job — the route calls `pipeline.ingest(path)`
  directly via a `get_ingestion_pipeline()` dependency.
- If, in a later milestone, upload handling grows real responsibility (virus
  scanning, dedup-before-save, async job queue), a service can be introduced then
  with an actual reason to exist.

**Design:**
- Route handler stays tiny: receive `UploadFile` → `save_upload()` → `pipeline.ingest()` → JSON.
- `save_upload` sanitizes the filename and resolves the target **under**
  `storage_dir`, rejecting path-traversal (`..`, absolute paths) → security guardrail.
- Returns JSON: `{ document_id, status, chunks_created, skipped }`.
- Errors map through the existing `AtlasIQError` handler in `main.py`.
- New dependency provider in `dependencies.py`: `get_ingestion_pipeline()` —
  composed from existing client singletons + config. (No `get_ingestion_service()`.)
- **Security note to surface:** this endpoint is unauthenticated (auth is out of
  V1 scope per PROJECT_SCOPE). Will be flagged explicitly in README known-limitations.

**Tests:** FastAPI `TestClient` with pipeline mocked; happy path (200/JSON shape),
unsupported file (422 via `DocumentValidationError`), path-traversal filename rejected.

**Commit:** `feat: add document upload ingestion API (step 8a)`

---

### Step 8B — Status API
**Files:** `atlasiq/backend/api/routes_ingestion.py` (extend), `tests/test_ingestion_api.py` (extend)

**What:** `GET /ingest/status/{document_id}` and `GET /ingest/documents` — let
callers see ingestion progress/results.

**Design:**
- `GET /ingest/status/{document_id}` → reads `document_repo.get_document_by_id`, returns status + counts, `404` (via `DocumentNotFoundError`) if missing.
- `GET /ingest/documents?limit=&offset=` → `document_repo.list_documents`, paginated. Defaults from a small constants block (limit=50), overridable via query params.
- Read-only; no new writes. Reuses the repository from Step 6B.

**Tests:** status found/not-found, pagination params passed through, response shape.

**Commit:** `feat: add ingestion status and document listing API (step 8b)`

---

### Step 8C — Folder Watcher
**Files:** `atlasiq/ingestion/watcher.py`, `tests/test_watcher.py`

**What:** Optional `watchdog`-based monitor on `ingestion.watched_folder`
(DL-005: watcher is a secondary, optional source that reuses the same pipeline).

**Design:**
- `watchdog` imported **lazily** inside the watcher (DL-009/DL-016 pattern) so the
  package/import cost is only paid when the watcher is actually started.
- A `FileSystemEventHandler` subclass debounces create/modify events and calls
  `pipeline.ingest(path)` — **exact same pipeline** as the API (no duplicated logic, DL-005).
- Since the pipeline is async and watchdog callbacks are sync, the handler
  schedules ingestion onto the running event loop via `asyncio.run_coroutine_threadsafe`.
- Started/stopped explicitly (not auto-on at import). A `start()`/`stop()` pair;
  wiring into app lifespan is deferred/optional and gated by a config flag so it
  stays truly optional and doesn't break headless/cloud deploys.
- Validator inside the pipeline already rejects unsupported files, so the watcher
  can be permissive about what it forwards.

**Tests:** simulate events by calling the handler directly with a fake path; assert
`pipeline.ingest` scheduled; assert lazy import; assert non-file / unsupported events
are ignored. No real filesystem watching in tests.

**Commit:** `feat: add optional folder watcher ingestion source (step 8c)`

---

### Step 9 — End-to-End Integration
**Files:** `tests/test_integration_ingestion.py`, wiring in `atlasiq/backend/main.py`, `atlasiq/backend/core/dependencies.py`, docs updates

**What:** Register the ingestion router, wire all dependency providers, and prove
the whole chain works together with a realistic (still offline) integration test.

**Design:**
- `main.py`: `app.include_router(ingestion_router, prefix="/ingest")`.
- `dependencies.py`: finalize `get_ingestion_pipeline()` composing validator,
  change detector, parser, chunker, embedder, and both repositories from the
  existing client singletons; ensure Qdrant `vector_size` derives from the
  embedding dimension (no hardcode).
- **Integration test (offline):** a real temp `.txt`/`.md` file → real Validator,
  Parser, Chunker, ChunkRecord building → **mocked** Embedder (deterministic fake
  vectors) + **mocked** repositories. Verifies the pipeline produces the right
  number of chunks and calls stores correctly end-to-end without Docker/network
  (DL-014). This exercises real logic for everything except the two heavy/IO deps.
- Full suite run: `pytest`, `ruff check`, `mypy --strict`. Docker build sanity
  (`docker build`) if environment allows; otherwise documented.

**Docs updates (Definition of Done):**
- `project_context.md` — mark Steps 6–9 complete, update status/test counts/pipeline diagram.
- `docs/DECISION_LOG.md` — add DL-017…DL-020 for the new decisions (records-not-ORM, shared chunk id / join key, ingestion-write-only vector repo, watcher event-loop bridging).
- `README.md` — ingestion API usage + known limitation (unauthenticated upload).

**Commit:** `feat: wire ingestion pipeline end-to-end and integrate API (step 9)`

---

## 3. New Decision Log Entries (to be added during the work)

| ID | Decision | Step |
|----|----------|------|
| DL-017 | Domain records as dataclasses, not ORM models, placed in `backend/domain/` (not `backend/models/`) — keep domain layer framework-free; repositories own raw SQL. | 6A |
| DL-018 | Shared **index-based** deterministic chunk id (`uuid5(ns, "{document_id}:{chunk_index}")`) as the PostgreSQL↔Qdrant join key; enables idempotent re-ingestion. Correctness under chunking-config changes depends on the Step 7B delete-then-insert re-index path (prevents orphaned tail chunks). Content-addressed ids rejected for V1 (YAGNI). | 6A/7B |
| DL-019 | Vector repository is ingestion-write-only in M1; search deferred to M2 (YAGNI). | 6C |
| DL-020 | Change detection migrates from in-memory dict to `get_document_by_hash` query — public behavior preserved (fulfils DL-007). | 7A |
| DL-021 | Watcher bridges sync watchdog callbacks to the async pipeline via `run_coroutine_threadsafe`; started via config flag, optional by design. | 8C |
| DL-022 | No `IngestionService` layer in M1 — it would be a thin pass-through to the pipeline (which is already the orchestration boundary). Routes call the pipeline directly; upload file-saving is a small local helper. Introduce a service later only if upload handling grows real responsibility. | 8A |

---

## 4. Test Strategy Summary (DL-014 compliant)

| Layer | What's real | What's mocked |
|-------|-------------|---------------|
| Domain models (6A) | everything (pure) | nothing |
| PG repo (6B) | mapping/SQL param logic | `PostgresClient`, `AsyncSession` |
| Vector repo (6C) | payload shaping | `QdrantVectorClient` |
| Pipeline (7A/7B) | orchestration/branching | all 7 collaborators |
| API (8A/8B) | routing, validation, serialization | pipeline |
| Watcher (8C) | event handling/debounce | `watchdog`, pipeline |
| Integration (9) | validator+parser+chunker+record building | embedder, repositories |

**Every** external heavy dependency (Docling, sentence-transformers, PostgreSQL,
Qdrant, watchdog) is mocked. Target: full suite stays <2s, runs on a bare clone.

---

## 5. Sequencing & Dependencies

```
6A ─► 6B ─┐
      6C ─┼─► 7A ─► 7B ─► 8A ─► 8B ─► 8C ─► 9
6D ──────┘
```

- **6A first** — everything else consumes the record types.
- **6B & 6C** depend on 6A; can be built back-to-back. **6D** is independent review.
- **7A** needs 6A/6B/6C. **7B** extends 7A.
- **8A→8B→8C** need the pipeline. **9** wires and verifies the whole thing.

Each step is one commit, tests green before moving on, checklist audited, decision
log updated where a real decision was made. No step proceeds while the previous
step's tests are red.

---

## 6. What This Plan Deliberately Excludes (V1 scope, Checklist §9)

- No retrieval/search endpoints (Milestone 2).
- No reranker, no LLM, no query API.
- No auth on upload (documented limitation).
- No OCR, Kafka, K8s, microservices, agents, external SaaS connectors.
- No ORM layer, no Alembic migrations (schema.sql + IF NOT EXISTS is sufficient for V1).

---

*This plan will be executed step-by-step. After each step: run tests, run ruff +
mypy, audit against CODE_REVIEW_CHECKLIST, update docs, then commit with a
conventional-commit message and stop for review before the next step.*
