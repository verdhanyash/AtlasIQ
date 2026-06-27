"""Qdrant vector database client for AtlasIQ.

Manages collection creation, vector upsert, similarity search, and deletion.
All Qdrant-specific logic is encapsulated here — no other module imports
the qdrant_client library directly.
"""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from atlasiq.backend.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


class QdrantVectorClient:
    """Client for Qdrant vector database operations.

    Wraps the official qdrant_client library and provides AtlasIQ-specific
    methods for collection management, vector storage, and similarity search.

    Attributes:
        client: The underlying qdrant_client instance.
        collection_name: Name of the vector collection.
        vector_size: Dimensionality of the embedding vectors.
    """

    def __init__(self, host: str, port: int, collection_name: str, vector_size: int) -> None:
        """Initialize the Qdrant client.

        Args:
            host: Qdrant server hostname.
            port: Qdrant server port.
            collection_name: Name of the collection to use.
            vector_size: Dimensionality of the vectors (must match embedding model).
        """
        self.client = _QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        logger.info(
            "Qdrant client initialized: host=%s, port=%d, collection=%s",
            host, port, collection_name,
        )

    def ensure_collection(self) -> None:
        """Create the vector collection if it does not already exist.

        Uses cosine distance for similarity, matching Nomic Embed's output space.
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", self.collection_name)
        else:
            logger.info("Qdrant collection already exists: %s", self.collection_name)

    def upsert_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict] | None = None,
    ) -> None:
        """Insert or update vectors in the collection.

        Args:
            ids: Unique identifiers for each vector (typically chunk IDs).
            vectors: Embedding vectors to store.
            payloads: Optional metadata payloads associated with each vector.
        """
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload or {},
            )
            for point_id, vector, payload in zip(
                ids, vectors, payloads or [{}] * len(ids), strict=True
            )
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("Upserted %d vectors into Qdrant", len(points))

    def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        score_threshold: float | None = None,
    ) -> list[dict]:
        """Search for similar vectors using cosine similarity.

        Args:
            query_vector: The query embedding vector.
            top_k: Maximum number of results to return.
            score_threshold: Minimum similarity score to include in results.

        Returns:
            List of result dicts with keys: id, score, payload.
        """
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all vectors associated with a document.

        Used during re-indexing to remove stale chunks before inserting
        updated ones.

        Args:
            document_id: The document ID whose chunks should be removed.
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
        logger.info("Deleted vectors for document_id=%s from Qdrant", document_id)

    def health_check(self) -> bool:
        """Check if Qdrant is reachable and the collection exists.

        Returns:
            True if Qdrant responds and the collection is accessible.
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return info is not None
        except UnexpectedResponse:
            # Collection doesn't exist yet — that's OK for health check
            # as long as the server is reachable
            try:
                self.client.get_collections()
                return True
            except Exception:
                logger.exception("Qdrant health check failed")
                return False
        except Exception:
            logger.exception("Qdrant health check failed")
            return False

    def close(self) -> None:
        """Close the Qdrant client connection."""
        self.client.close()
        logger.info("Qdrant client connection closed")
