"""Chunk domain record.

Defines the ``ChunkRecord`` dataclass and the ``chunk_id`` helper that produces
a deterministic, index-based identifier for a chunk. ``ChunkRecord`` mirrors the
``chunks`` table in ``schema.sql`` but carries no persistence behavior.

``ChunkRecord`` is frozen: once a chunk is produced for a given position in a
document it never mutates. Re-ingestion replaces chunks wholesale (see the
Step 7B re-index path) rather than editing them in place.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# Fixed namespace for deterministic chunk-id generation. Randomly generated
# once and pinned here so that ``chunk_id`` is stable across processes and
# machines — a given (document_id, chunk_index) pair always maps to the same
# UUID. Do not change this value: doing so would orphan every existing chunk id.
_CHUNK_ID_NAMESPACE = uuid.UUID("6f9b1d7c-2a3e-4c1b-9f8a-0d5e7c2b4a11")


def chunk_id(document_id: str, chunk_index: int) -> str:
    """Generate a deterministic identifier for a chunk.

    The id is derived from the document id and the chunk's position within that
    document, so the same ``(document_id, chunk_index)`` pair always yields the
    same id. This makes re-ingestion idempotent: chunk ``#3`` of a document
    always upserts onto the same id rather than creating a duplicate.

    Identity is **positional** — it depends on ``chunk_index``, not on the chunk
    text. If the chunking configuration changes and a document produces a
    different number of chunks, ids realign by index; stale trailing chunks from
    a previous run must be deleted explicitly (handled by the re-index path).

    Args:
        document_id: The stable id of the owning document.
        chunk_index: The zero-based position of the chunk within the document.

    Returns:
        A deterministic UUID string.
    """
    return str(uuid.uuid5(_CHUNK_ID_NAMESPACE, f"{document_id}:{chunk_index}"))


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    """A single chunk of a document.

    Mirrors the ``chunks`` table. Frozen because a chunk is an immutable
    artifact of a particular ingestion — it is never edited in place.

    Attributes:
        id: Deterministic chunk id (see :func:`chunk_id`); join key with the
            vector store.
        document_id: Id of the owning document.
        chunk_index: Zero-based position of the chunk within the document.
        content: The chunk text.
        token_count: Optional token count for the chunk.
        start_page: Optional starting page number (for paginated sources).
        end_page: Optional ending page number (for paginated sources).
        metadata: Free-form metadata dictionary (maps to the ``metadata_json``
            JSONB column).
    """

    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int | None = None
    start_page: int | None = None
    end_page: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
