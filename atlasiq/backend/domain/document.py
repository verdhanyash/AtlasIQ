"""Document domain record.

Defines the ``DocumentRecord`` dataclass and the ``DocumentStatus`` enum that
describe a document as AtlasIQ understands it. These mirror the columns of the
``documents`` table in ``schema.sql`` but carry no persistence behavior — they
are the shared vocabulary passed between the pipeline and the repository layer.

``DocumentRecord`` is intentionally mutable: a document's ``status`` transitions
through its lifecycle (PENDING → PROCESSING → COMPLETED / FAILED) as the
ingestion pipeline runs.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


# NOTE: `str, enum.Enum` is used rather than `enum.StrEnum` (ruff UP042) because
# the enum must remain importable on Python 3.10 runtimes; `StrEnum` is 3.11+.
class DocumentStatus(str, enum.Enum):  # noqa: UP042
    """Lifecycle status of a document during ingestion.

    The string values match the ``valid_status`` CHECK constraint on the
    ``documents`` table in ``schema.sql``. Inheriting from ``str`` means the
    enum members serialize directly to their SQL/JSON string form.

    Members:
        PENDING: Document is registered but ingestion has not started.
        PROCESSING: Ingestion is currently in progress.
        COMPLETED: Ingestion finished successfully.
        FAILED: Ingestion failed at some stage.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class DocumentRecord:
    """A document tracked by the ingestion pipeline.

    Mirrors the ``documents`` table. Mutable because ``status`` and the
    ``updated_at`` timestamp change as the document progresses through
    ingestion.

    Attributes:
        id: Stable unique identifier for the document (join key for chunks).
        filename: Original file name as ingested.
        file_hash: SHA-256 hex digest of the file contents.
        file_type: File extension including the leading dot (e.g. ``.pdf``).
        file_size_bytes: Size of the source file in bytes.
        status: Current lifecycle status.
        title: Optional document title.
        author: Optional document author.
        page_count: Optional number of pages (for paginated formats).
        word_count: Optional total word count.
        created_at: UTC timestamp when the record was first created.
        updated_at: UTC timestamp of the last update.
        ingested_at: UTC timestamp when ingestion completed, if it has.
    """

    id: str
    filename: str
    file_hash: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus = DocumentStatus.PENDING
    title: str | None = None
    author: str | None = None
    page_count: int | None = None
    word_count: int | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)  # noqa: UP017
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)  # noqa: UP017
    )
    ingested_at: datetime | None = None
