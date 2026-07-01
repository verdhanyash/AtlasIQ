"""Tests for the PostgreSQL document repository.

All database interaction is mocked — no real PostgreSQL, no network (DL-014).
The tests verify SQL parameter binding, domain-record mapping, transaction
commits, and that driver errors are wrapped in ``DatabaseQueryError``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from atlasiq.backend.core.exceptions import DatabaseQueryError
from atlasiq.backend.domain import ChunkRecord, DocumentRecord, DocumentStatus, chunk_id
from atlasiq.backend.repositories.document_repository import DocumentRepository

# ── Fixtures / helpers ───────────────────────────────────────────────────────


class _FakeResult:
    """Stand-in for a SQLAlchemy Result supporting .mappings().first()/.all()."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _FakeResult:
        return self

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows


def _make_session(result: _FakeResult | None = None) -> MagicMock:
    """Build a mock AsyncSession usable as an async context manager."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    # async context manager protocol
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _make_client(session: MagicMock) -> MagicMock:
    """Build a mock PostgresClient whose session_factory() returns the session."""
    client = MagicMock()
    client.session_factory = MagicMock(return_value=session)
    return client


def _sample_document() -> DocumentRecord:
    return DocumentRecord(
        id="doc-1",
        filename="report.pdf",
        file_hash="hash-abc",
        file_type=".pdf",
        file_size_bytes=1024,
        status=DocumentStatus.PENDING,
    )


def _sample_row() -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "id": "doc-1",
        "filename": "report.pdf",
        "file_hash": "hash-abc",
        "file_type": ".pdf",
        "file_size_bytes": 1024,
        "status": "completed",
        "title": "A Title",
        "author": "An Author",
        "page_count": 10,
        "word_count": 500,
        "created_at": now,
        "updated_at": now,
        "ingested_at": now,
    }


# ── upsert_document ──────────────────────────────────────────────────────────


class TestUpsertDocument:
    """Tests for upsert_document."""

    @pytest.mark.asyncio
    async def test_executes_and_commits(self) -> None:
        session = _make_session()
        repo = DocumentRepository(_make_client(session))

        await repo.upsert_document(_sample_document())

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_binds_status_as_string_value(self) -> None:
        session = _make_session()
        repo = DocumentRepository(_make_client(session))

        await repo.upsert_document(_sample_document())

        _, params = session.execute.await_args.args
        assert params["status"] == "pending"
        assert params["id"] == "doc-1"
        assert params["file_hash"] == "hash-abc"

    @pytest.mark.asyncio
    async def test_wraps_driver_error(self) -> None:
        session = _make_session()
        session.execute.side_effect = SQLAlchemyError("boom")
        repo = DocumentRepository(_make_client(session))

        with pytest.raises(DatabaseQueryError, match="Failed to upsert document"):
            await repo.upsert_document(_sample_document())


# ── get_document_by_id / by_hash ─────────────────────────────────────────────


class TestGetDocument:
    """Tests for get_document_by_id and get_document_by_hash."""

    @pytest.mark.asyncio
    async def test_get_by_id_maps_row(self) -> None:
        session = _make_session(_FakeResult([_sample_row()]))
        repo = DocumentRepository(_make_client(session))

        doc = await repo.get_document_by_id("doc-1")

        assert doc is not None
        assert doc.id == "doc-1"
        assert doc.status is DocumentStatus.COMPLETED
        assert doc.title == "A Title"
        assert doc.page_count == 10

    @pytest.mark.asyncio
    async def test_get_by_id_not_found_returns_none(self) -> None:
        session = _make_session(_FakeResult([]))
        repo = DocumentRepository(_make_client(session))

        assert await repo.get_document_by_id("missing") is None

    @pytest.mark.asyncio
    async def test_get_by_hash_binds_param(self) -> None:
        session = _make_session(_FakeResult([_sample_row()]))
        repo = DocumentRepository(_make_client(session))

        doc = await repo.get_document_by_hash("hash-abc")

        assert doc is not None
        _, params = session.execute.await_args.args
        assert params["file_hash"] == "hash-abc"

    @pytest.mark.asyncio
    async def test_get_by_hash_not_found_returns_none(self) -> None:
        session = _make_session(_FakeResult([]))
        repo = DocumentRepository(_make_client(session))

        assert await repo.get_document_by_hash("nope") is None

    @pytest.mark.asyncio
    async def test_get_wraps_driver_error(self) -> None:
        session = _make_session()
        session.execute.side_effect = SQLAlchemyError("boom")
        repo = DocumentRepository(_make_client(session))

        with pytest.raises(DatabaseQueryError):
            await repo.get_document_by_id("doc-1")


# ── update_status ────────────────────────────────────────────────────────────


class TestUpdateStatus:
    """Tests for update_status."""

    @pytest.mark.asyncio
    async def test_binds_status_and_id(self) -> None:
        session = _make_session()
        repo = DocumentRepository(_make_client(session))

        await repo.update_status("doc-1", DocumentStatus.PROCESSING)

        _, params = session.execute.await_args.args
        assert params["status"] == "processing"
        assert params["id"] == "doc-1"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wraps_driver_error(self) -> None:
        session = _make_session()
        session.execute.side_effect = SQLAlchemyError("boom")
        repo = DocumentRepository(_make_client(session))

        with pytest.raises(DatabaseQueryError, match="Failed to update status"):
            await repo.update_status("doc-1", DocumentStatus.FAILED)


# ── insert_chunks ────────────────────────────────────────────────────────────


class TestInsertChunks:
    """Tests for insert_chunks."""

    def _chunks(self) -> list[ChunkRecord]:
        return [
            ChunkRecord(
                id=chunk_id("doc-1", i),
                document_id="doc-1",
                chunk_index=i,
                content=f"chunk {i}",
                metadata={"k": i},
            )
            for i in range(3)
        ]

    @pytest.mark.asyncio
    async def test_empty_list_is_noop(self) -> None:
        session = _make_session()
        repo = DocumentRepository(_make_client(session))

        await repo.insert_chunks([])

        session.execute.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_inserts_all_chunks_with_serialized_metadata(self) -> None:
        session = _make_session()
        repo = DocumentRepository(_make_client(session))

        await repo.insert_chunks(self._chunks())

        _, params = session.execute.await_args.args
        assert isinstance(params, list)
        assert len(params) == 3
        # metadata must be JSON-serialized to a string for the JSONB cast
        assert params[0]["metadata_json"] == '{"k": 0}'
        assert params[2]["chunk_index"] == 2
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wraps_driver_error(self) -> None:
        session = _make_session()
        session.execute.side_effect = SQLAlchemyError("boom")
        repo = DocumentRepository(_make_client(session))

        with pytest.raises(DatabaseQueryError, match="Failed to insert"):
            await repo.insert_chunks(self._chunks())


# ── delete_chunks_for_document ───────────────────────────────────────────────


class TestDeleteChunks:
    """Tests for delete_chunks_for_document."""

    @pytest.mark.asyncio
    async def test_binds_document_id_and_commits(self) -> None:
        session = _make_session()
        repo = DocumentRepository(_make_client(session))

        await repo.delete_chunks_for_document("doc-1")

        _, params = session.execute.await_args.args
        assert params["document_id"] == "doc-1"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wraps_driver_error(self) -> None:
        session = _make_session()
        session.execute.side_effect = SQLAlchemyError("boom")
        repo = DocumentRepository(_make_client(session))

        with pytest.raises(DatabaseQueryError, match="Failed to delete chunks"):
            await repo.delete_chunks_for_document("doc-1")


# ── list_documents ───────────────────────────────────────────────────────────


class TestListDocuments:
    """Tests for list_documents."""

    @pytest.mark.asyncio
    async def test_maps_rows(self) -> None:
        session = _make_session(_FakeResult([_sample_row(), _sample_row()]))
        repo = DocumentRepository(_make_client(session))

        docs = await repo.list_documents()

        assert len(docs) == 2
        assert all(isinstance(d, DocumentRecord) for d in docs)

    @pytest.mark.asyncio
    async def test_default_limit_and_offset(self) -> None:
        session = _make_session(_FakeResult([]))
        repo = DocumentRepository(_make_client(session))

        await repo.list_documents()

        _, params = session.execute.await_args.args
        assert params["limit"] == 50
        assert params["offset"] == 0

    @pytest.mark.asyncio
    async def test_custom_limit_and_offset(self) -> None:
        session = _make_session(_FakeResult([]))
        repo = DocumentRepository(_make_client(session))

        await repo.list_documents(limit=10, offset=20)

        _, params = session.execute.await_args.args
        assert params["limit"] == 10
        assert params["offset"] == 20

    @pytest.mark.asyncio
    async def test_wraps_driver_error(self) -> None:
        session = _make_session()
        session.execute.side_effect = SQLAlchemyError("boom")
        repo = DocumentRepository(_make_client(session))

        with pytest.raises(DatabaseQueryError, match="Failed to list documents"):
            await repo.list_documents()
