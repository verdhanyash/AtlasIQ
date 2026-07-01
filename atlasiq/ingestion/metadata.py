"""Document metadata extraction for the ingestion pipeline.

Extracts file-system-level metadata from a document file into a structured
dataclass.  This module is strictly concerned with metadata — it does not
read file content, compute hashes, validate formats, or parse documents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from atlasiq.backend.core.exceptions import DocumentNotFoundError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Immutable snapshot of a document's file-system metadata.

    Attributes:
        file_name: The file's basename (e.g., ``report.pdf``).
        file_path: The full absolute path as a string.
        file_extension: The file suffix in lowercase (e.g., ``.pdf``).
        file_size_bytes: The file size in bytes.
        ingested_at: UTC timestamp of when the metadata was extracted.
    """

    file_name: str
    file_path: str
    file_extension: str
    file_size_bytes: int
    ingested_at: datetime


def extract_metadata(file_path: Path) -> DocumentMetadata:
    """Extract metadata from a file on disk.

    Args:
        file_path: Path to the document file.  Must exist and be a file.

    Returns:
        A populated ``DocumentMetadata`` instance.

    Raises:
        DocumentNotFoundError: If the file does not exist or is not a file.
    """
    if not file_path.exists() or not file_path.is_file():
        msg = f"Cannot extract metadata — file not found: {file_path}"
        raise DocumentNotFoundError(msg)

    stat = file_path.stat()

    metadata = DocumentMetadata(
        file_name=file_path.name,
        file_path=str(file_path.resolve()),
        file_extension=file_path.suffix.lower(),
        file_size_bytes=stat.st_size,
        ingested_at=datetime.now(UTC),
    )

    logger.info(
        "Extracted metadata: %s (%d bytes)",
        metadata.file_name,
        metadata.file_size_bytes,
    )
    return metadata
