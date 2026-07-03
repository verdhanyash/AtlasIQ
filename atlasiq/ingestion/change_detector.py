"""Change detection for the ingestion pipeline.

Computes SHA-256 content hashes and compares them against a registry of
previously ingested documents.  Returns a strongly typed ``ChangeStatus``
indicating whether a file is new, modified, or unchanged.

The public interface (``check`` / ``register``) is designed so that the
backing store can be swapped from the current in-memory dictionary to
PostgreSQL without changing any calling code.
"""

from __future__ import annotations

import enum
import hashlib
import logging
from typing import TYPE_CHECKING

from atlasiq.backend.core.exceptions import DocumentNotFoundError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Read files in 64 KB chunks to keep memory usage constant regardless
# of file size.  This is a true constant — not a configurable value.
_HASH_CHUNK_SIZE: int = 65_536  # 64 KB


class ChangeStatus(enum.Enum):
    """Result of comparing a file's current hash against the registry.

    Members:
        NEW: The file path has never been registered.
        MODIFIED: The file path exists in the registry but the hash differs.
        UNCHANGED: The file path exists and the hash matches exactly.
    """

    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ChangeDetector:
    """Detects whether a document has changed since its last ingestion.

    Maintains an internal registry mapping file paths to their last-known
    SHA-256 content hashes.  The ``check`` method computes the current hash
    and compares it; the ``register`` method records or updates the hash.

    In V1, the registry is an in-memory dictionary.  When the PostgreSQL
    repository layer is implemented, ``check`` and ``register`` will delegate
    to database queries — the public API will remain identical.
    """

    def __init__(self) -> None:
        """Initialise the detector with an empty registry."""
        self._registry: dict[str, str] = {}

    def check(self, file_path: Path) -> ChangeStatus:
        """Determine whether a file is new, modified, or unchanged.

        Args:
            file_path: Path to the document file.  Must exist.

        Returns:
            A ``ChangeStatus`` enum value.

        Raises:
            DocumentNotFoundError: If the file does not exist or is not a file.
        """
        current_hash = self.compute_hash(file_path)
        key = str(file_path.resolve())

        if key not in self._registry:
            logger.info("Change detection: NEW — %s", file_path.name)
            return ChangeStatus.NEW

        if self._registry[key] != current_hash:
            logger.info("Change detection: MODIFIED — %s", file_path.name)
            return ChangeStatus.MODIFIED

        logger.info("Change detection: UNCHANGED — %s", file_path.name)
        return ChangeStatus.UNCHANGED

    def register(self, file_path: Path) -> str:
        """Record (or update) the hash for a file in the registry.

        Call this after a file has been successfully ingested so that
        future ``check`` calls will return ``UNCHANGED`` for the same
        content.

        Args:
            file_path: Path to the document file.  Must exist.

        Returns:
            The computed SHA-256 hex digest that was stored.

        Raises:
            DocumentNotFoundError: If the file does not exist or is not a file.
        """
        content_hash = self.compute_hash(file_path)
        key = str(file_path.resolve())
        self._registry[key] = content_hash
        logger.info("Registered hash for %s", file_path.name)
        return content_hash

    @staticmethod
    def compute_hash(file_path: Path) -> str:
        """Compute the SHA-256 hex digest of a file's contents.

        Reads the file in fixed-size chunks to keep memory usage constant
        regardless of file size. Public and side-effect-free so that callers
        which need the content hash (e.g. the ingestion pipeline) can obtain it
        without touching the registry — hashing is owned by this module (DL-008)
        and is not reimplemented elsewhere.

        Args:
            file_path: Path to the file to hash.

        Returns:
            The lowercase hex SHA-256 digest string (64 characters).

        Raises:
            DocumentNotFoundError: If the file does not exist or is not a file.
        """
        if not file_path.exists() or not file_path.is_file():
            msg = f"Cannot compute hash — file not found: {file_path}"
            raise DocumentNotFoundError(msg)

        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(_HASH_CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)

        return hasher.hexdigest()
