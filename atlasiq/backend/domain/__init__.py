"""Domain records for AtlasIQ.

Framework-independent dataclasses that describe core entities (documents and
chunks) in AtlasIQ's own vocabulary. These records carry no persistence
behavior, no ORM metadata, and no knowledge of any store — repositories
translate between these records and the underlying databases.
"""

from atlasiq.backend.domain.chunk import ChunkRecord, chunk_id
from atlasiq.backend.domain.document import DocumentRecord, DocumentStatus

__all__ = [
    "ChunkRecord",
    "DocumentRecord",
    "DocumentStatus",
    "chunk_id",
]
