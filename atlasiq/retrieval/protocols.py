"""Retrieval abstractions.

Defines the :class:`Retriever` protocol implemented (structurally) by every
retrieval strategy — dense, BM25, hybrid, and future ones (reranking, metadata,
ColBERT/SPLADE, ...). Components such as the hybrid retriever depend on this
abstraction rather than on concrete classes, following the Dependency Inversion
Principle so new retrievers can be added without modifying existing code.

The protocol is structural: `DenseRetriever` and `BM25Retriever` already satisfy
it by having a matching ``retrieve`` method — no explicit inheritance needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from atlasiq.retrieval.models import ScoredChunkRef


class Retriever(Protocol):
    """A component that returns scored chunk references for a question."""

    def retrieve(self, question: str, top_k: int | None = None) -> list[ScoredChunkRef]:
        """Return scored chunk references most relevant to ``question``.

        Args:
            question: The natural-language query.
            top_k: Maximum results to return; ``None`` uses the retriever's
                configured default.

        Returns:
            Scored chunk references in descending relevance order.
        """
        ...
