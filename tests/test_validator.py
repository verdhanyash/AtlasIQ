"""Tests for the document validator module.

Verifies that DocumentValidator correctly accepts valid files and rejects
files that are missing, have unsupported formats, or exceed size limits.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atlasiq.backend.core.config import IngestionConfig
from atlasiq.backend.core.exceptions import DocumentValidationError
from atlasiq.ingestion.validator import DocumentValidator


@pytest.fixture
def config() -> IngestionConfig:
    """Provide a default IngestionConfig for testing."""
    return IngestionConfig(
        supported_formats=[".pdf", ".docx", ".md", ".txt"],
        max_file_size_mb=50,
    )


@pytest.fixture
def validator(config: IngestionConfig) -> DocumentValidator:
    """Provide a DocumentValidator initialized with test config."""
    return DocumentValidator(config)


# ── Valid file tests ─────────────────────────────────────────────────────────


class TestValidFiles:
    """Tests for files that should pass validation."""

    def test_valid_txt_file(self, validator: DocumentValidator, tmp_path: Path) -> None:
        """A small .txt file should pass all checks."""
        file = tmp_path / "document.txt"
        file.write_text("Hello, AtlasIQ.")
        validator.validate(file)  # Should not raise

    def test_valid_md_file(self, validator: DocumentValidator, tmp_path: Path) -> None:
        """A .md file should pass validation."""
        file = tmp_path / "notes.md"
        file.write_text("# Heading\n\nSome content.")
        validator.validate(file)

    def test_valid_pdf_extension(self, validator: DocumentValidator, tmp_path: Path) -> None:
        """A file with .pdf extension should pass format check."""
        file = tmp_path / "report.pdf"
        file.write_bytes(b"%PDF-1.4 fake content")
        validator.validate(file)

    def test_valid_docx_extension(self, validator: DocumentValidator, tmp_path: Path) -> None:
        """A file with .docx extension should pass format check."""
        file = tmp_path / "paper.docx"
        file.write_bytes(b"PK fake docx content")
        validator.validate(file)

    def test_case_insensitive_extension(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """Extensions should be matched case-insensitively."""
        file = tmp_path / "REPORT.PDF"
        file.write_bytes(b"%PDF-1.4 fake content")
        validator.validate(file)

    def test_file_exactly_at_size_limit(self, tmp_path: Path) -> None:
        """A file exactly at the size limit should pass."""
        config = IngestionConfig(
            supported_formats=[".txt"],
            max_file_size_mb=1,
        )
        validator = DocumentValidator(config)
        file = tmp_path / "exact.txt"
        # Write exactly 1 MB
        file.write_bytes(b"x" * (1 * 1024 * 1024))
        validator.validate(file)


# ── File existence tests ─────────────────────────────────────────────────────


class TestFileExistence:
    """Tests for missing or invalid file paths."""

    def test_nonexistent_file_raises(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """A file that does not exist should raise DocumentValidationError."""
        missing = tmp_path / "nonexistent.pdf"
        with pytest.raises(DocumentValidationError, match="File not found"):
            validator.validate(missing)

    def test_directory_path_raises(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """A directory path (not a file) should raise DocumentValidationError."""
        subdir = tmp_path / "subfolder"
        subdir.mkdir()
        with pytest.raises(DocumentValidationError, match="not a file"):
            validator.validate(subdir)


# ── Format validation tests ──────────────────────────────────────────────────


class TestFormatValidation:
    """Tests for unsupported file formats."""

    def test_unsupported_extension_raises(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """A .csv file should be rejected."""
        file = tmp_path / "data.csv"
        file.write_text("a,b,c")
        with pytest.raises(DocumentValidationError, match="Unsupported file format"):
            validator.validate(file)

    def test_no_extension_raises(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """A file without an extension should be rejected."""
        file = tmp_path / "README"
        file.write_text("No extension")
        with pytest.raises(DocumentValidationError, match="Unsupported file format"):
            validator.validate(file)

    def test_exe_extension_raises(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """A .exe file should be rejected."""
        file = tmp_path / "malware.exe"
        file.write_bytes(b"\x00" * 100)
        with pytest.raises(DocumentValidationError, match="Unsupported file format"):
            validator.validate(file)


# ── Size validation tests ────────────────────────────────────────────────────


class TestSizeValidation:
    """Tests for file size limits."""

    def test_oversized_file_raises(self, tmp_path: Path) -> None:
        """A file exceeding max_file_size_mb should be rejected."""
        config = IngestionConfig(
            supported_formats=[".txt"],
            max_file_size_mb=1,  # 1 MB limit
        )
        validator = DocumentValidator(config)

        file = tmp_path / "large.txt"
        # Write 1 MB + 1 byte to exceed the limit
        file.write_bytes(b"x" * (1 * 1024 * 1024 + 1))
        with pytest.raises(DocumentValidationError, match="File too large"):
            validator.validate(file)

    def test_empty_file_passes(
        self, validator: DocumentValidator, tmp_path: Path
    ) -> None:
        """An empty file should pass size validation (0 bytes < limit)."""
        file = tmp_path / "empty.txt"
        file.write_text("")
        validator.validate(file)


# ── Custom config tests ──────────────────────────────────────────────────────


class TestCustomConfig:
    """Tests verifying the validator respects custom configuration values."""

    def test_custom_formats(self, tmp_path: Path) -> None:
        """Validator should only accept formats specified in config."""
        config = IngestionConfig(
            supported_formats=[".json"],
            max_file_size_mb=10,
        )
        validator = DocumentValidator(config)

        json_file = tmp_path / "data.json"
        json_file.write_text("{}")
        validator.validate(json_file)  # Should pass

        txt_file = tmp_path / "data.txt"
        txt_file.write_text("text")
        with pytest.raises(DocumentValidationError, match="Unsupported file format"):
            validator.validate(txt_file)
