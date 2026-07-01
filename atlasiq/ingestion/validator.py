"""Document file validator for the ingestion pipeline.

Validates that a file meets AtlasIQ's ingestion requirements before any
parsing or processing begins. Checks file existence, supported format,
and size constraints using values from IngestionConfig.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlasiq.backend.core.exceptions import DocumentValidationError

if TYPE_CHECKING:
    from pathlib import Path

    from atlasiq.backend.core.config import IngestionConfig

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Validates documents against format and size constraints.

    Uses IngestionConfig to determine which file extensions are supported
    and the maximum allowed file size.

    Attributes:
        supported_formats: Set of allowed file extensions (e.g., {".pdf", ".md"}).
        max_file_size_bytes: Maximum file size in bytes.
    """

    def __init__(self, config: IngestionConfig) -> None:
        """Initialize the validator with ingestion configuration.

        Args:
            config: IngestionConfig containing supported_formats and max_file_size_mb.
        """
        self.supported_formats: set[str] = {
            fmt.lower() for fmt in config.supported_formats
        }
        self.max_file_size_bytes: int = config.max_file_size_mb * 1024 * 1024

    def validate(self, file_path: Path) -> None:
        """Validate a file for ingestion.

        Checks in order:
            1. File exists on disk.
            2. File extension is in the supported formats list.
            3. File size does not exceed the configured maximum.

        Args:
            file_path: Path to the file to validate.

        Raises:
            DocumentValidationError: If any validation check fails.
        """
        self._check_exists(file_path)
        self._check_format(file_path)
        self._check_size(file_path)
        logger.info("Validation passed: %s", file_path.name)

    def _check_exists(self, file_path: Path) -> None:
        """Verify the file exists on disk."""
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise DocumentValidationError(msg)
        if not file_path.is_file():
            msg = f"Path is not a file: {file_path}"
            raise DocumentValidationError(msg)

    def _check_format(self, file_path: Path) -> None:
        """Verify the file extension is supported."""
        suffix = file_path.suffix.lower()
        if suffix not in self.supported_formats:
            msg = (
                f"Unsupported file format: '{suffix}'. "
                f"Supported formats: {sorted(self.supported_formats)}"
            )
            raise DocumentValidationError(msg)

    def _check_size(self, file_path: Path) -> None:
        """Verify the file does not exceed the maximum size limit."""
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size_bytes:
            size_mb = file_size / (1024 * 1024)
            limit_mb = self.max_file_size_bytes / (1024 * 1024)
            msg = (
                f"File too large: {size_mb:.1f} MB "
                f"(limit: {limit_mb:.0f} MB)"
            )
            raise DocumentValidationError(msg)
