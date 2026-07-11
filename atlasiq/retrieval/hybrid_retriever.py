"""Hybrid retriever combining multiple retrievers via Reciprocal Rank Fusion.

Depends on the :class:`Retriever` protocol (not concrete classes), so any
retrieval strategy — dense, BM25, and future ones (reranking, metadata,
ColBERT/SPLADE) — can be fused without modifying this class (Dependency
Inversion / Open–Closed).

Reciprocal Rank Fusion (RRF) combines ranked lists using only their **ranks**
(not raw scores), so retrievers with incomparable score scales (cosine
similarity vs BM25) merge fairly: ``rrf_score(chunk) = Σ 1 / (rrf_k + rank_i)``
over each list the chunk appears in. Each input retriever controls its own
candidate pool (e.g. dense_top_k / bm25_top_k); this class only fuses those
outputs and applies the final ``top_k``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlasiq.retrieval.models import ScoredChunkRef

if TYPE_CHECKING:
    from collections.abc import Sequence

    from atlasiq.retrieval.protocols import Retriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Fuses several retrievers' results with Reciprocal Rank Fusion.

    Accepts any objects implementing the :class:`Retriever` protocol, so it
    generalises beyond dense + BM25 to any number of retrievers without change.
    """

    def __init__(
        self,
        retrievers: Sequence[Retriever],
        rrf_k: int,
        default_top_k: int,
    ) -> None:
        """Initialise the hybrid retriever.

        Args:
            retrievers: The retrievers whose results are fused (each controls
                its own candidate pool). Typically the dense and BM25 retrievers.
                Must contain at least one retriever.
            rrf_k: The RRF constant (dampens the contribution of lower ranks).
            default_top_k: Final result count when ``top_k`` is omitted.

        Raises:
            ValueError: If ``retrievers`` is empty (fail fast rather than
                silently returning no results).
        """
        if not retrievers:
            raise ValueError("HybridRetriever requires at least one retriever.")

        self._retrievers = list(retrievers)
        self._rrf_k = rrf_k
        self._default_top_k = default_top_k

    def retrieve(self, question: str, top_k: int | None = None) -> list[ScoredChunkRef]:
        """Retrieve, fuse, and return the top chunks for a question.

        Orchestration only: (1) gather each retriever's candidates, (2) fuse
        their rankings via RRF, (3) return the final ``top_k``.

        Args:
            question: The natural-language query.
            top_k: Final result count; falls back to the configured default.

        Returns:
            Fused scored chunk references (RRF score) in descending order.
        """
        candidate_lists = [retriever.retrieve(question) for retriever in self._retrievers]
        fused = self._fuse_rrf(candidate_lists)
        k = top_k if top_k is not None else self._default_top_k

        logger.info(
            "Hybrid retrieval fused %d lists into %d unique chunks (returning %d)",
            len(candidate_lists),
            len(fused),
            min(k, len(fused)),
        )
        return fused[:k]

    def _fuse_rrf(
        self, ranked_lists: Sequence[Sequence[ScoredChunkRef]]
    ) -> list[ScoredChunkRef]:
        """Fuse ranked lists with Reciprocal Rank Fusion.

        Each chunk's fused score is the sum of ``1 / (rrf_k + rank)`` over every
        list it appears in (1-based ranks). Chunks appearing in multiple lists
        are deduplicated by ``chunk_id`` and accumulate one contribution per
        list. Results are ordered by ``(-rrf_score, document_id, chunk_index)``
        — deterministic and reflecting document structure rather than arbitrary
        UUID order.

        Args:
            ranked_lists: One ranked list of references per retriever.

        Returns:
            The fused, ordered list of scored chunk references.
        """
        fused_scores: dict[str, float] = {}
        coordinates: dict[str, ScoredChunkRef] = {}

        for ranked in ranked_lists:
            for rank, ref in enumerate(ranked, start=1):
                fused_scores[ref.chunk_id] = (
                    fused_scores.get(ref.chunk_id, 0.0) + 1.0 / (self._rrf_k + rank)
                )
                coordinates.setdefault(ref.chunk_id, ref)

        fused = [
            ScoredChunkRef(
                chunk_id=chunk_id,
                document_id=coordinates[chunk_id].document_id,
                chunk_index=coordinates[chunk_id].chunk_index,
                score=score,
            )
            for chunk_id, score in fused_scores.items()
        ]
        fused.sort(key=lambda ref: (-ref.score, ref.document_id, ref.chunk_index))
        return fused
