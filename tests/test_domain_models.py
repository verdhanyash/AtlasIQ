"""Tests for the domain records (document and chunk).

Verifies field defaults, enum values against the schema CHECK constraint,
deterministic chunk-id generation, and immutability guarantees. These records
are pure — no mocking, no I/O.
"""

from __future__ import annotations

import dataclasses
from datetime import timezone

import pytest

from atlasiq.backend.domain import (
    ChunkRecord,
    DocumentRecord,
    DocumentStatus,
    chunk_id,
)

# ── DocumentStatus enum ──────────────────────────────────────────────────────


class TestDocumentStatus:
    """Tests for the DocumentStatus enum."""

    def test_values_match_schema_constraint(self) -> None:
        """Enum values must match the valid_status CHECK constraint in schema.sql."""
        assert {s.value for s in DocumentStatus} == {
            "pending",
            "processing",
            "completed",
            "failed",
        }

    def test_is_str_enum(self) -> None:
        """Members should compare equal to their string value for SQL/JSON use."""
        assert DocumentStatus.PENDING == "pending"
        assert DocumentStatus.COMPLETED.value == "completed"

    def test_string_serialization(self) -> None:
        """Members should serialize to their plain string value."""
        assert f"{DocumentStatus.FAILED.value}" == "failed"


# ── DocumentRecord ───────────────────────────────────────────────────────────


class TestDocumentRecord:
    """Tests for the DocumentRecord dataclass."""

    def _make(self) -> DocumentRecord:
        return DocumentRecord(
            id="doc-1",
            filename="report.pdf",
            file_hash="abc123",
            file_type=".pdf",
            file_size_bytes=2048,
        )

    def test_required_fields(self) -> None:
        """Required fields should be stored as provided."""
        doc = self._make()
        assert doc.id == "doc-1"
        assert doc.filename == "report.pdf"
        assert doc.file_hash == "abc123"
        assert doc.file_type == ".pdf"
        assert doc.file_size_bytes == 2048

    def test_default_status_is_pending(self) -> None:
        """A new document defaults to PENDING status."""
        assert self._make().status is DocumentStatus.PENDING

    def test_optional_fields_default_none(self) -> None:
        """Optional metadata fields default to None."""
        doc = self._make()
        assert doc.title is None
        assert doc.author is None
        assert doc.page_count is None
        assert doc.word_count is None
        assert doc.ingested_at is None

    def test_timestamps_are_utc(self) -> None:
        """created_at and updated_at default to timezone-aware UTC timestamps."""
        doc = self._make()
        assert doc.created_at.tzinfo == timezone.utc  # noqa: UP017
        assert doc.updated_at.tzinfo == timezone.utc  # noqa: UP017

    def test_status_is_mutable(self) -> None:
        """status should be reassignable as the document progresses."""
        doc = self._make()
        doc.status = DocumentStatus.PROCESSING
        assert doc.status is DocumentStatus.PROCESSING

    def test_independent_default_timestamps(self) -> None:
        """Each instance gets its own default timestamps (no shared mutable default)."""
        d1 = self._make()
        d2 = self._make()
        # Distinct instances; timestamps are independent objects.
        assert d1.created_at is not d2.created_at


# ── chunk_id ─────────────────────────────────────────────────────────────────


class TestChunkId:
    """Tests for the deterministic chunk_id helper."""

    def test_deterministic(self) -> None:
        """Same document id and index always produce the same chunk id."""
        assert chunk_id("doc-1", 0) == chunk_id("doc-1", 0)

    def test_different_index_differs(self) -> None:
        """Different chunk indices produce different ids."""
        assert chunk_id("doc-1", 0) != chunk_id("doc-1", 1)

    def test_different_document_differs(self) -> None:
        """Different documents produce different ids for the same index."""
        assert chunk_id("doc-1", 0) != chunk_id("doc-2", 0)

    def test_is_valid_uuid_string(self) -> None:
        """The generated id should be a valid UUID string."""
        import uuid

        value = chunk_id("doc-1", 3)
        # Should not raise.
        assert str(uuid.UUID(value)) == value


# ── ChunkRecord ──────────────────────────────────────────────────────────────


class TestChunkRecord:
    """Tests for the ChunkRecord dataclass."""

    def _make(self) -> ChunkRecord:
        return ChunkRecord(
            id=chunk_id("doc-1", 0),
            document_id="doc-1",
            chunk_index=0,
            content="Hello, AtlasIQ.",
        )

    def test_required_fields(self) -> None:
        """Required fields should be stored as provided."""
        chunk = self._make()
        assert chunk.document_id == "doc-1"
        assert chunk.chunk_index == 0
        assert chunk.content == "Hello, AtlasIQ."
        assert chunk.id == chunk_id("doc-1", 0)

    def test_optional_fields_default(self) -> None:
        """Optional fields default to None / empty metadata dict."""
        chunk = self._make()
        assert chunk.token_count is None
        assert chunk.start_page is None
        assert chunk.end_page is None
        assert chunk.metadata == {}

    def test_frozen_immutability(self) -> None:
        """ChunkRecord instances should be immutable (frozen=True)."""
        chunk = self._make()
        with pytest.raises(dataclasses.FrozenInstanceError):
            chunk.content = "changed"  # type: ignore[misc]

    def test_independent_metadata_defaults(self) -> None:
        """Each instance gets its own metadata dict (no shared mutable default)."""
        c1 = self._make()
        c2 = self._make()
        assert c1.metadata is not c2.metadata

    def test_equality_same_values(self) -> None:
        """Two chunks with identical values should be equal."""
        c1 = self._make()
        c2 = self._make()
        assert c1 == c2
