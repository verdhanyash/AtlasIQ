"""Tests for the Qdrant chunk vector repository.

The Qdrant client is fully mocked — no real Qdrant, no network (DL-014). The
tests verify id alignment, payload shape, the length-mismatch error, empty-input
no-op behavior, and delete delegation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from atlasiq.backend.core.exceptions import DatabaseQueryError
from atlasiq.backend.domain import ChunkRecord, chunk_id
from atlasiq.backend.repositories.vector_repository import ChunkVectorRepository

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_client() -> MagicMock:
    """Build a mock QdrantVectorClient with the methods the repo delegates to."""
    client = MagicMock()
    client.upsert_vectors = MagicMock()
    client.delete_by_document_id = MagicMock()
    return client


def _chunks(count: int, document_id: str = "doc-1") -> list[ChunkRecord]:
    return [
        ChunkRecord(
            id=chunk_id(document_id, i),
            document_id=document_id,
            chunk_index=i,
            content=f"chunk {i}",
        )
        for i in range(count)
    ]


def _vectors(count: int) -> list[list[float]]:
    return [[float(i), float(i) + 0.5] for i in range(count)]


# ── store ────────────────────────────────────────────────────────────────────


class TestStore:
    """Tests for ChunkVectorRepository.store."""

    def test_delegates_to_upsert_vectors(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)

        repo.store(_chunks(3), _vectors(3))

        client.upsert_vectors.assert_called_once()

    def test_ids_align_with_chunk_ids(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)
        chunks = _chunks(3)

        repo.store(chunks, _vectors(3))

        kwargs = client.upsert_vectors.call_args.kwargs
        assert kwargs["ids"] == [c.id for c in chunks]

    def test_vectors_passed_through_in_order(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)
        vectors = _vectors(3)

        repo.store(_chunks(3), vectors)

        kwargs = client.upsert_vectors.call_args.kwargs
        assert kwargs["vectors"] == vectors

    def test_payload_shape(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)

        repo.store(_chunks(2), _vectors(2))

        kwargs = client.upsert_vectors.call_args.kwargs
        payloads = kwargs["payloads"]
        assert payloads == [
            {"document_id": "doc-1", "chunk_index": 0},
            {"document_id": "doc-1", "chunk_index": 1},
        ]

    def test_length_mismatch_raises(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)

        with pytest.raises(DatabaseQueryError, match="mismatch"):
            repo.store(_chunks(3), _vectors(2))

        client.upsert_vectors.assert_not_called()

    def test_empty_input_is_noop(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)

        repo.store([], [])

        client.upsert_vectors.assert_not_called()


# ── delete_for_document ──────────────────────────────────────────────────────


class TestDeleteForDocument:
    """Tests for ChunkVectorRepository.delete_for_document."""

    def test_delegates_to_client(self) -> None:
        client = _make_client()
        repo = ChunkVectorRepository(client)

        repo.delete_for_document("doc-1")

        client.delete_by_document_id.assert_called_once_with("doc-1")
