"""Dense (semantic) retriever backed by Qdrant.

Embeds a natural-language question with the shared embedding model and queries
Qdrant for the nearest chunk vectors. Returns lightweight
:class:`ScoredChunkRef` objects (chunk id + score + document coordinates); the
chunk text and page metadata are hydrated from PostgreSQL later — the Qdrant
payload deliberately stores only ``document_id`` and ``chunk_index`` (the
retrieval → hydration boundary).

Semantic search only. Lexical BM25 is a separate retriever, and combining the
two happens in the hybrid retriever — this component does one thing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from atlasiq.backend.core.exceptions import RetrievalError
from atlasiq.retrieval.models import ScoredChunkRef

if TYPE_CHECKING:
    from atlasiq.database.qdrant_client import QdrantVectorClient
    from atlasiq.ingestion.embedder import DocumentEmbedder

logger = logging.getLogger(__name__)

# Qdrant payload keys written by the vector repository (must match).
_PAYLOAD_DOCUMENT_ID = "document_id"
_PAYLOAD_CHUNK_INDEX = "chunk_index"


class DenseRetriever:
    """Retrieves chunks by semantic similarity via Qdrant.

    Depends on an injected :class:`QdrantVectorClient` (vector search) and
    :class:`DocumentEmbedder` (query embedding). The default result count comes
    from configuration but can be overridden per call.
    """

    def __init__(
        self,
        qdrant_client: QdrantVectorClient,
        embedder: DocumentEmbedder,
        default_top_k: int,
    ) -> None:
        """Initialise the dense retriever.

        Args:
            qdrant_client: The Qdrant client that owns vector search.
            embedder: The embedder used to encode the query (``search_query:``).
            default_top_k: Default number of results when ``top_k`` is omitted.
        """
        self._qdrant = qdrant_client
        self._embedder = embedder
        self._default_top_k = default_top_k

    def retrieve(self, question: str, top_k: int | None = None) -> list[ScoredChunkRef]:
        """Retrieve the most semantically similar chunks for a question.

        Args:
            question: The natural-language query.
            top_k: Maximum results to return; falls back to the configured
                default when ``None``.

        Returns:
            Scored chunk references in descending relevance order.

        Raises:
            EmbeddingError: If the query cannot be embedded.
            RetrievalError: If the vector search fails or returns malformed hits.
        """
        k = top_k if top_k is not None else self._default_top_k

        # Embedding failures raise EmbeddingError (already a domain error) and
        # are allowed to propagate unchanged.
        query_vector = self._embedder.embed_query(question)

        try:
            hits = self._qdrant.search(query_vector, top_k=k)
        except Exception as exc:
            msg = f"Dense retrieval failed: {exc}"
            raise RetrievalError(msg) from exc

        refs = [self._to_ref(hit) for hit in hits]
        logger.info("Dense retrieval returned %d chunks", len(refs))
        return refs

    @staticmethod
    def _to_ref(hit: dict[str, Any]) -> ScoredChunkRef:
        """Map a raw Qdrant hit to a :class:`ScoredChunkRef`.

        Args:
            hit: A search hit dict with keys ``id``, ``score``, ``payload``.

        Returns:
            The scored chunk reference.

        Raises:
            RetrievalError: If the hit's payload is missing required keys.
        """
        payload = hit.get("payload", {})
        try:
            return ScoredChunkRef(
                chunk_id=str(hit["id"]),
                document_id=payload[_PAYLOAD_DOCUMENT_ID],
                chunk_index=payload[_PAYLOAD_CHUNK_INDEX],
                score=float(hit["score"]),
            )
        except KeyError as exc:
            msg = f"Malformed Qdrant hit missing key {exc}"
            raise RetrievalError(msg) from exc
