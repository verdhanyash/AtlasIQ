"""Tests for the retrieval domain models.

Pure value objects — no I/O, no mocks needed (DL-014). Verifies fields,
immutability (frozen), equality, and that ``RetrievedChunk`` correctly wraps a
:class:`ChunkRecord`.
"""

from __future__ import annotations

import dataclasses

import pytest

from atlasiq.backend.domain import ChunkRecord
from atlasiq.retrieval.models import RetrievedChunk, ScoredChunkRef

# ── ScoredChunkRef ───────────────────────────────────────────────────────────


class TestScoredChunkRef:
    """Tests for ScoredChunkRef."""

    def test_holds_all_fields(self) -> None:
        ref = ScoredChunkRef(
            chunk_id="c-1", document_id="d-1", chunk_index=3, score=0.87
        )

        assert ref.chunk_id == "c-1"
        assert ref.document_id == "d-1"
        assert ref.chunk_index == 3
        assert ref.score == 0.87

    def test_is_frozen(self) -> None:
        ref = ScoredChunkRef(
            chunk_id="c-1", document_id="d-1", chunk_index=0, score=1.0
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            ref.score = 2.0  # type: ignore[misc]

    def test_value_equality(self) -> None:
        a = ScoredChunkRef("c-1", "d-1", 0, 0.5)
        b = ScoredChunkRef("c-1", "d-1", 0, 0.5)

        assert a == b


# ── RetrievedChunk ───────────────────────────────────────────────────────────


class TestRetrievedChunk:
    """Tests for RetrievedChunk."""

    @staticmethod
    def _chunk() -> ChunkRecord:
        return ChunkRecord(
            id="c-1",
            document_id="d-1",
            chunk_index=0,
            content="hello world",
            start_page=2,
            end_page=3,
        )

    def test_wraps_chunk_with_filename_and_score(self) -> None:
        rc = RetrievedChunk(chunk=self._chunk(), filename="book.pdf", score=0.9)

        assert rc.chunk.content == "hello world"
        assert rc.chunk.start_page == 2
        assert rc.chunk.end_page == 3
        assert rc.filename == "book.pdf"
        assert rc.score == 0.9

    def test_is_frozen(self) -> None:
        rc = RetrievedChunk(chunk=self._chunk(), filename="book.pdf", score=0.9)

        with pytest.raises(dataclasses.FrozenInstanceError):
            rc.filename = "other.pdf"  # type: ignore[misc]
