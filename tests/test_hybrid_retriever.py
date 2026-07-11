"""Tests for the hybrid retriever (Reciprocal Rank Fusion).

Fully offline (DL-014): the input retrievers are simple stubs implementing the
``Retriever`` protocol, returning preset ranked lists. Verifies exact RRF
scoring, deduplication, overlap boosting, deterministic ordering, empty-input
handling, top-k, and N-retriever generalisation.
"""

from __future__ import annotations

import math

import pytest

from atlasiq.retrieval.hybrid_retriever import HybridRetriever
from atlasiq.retrieval.models import ScoredChunkRef

_RRF_K = 60

# ── Helpers ──────────────────────────────────────────────────────────────────


class _StubRetriever:
    """Minimal object satisfying the Retriever protocol for tests."""

    def __init__(self, results: list[ScoredChunkRef]) -> None:
        self._results = results

    def retrieve(self, question: str, top_k: int | None = None) -> list[ScoredChunkRef]:
        return list(self._results)


def _ref(chunk_id: str, document_id: str = "d-1", chunk_index: int = 0) -> ScoredChunkRef:
    # The incoming score is irrelevant to RRF (rank-based); default it to 0.0.
    return ScoredChunkRef(chunk_id=chunk_id, document_id=document_id, chunk_index=chunk_index, score=0.0)


def _rrf(*ranks: int) -> float:
    """Expected RRF score contributed at the given 1-based ranks."""
    return sum(1.0 / (_RRF_K + rank) for rank in ranks)


def _hybrid(*result_lists: list[ScoredChunkRef], default_top_k: int = 10) -> HybridRetriever:
    return HybridRetriever(
        retrievers=[_StubRetriever(results) for results in result_lists],
        rrf_k=_RRF_K,
        default_top_k=default_top_k,
    )


def _by_id(results: list[ScoredChunkRef]) -> dict[str, ScoredChunkRef]:
    return {r.chunk_id: r for r in results}


# ── Constructor validation ───────────────────────────────────────────────────


class TestConstructorValidation:
    def test_empty_retrievers_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one retriever"):
            HybridRetriever(retrievers=[], rrf_k=_RRF_K, default_top_k=10)

    def test_single_retriever_is_allowed(self) -> None:
        hybrid = HybridRetriever(
            retrievers=[_StubRetriever([_ref("A")])], rrf_k=_RRF_K, default_top_k=10
        )

        assert [r.chunk_id for r in hybrid.retrieve("q")] == ["A"]


# ── Core RRF + deduplication ─────────────────────────────────────────────────


class TestFusion:
    def test_exact_rrf_scoring_and_dedup(self) -> None:
        # Dense: A B C   BM25: B A   (A and B appear in both → dedup + summed)
        dense = [_ref("A", chunk_index=0), _ref("B", chunk_index=1), _ref("C", chunk_index=2)]
        bm25 = [_ref("B", chunk_index=1), _ref("A", chunk_index=0)]

        results = _hybrid(dense, bm25).retrieve("q")

        # Each chunk appears exactly once (deduplicated)
        assert [r.chunk_id for r in results] == ["A", "B", "C"]
        scored = _by_id(results)
        # A: dense rank1 + bm25 rank2 ; B: dense rank2 + bm25 rank1 (equal to A)
        assert math.isclose(scored["A"].score, _rrf(1, 2))
        assert math.isclose(scored["B"].score, _rrf(2, 1))
        assert math.isclose(scored["C"].score, _rrf(3))
        # A and B tie on score; tie broken by (document_id, chunk_index) → A before B
        assert math.isclose(scored["A"].score, scored["B"].score)

    def test_overlap_boosts_rank(self) -> None:
        # A appears in both lists (rank1 each) → should outrank X (single list)
        dense = [_ref("A"), _ref("X", chunk_index=1)]
        bm25 = [_ref("A")]

        results = _hybrid(dense, bm25).retrieve("q")

        assert results[0].chunk_id == "A"
        assert math.isclose(_by_id(results)["A"].score, _rrf(1, 1))
        assert math.isclose(_by_id(results)["X"].score, _rrf(2))


# ── Deterministic ordering ───────────────────────────────────────────────────


class TestDeterministicOrdering:
    def test_tie_broken_by_document_id(self) -> None:
        # P and Q both rank1 in their single list → equal RRF; different docs
        dense = [_ref("P", document_id="d-2", chunk_index=5)]
        bm25 = [_ref("Q", document_id="d-1", chunk_index=0)]

        results = _hybrid(dense, bm25).retrieve("q")

        # equal scores → ordered by document_id ("d-1" before "d-2")
        assert [r.chunk_id for r in results] == ["Q", "P"]

    def test_tie_broken_by_chunk_index_within_document(self) -> None:
        dense = [_ref("M", document_id="d-1", chunk_index=3)]
        bm25 = [_ref("N", document_id="d-1", chunk_index=1)]

        results = _hybrid(dense, bm25).retrieve("q")

        # equal scores, same document → ordered by chunk_index (1 before 3)
        assert [r.chunk_id for r in results] == ["N", "M"]


# ── Empty inputs ─────────────────────────────────────────────────────────────


class TestEmptyInputs:
    def test_one_list_empty(self) -> None:
        dense = [_ref("A", chunk_index=0), _ref("B", chunk_index=1)]
        results = _hybrid(dense, []).retrieve("q")

        assert [r.chunk_id for r in results] == ["A", "B"]

    def test_all_lists_empty(self) -> None:
        assert _hybrid([], []).retrieve("q") == []


# ── top_k handling ───────────────────────────────────────────────────────────


class TestTopK:
    def test_default_top_k(self) -> None:
        dense = [_ref("A", chunk_index=0), _ref("B", chunk_index=1), _ref("C", chunk_index=2)]
        results = _hybrid(dense, default_top_k=2).retrieve("q")

        assert len(results) == 2

    def test_override_top_k(self) -> None:
        dense = [_ref("A", chunk_index=0), _ref("B", chunk_index=1), _ref("C", chunk_index=2)]
        results = _hybrid(dense, default_top_k=10).retrieve("q", top_k=1)

        assert len(results) == 1


# ── Extensibility (Dependency Inversion) ─────────────────────────────────────


class TestGeneralisesToNRetrievers:
    def test_three_retrievers_fuse(self) -> None:
        # A is rank1 in all three lists → accumulates three contributions
        r1 = [_ref("A"), _ref("B", chunk_index=1)]
        r2 = [_ref("A")]
        r3 = [_ref("A")]

        results = _hybrid(r1, r2, r3).retrieve("q")

        assert results[0].chunk_id == "A"
        assert math.isclose(_by_id(results)["A"].score, _rrf(1, 1, 1))
