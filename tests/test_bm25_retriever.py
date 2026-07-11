"""Tests for the BM25 lexical retriever.

Fully offline (DL-014): chunks are injected directly — no database, no Docker,
no network. Verifies indexing, lexical ranking, ScoredChunkRef mapping, top-k
handling, zero-score exclusion, state (never-indexed vs empty), edge cases, and
deterministic ordering.
"""

from __future__ import annotations

import pytest

from atlasiq.backend.core.exceptions import RetrievalError
from atlasiq.backend.domain import ChunkRecord
from atlasiq.retrieval.bm25_retriever import BM25Retriever
from atlasiq.retrieval.models import ScoredChunkRef

# ── Helpers ──────────────────────────────────────────────────────────────────


def _chunk(chunk_id: str, chunk_index: int, content: str, document_id: str = "d-1") -> ChunkRecord:
    return ChunkRecord(
        id=chunk_id,
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
    )


def _fox_corpus() -> list[ChunkRecord]:
    """Corpus where query terms 'quick'/'fox' are a minority (positive IDF)."""
    return [
        _chunk("c-0", 0, "quick fox runs across the field"),
        _chunk("c-1", 1, "the fox sleeps quietly"),
        _chunk("c-2", 2, "a lazy dog barks loudly"),
        _chunk("c-3", 3, "the sun shines bright today"),
        _chunk("c-4", 4, "cat and mouse play together"),
    ]


# ── Normal retrieval + ranking ───────────────────────────────────────────────


class TestRetrieval:
    def test_normal_retrieval_returns_matches(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(_fox_corpus())

        results = retriever.retrieve("quick fox")

        ids = [r.chunk_id for r in results]
        assert "c-0" in ids  # has both terms
        assert "c-1" in ids  # has 'fox'
        # non-matching chunks excluded
        assert "c-2" not in ids
        assert "c-3" not in ids
        assert "c-4" not in ids

    def test_lexical_ranking_more_matches_first(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(_fox_corpus())

        results = retriever.retrieve("quick fox")

        # c-0 (both 'quick' and 'fox') must outrank c-1 (only 'fox')
        assert results[0].chunk_id == "c-0"
        assert results[1].chunk_id == "c-1"

    def test_higher_term_frequency_ranks_higher(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(
            [
                _chunk("c-0", 0, "data science"),
                _chunk("c-1", 1, "data data data science methods"),
                _chunk("c-2", 2, "unrelated filler content one"),
                _chunk("c-3", 3, "unrelated filler content two"),
                _chunk("c-4", 4, "unrelated filler content three"),
            ]
        )

        results = retriever.retrieve("data")

        assert [r.chunk_id for r in results] == ["c-1", "c-0"]
        assert results[0].score > results[1].score

    def test_scored_chunk_ref_mapping(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        # 'unique' must be a minority term (positive IDF), so add filler docs.
        retriever.index(
            [
                _chunk("c-9", 7, "unique lexical token", document_id="doc-42"),
                _chunk("f-0", 0, "filler alpha content"),
                _chunk("f-1", 1, "filler beta content"),
                _chunk("f-2", 2, "filler gamma content"),
            ]
        )

        results = retriever.retrieve("unique")

        assert len(results) == 1
        ref = results[0]
        assert isinstance(ref, ScoredChunkRef)
        assert ref.chunk_id == "c-9"
        assert ref.document_id == "doc-42"
        assert ref.chunk_index == 7
        assert ref.score > 0.0


# ── top_k handling ───────────────────────────────────────────────────────────


class TestTopK:
    @staticmethod
    def _alpha_corpus() -> list[ChunkRecord]:
        # 'alpha' present in 3 of 7 docs → minority → positive IDF.
        return [
            _chunk("a-0", 0, "alpha one"),
            _chunk("a-1", 1, "alpha two"),
            _chunk("a-2", 2, "alpha three"),
            _chunk("f-0", 3, "filler aaa"),
            _chunk("f-1", 4, "filler bbb"),
            _chunk("f-2", 5, "filler ccc"),
            _chunk("f-3", 6, "filler ddd"),
        ]

    def test_default_top_k_limits_results(self) -> None:
        retriever = BM25Retriever(default_top_k=2)
        retriever.index(self._alpha_corpus())

        results = retriever.retrieve("alpha")

        assert len(results) == 2  # 3 positive matches, capped at default_top_k

    def test_override_top_k(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(self._alpha_corpus())

        results = retriever.retrieve("alpha", top_k=1)

        assert len(results) == 1


# ── Zero-overlap / empty query ───────────────────────────────────────────────


class TestNoResults:
    def test_zero_overlap_query_returns_empty(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(_fox_corpus())

        assert retriever.retrieve("nonexistentterm") == []

    def test_empty_query_returns_empty(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(_fox_corpus())

        assert retriever.retrieve("") == []

    def test_whitespace_query_returns_empty(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(_fox_corpus())

        assert retriever.retrieve("   \t\n  ") == []


# ── State: never indexed vs empty corpus ─────────────────────────────────────


class TestState:
    def test_retrieve_before_index_raises(self) -> None:
        retriever = BM25Retriever(default_top_k=10)

        with pytest.raises(RetrievalError, match="not built"):
            retriever.retrieve("anything")

    def test_empty_corpus_returns_empty(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index([])

        assert retriever.retrieve("anything") == []

    def test_reindex_replaces_corpus(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        filler = [
            _chunk("f-0", 1, "filler one"),
            _chunk("f-1", 2, "filler two"),
            _chunk("f-2", 3, "filler three"),
        ]
        retriever.index([_chunk("old-0", 0, "apple orange"), *filler])
        assert [r.chunk_id for r in retriever.retrieve("apple")] == ["old-0"]

        retriever.index([_chunk("new-0", 0, "banana grape"), *filler])

        # old corpus is gone; 'apple' no longer matches, 'banana' does
        assert retriever.retrieve("apple") == []
        assert [r.chunk_id for r in retriever.retrieve("banana")] == ["new-0"]


# ── Determinism ──────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_ties_broken_by_corpus_position(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        # identical content → identical scores → tie broken by corpus position
        retriever.index(
            [
                _chunk("c-0", 0, "apple apple"),
                _chunk("c-1", 1, "apple apple"),
                _chunk("f-0", 2, "zzz filler one"),
                _chunk("f-1", 3, "zzz filler two"),
                _chunk("f-2", 4, "zzz filler three"),
            ]
        )

        results = retriever.retrieve("apple")

        assert [r.chunk_id for r in results] == ["c-0", "c-1"]

    def test_repeated_queries_are_stable(self) -> None:
        retriever = BM25Retriever(default_top_k=10)
        retriever.index(_fox_corpus())

        first = [r.chunk_id for r in retriever.retrieve("quick fox")]
        second = [r.chunk_id for r in retriever.retrieve("quick fox")]

        assert first == second
