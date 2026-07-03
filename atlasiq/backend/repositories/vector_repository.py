"""Qdrant repository for chunk vectors.

Domain-facing wrapper over :class:`QdrantVectorClient`. Speaks in
:class:`ChunkRecord` objects plus their embedding vectors, and owns the shaping
of the Qdrant payload — the pipeline never sees vector-store primitives.

This repository is **ingestion-write-only** for Milestone 1: it stores and
deletes chunk vectors. Similarity search / retrieval is deferred to Milestone 2
(YAGNI). Driver-error wrapping is intentionally *not* done here — that belongs to
the ``database/`` client boundary; this module never imports the qdrant library.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlasiq.backend.core.exceptions import DatabaseQueryError

if TYPE_CHECKING:
    from atlasiq.backend.domain import ChunkRecord
    from atlasiq.database.qdrant_client import QdrantVectorClient

# Payload keys stored alongside each vector. ``document_id`` must match the key
# used by ``QdrantVectorClient.delete_by_document_id`` so filtered deletes work.
# Kept as constants rather than inline strings (no magic strings — DL-002).
_PAYLOAD_DOCUMENT_ID = "document_id"
_PAYLOAD_CHUNK_INDEX = "chunk_index"


class ChunkVectorRepository:
    """Data-access layer for chunk vectors in Qdrant.

    Translates between AtlasIQ :class:`ChunkRecord` domain objects and the
    vector store. Depends on an injected :class:`QdrantVectorClient`.
    """

    def __init__(self, client: QdrantVectorClient) -> None:
        """Initialise the repository.

        Args:
            client: The Qdrant client that owns all vector-store operations.
        """
        self._client = client

    def store(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> None:
        """Upsert chunk vectors into the vector store.

        Each chunk's deterministic id becomes the vector's point id (the join
        key with PostgreSQL), and a minimal payload of ``document_id`` /
        ``chunk_index`` is attached to support filtered deletes and later
        retrieval.

        Args:
            chunks: The chunk records whose vectors are being stored.
            vectors: The embedding vectors, positionally aligned with ``chunks``.
                An empty input is a no-op.

        Raises:
            DatabaseQueryError: If ``chunks`` and ``vectors`` differ in length.
        """
        if len(chunks) != len(vectors):
            msg = (
                "Chunk/vector count mismatch: "
                f"{len(chunks)} chunks but {len(vectors)} vectors"
            )
            raise DatabaseQueryError(msg)

        if not chunks:
            return

        ids = [chunk.id for chunk in chunks]
        payloads: list[dict[str, Any]] = [
            {
                _PAYLOAD_DOCUMENT_ID: chunk.document_id,
                _PAYLOAD_CHUNK_INDEX: chunk.chunk_index,
            }
            for chunk in chunks
        ]

        self._client.upsert_vectors(ids=ids, vectors=vectors, payloads=payloads)

    def delete_for_document(self, document_id: str) -> None:
        """Delete all chunk vectors belonging to a document.

        Used by the re-index path when a document has been modified, before the
        freshly generated vectors are stored.

        Args:
            document_id: The owning document id whose vectors should be removed.
        """
        self._client.delete_by_document_id(document_id)
