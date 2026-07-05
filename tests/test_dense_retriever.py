"""Tests for the dense (semantic) retriever.

Qdrant and the embedder are fully mocked — no vectors computed, no network,
no model download (DL-014). Verifies query embedding, search delegation,
top-k handling, hit mapping, empty results, and error wrapping.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from atlasiq.backend.core.exceptions import RetrievalError
from atlasiq.retrieval.dense_retriever import DenseRetriever
from atlasiq.retrieval.models import ScoredChunkRef

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_retriever(
    hits: list[dict[str, Any]] | None = None, default_top_k: int = 20
) -> tuple[DenseRetriever, MagicMock, MagicMock]:
    qdrant = MagicMock()
    qdrant.search = MagicMock(return_value=hits if hits is not None else [])
    embedder = MagicMock()
    embedder.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3])
    retriever = DenseRetriever(qdrant, embedder, default_top_k)
    return retriever, qdrant, embedder


def _hit(chunk_id: str, document_id: str, chunk_index: int, score: float) -> dict[str, Any]:
    return {
        "id": chunk_id,
        "score": score,
        "payload": {"document_id": document_id, "chunk_index": chunk_index},
    }


# ── Tests ────────────────────────────────────────────────────────────────────


class TestDenseRetrieve:
    """Tests for DenseRetriever.retrieve."""

    def test_embeds_query_and_searches(self) -> None:
        retriever, qdrant, embedder = _make_retriever(hits=[_hit("c-0", "d-1", 0, 0.9)])

        retriever.retrieve("what is x?")

        embedder.embed_query.assert_called_once_with("what is x?")
        qdrant.search.assert_called_once()

    def test_passes_query_vector_to_search(self) -> None:
        retriever, qdrant, embedder = _make_retriever()
        embedder.embed_query.return_value = [0.5, 0.6]

        retriever.retrieve("q")

        args, _ = qdrant.search.call_args
        assert args[0] == [0.5, 0.6]

    def test_maps_hits_to_scored_refs_in_order(self) -> None:
        retriever, _, _ = _make_retriever(
            hits=[_hit("c-0", "d-1", 0, 0.9), _hit("c-1", "d-1", 1, 0.8)]
        )

        refs = retriever.retrieve("q")

        assert all(isinstance(r, ScoredChunkRef) for r in refs)
        assert refs[0] == ScoredChunkRef("c-0", "d-1", 0, 0.9)
        assert refs[1] == ScoredChunkRef("c-1", "d-1", 1, 0.8)

    def test_uses_default_top_k(self) -> None:
        retriever, qdrant, _ = _make_retriever(default_top_k=15)

        retriever.retrieve("q")

        _, kwargs = qdrant.search.call_args
        assert kwargs["top_k"] == 15

    def test_top_k_override(self) -> None:
        retriever, qdrant, _ = _make_retriever(default_top_k=20)

        retriever.retrieve("q", top_k=5)

        _, kwargs = qdrant.search.call_args
        assert kwargs["top_k"] == 5

    def test_empty_results(self) -> None:
        retriever, _, _ = _make_retriever(hits=[])

        assert retriever.retrieve("q") == []

    def test_qdrant_error_wrapped(self) -> None:
        retriever, qdrant, _ = _make_retriever()
        qdrant.search.side_effect = RuntimeError("boom")

        with pytest.raises(RetrievalError, match="Dense retrieval failed"):
            retriever.retrieve("q")

    def test_malformed_hit_missing_payload_key(self) -> None:
        retriever, _, _ = _make_retriever(
            hits=[{"id": "c-0", "score": 0.9, "payload": {}}]
        )

        with pytest.raises(RetrievalError, match="Malformed Qdrant hit"):
            retriever.retrieve("q")
