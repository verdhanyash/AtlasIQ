"""Tests for the ingestion pipeline orchestrator.

Every collaborator is mocked — no real files beyond a tiny ``tmp_path`` fixture,
no database, no network, no models (DL-014). The tests verify call ordering,
the NEW / UNCHANGED / MODIFIED branches, deterministic id wiring, and that a
mid-pipeline failure sets the document status to FAILED and re-raises.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from atlasiq.backend.core.exceptions import ChunkingError
from atlasiq.backend.domain import DocumentRecord, DocumentStatus, chunk_id
from atlasiq.ingestion.change_detector import ChangeStatus
from atlasiq.ingestion.pipeline import IngestionPipeline

if TYPE_CHECKING:
    from pathlib import Path

# ── Fixtures / helpers ───────────────────────────────────────────────────────


def _make_file(tmp_path: Path, name: str = "doc.txt", content: str = "hello world") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _build_pipeline() -> tuple[IngestionPipeline, dict[str, MagicMock]]:
    """Construct a pipeline with all seven collaborators mocked."""
    validator = MagicMock()
    validator.validate = MagicMock()

    change_detector = MagicMock()
    change_detector.compute_hash = MagicMock(return_value="hash-abc")

    parser = MagicMock()
    parser.parse = MagicMock(return_value="parsed text")

    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=["chunk 0", "chunk 1"])

    embedder = MagicMock()
    embedder.embed = MagicMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

    document_repo = MagicMock()
    document_repo.get_document_by_id = AsyncMock(return_value=None)
    document_repo.upsert_document = AsyncMock()
    document_repo.insert_chunks = AsyncMock()
    document_repo.update_status = AsyncMock()
    document_repo.delete_chunks_for_document = AsyncMock()

    vector_repo = MagicMock()
    vector_repo.store = MagicMock()
    vector_repo.delete_for_document = MagicMock()

    pipeline = IngestionPipeline(
        validator=validator,
        change_detector=change_detector,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        document_repo=document_repo,
        vector_repo=vector_repo,
    )
    collaborators = {
        "validator": validator,
        "change_detector": change_detector,
        "parser": parser,
        "chunker": chunker,
        "embedder": embedder,
        "document_repo": document_repo,
        "vector_repo": vector_repo,
    }
    return pipeline, collaborators


def _existing_record(file_hash: str, status: DocumentStatus) -> DocumentRecord:
    now = datetime.now(UTC)
    return DocumentRecord(
        id="whatever",
        filename="doc.txt",
        file_hash=file_hash,
        file_type=".txt",
        file_size_bytes=11,
        status=status,
        created_at=now,
        updated_at=now,
    )


# ── NEW (happy path) ─────────────────────────────────────────────────────────


class TestNewDocument:
    """Ingestion of a brand-new document."""

    @pytest.mark.asyncio
    async def test_returns_new_status_and_chunk_count(self, tmp_path: Path) -> None:
        pipeline, _ = _build_pipeline()

        result = await pipeline.ingest(_make_file(tmp_path))

        assert result.status is ChangeStatus.NEW
        assert result.chunks_created == 2
        assert result.skipped is False

    @pytest.mark.asyncio
    async def test_persists_to_both_stores_and_completes(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()

        await pipeline.ingest(_make_file(tmp_path))

        mocks["document_repo"].insert_chunks.assert_awaited_once()
        mocks["vector_repo"].store.assert_called_once()
        # final status transition is COMPLETED
        last_status = mocks["document_repo"].update_status.await_args.args[1]
        assert last_status is DocumentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_upserts_processing_before_parsing(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()
        calls: list[str] = []

        async def _record_upsert(*_a: object, **_k: object) -> None:
            calls.append("upsert")

        def _record_parse(*_a: object, **_k: object) -> str:
            calls.append("parse")
            return "text"

        mocks["document_repo"].upsert_document.side_effect = _record_upsert
        mocks["parser"].parse.side_effect = _record_parse

        await pipeline.ingest(_make_file(tmp_path))

        assert calls.index("upsert") < calls.index("parse")

    @pytest.mark.asyncio
    async def test_chunk_ids_are_deterministic(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()

        result = await pipeline.ingest(_make_file(tmp_path))

        records = mocks["document_repo"].insert_chunks.await_args.args[0]
        assert records[0].id == chunk_id(result.document_id, 0)
        assert records[1].id == chunk_id(result.document_id, 1)

    @pytest.mark.asyncio
    async def test_validate_called_first(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()

        await pipeline.ingest(_make_file(tmp_path))

        mocks["validator"].validate.assert_called_once()


# ── UNCHANGED ────────────────────────────────────────────────────────────────


class TestUnchangedDocument:
    """A completed document with identical content is skipped."""

    @pytest.mark.asyncio
    async def test_skips_when_hash_matches_and_completed(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()
        mocks["document_repo"].get_document_by_id = AsyncMock(
            return_value=_existing_record("hash-abc", DocumentStatus.COMPLETED)
        )

        result = await pipeline.ingest(_make_file(tmp_path))

        assert result.status is ChangeStatus.UNCHANGED
        assert result.skipped is True
        assert result.chunks_created == 0
        mocks["parser"].parse.assert_not_called()
        mocks["embedder"].embed.assert_not_called()
        mocks["document_repo"].insert_chunks.assert_not_awaited()
        mocks["vector_repo"].store.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_prior_attempt_is_reprocessed_not_skipped(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()
        # same hash but previous attempt did not complete → must re-process
        mocks["document_repo"].get_document_by_id = AsyncMock(
            return_value=_existing_record("hash-abc", DocumentStatus.FAILED)
        )

        result = await pipeline.ingest(_make_file(tmp_path))

        assert result.status is ChangeStatus.MODIFIED
        assert result.skipped is False


# ── MODIFIED (basic; rigorous coverage is Step 7B) ───────────────────────────


class TestModifiedDocument:
    """A completed document whose content changed is re-indexed."""

    @pytest.mark.asyncio
    async def test_deletes_from_both_stores_before_reinsert(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()
        mocks["document_repo"].get_document_by_id = AsyncMock(
            return_value=_existing_record("old-hash", DocumentStatus.COMPLETED)
        )

        result = await pipeline.ingest(_make_file(tmp_path))

        assert result.status is ChangeStatus.MODIFIED
        mocks["document_repo"].delete_chunks_for_document.assert_awaited_once()
        mocks["vector_repo"].delete_for_document.assert_called_once()
        # and it still re-inserts fresh chunks
        mocks["document_repo"].insert_chunks.assert_awaited_once()


# ── Failure handling ─────────────────────────────────────────────────────────


class TestFailureHandling:
    """A mid-pipeline failure marks the document FAILED and re-raises."""

    @pytest.mark.asyncio
    async def test_sets_failed_and_reraises(self, tmp_path: Path) -> None:
        pipeline, mocks = _build_pipeline()
        mocks["chunker"].chunk.side_effect = ChunkingError("bad text")

        with pytest.raises(ChunkingError):
            await pipeline.ingest(_make_file(tmp_path))

        # last status transition must be FAILED
        last_status = mocks["document_repo"].update_status.await_args.args[1]
        assert last_status is DocumentStatus.FAILED
        # nothing was persisted
        mocks["document_repo"].insert_chunks.assert_not_awaited()
        mocks["vector_repo"].store.assert_not_called()
