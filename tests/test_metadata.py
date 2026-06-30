"""Tests for the document metadata extraction module.

Verifies that ``extract_metadata`` correctly populates every field of the
``DocumentMetadata`` dataclass from file-system information, and raises
the correct exception for missing files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from atlasiq.backend.core.exceptions import DocumentNotFoundError
from atlasiq.ingestion.metadata import DocumentMetadata, extract_metadata


# ── Successful extraction ────────────────────────────────────────────────────


class TestExtractMetadata:
    """Tests for the extract_metadata factory function."""

    def test_file_name(self, tmp_path: Path) -> None:
        """file_name should be the basename of the file."""
        file = tmp_path / "report.pdf"
        file.write_bytes(b"%PDF-1.4 fake")
        meta = extract_metadata(file)
        assert meta.file_name == "report.pdf"

    def test_file_path_is_absolute(self, tmp_path: Path) -> None:
        """file_path should be the resolved absolute path."""
        file = tmp_path / "notes.md"
        file.write_text("# Notes", encoding="utf-8")
        meta = extract_metadata(file)
        assert Path(meta.file_path).is_absolute()
        assert meta.file_path == str(file.resolve())

    def test_file_extension_lowercase(self, tmp_path: Path) -> None:
        """file_extension should be lowercase regardless of the actual suffix."""
        file = tmp_path / "DATA.DOCX"
        file.write_bytes(b"PK fake docx")
        meta = extract_metadata(file)
        assert meta.file_extension == ".docx"

    def test_file_size_bytes(self, tmp_path: Path) -> None:
        """file_size_bytes should match the actual file size."""
        content = b"Hello, AtlasIQ! " * 100
        file = tmp_path / "content.txt"
        file.write_bytes(content)
        meta = extract_metadata(file)
        assert meta.file_size_bytes == len(content)

    def test_empty_file_size_is_zero(self, tmp_path: Path) -> None:
        """An empty file should report 0 bytes."""
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")
        meta = extract_metadata(file)
        assert meta.file_size_bytes == 0

    def test_ingested_at_is_recent_utc(self, tmp_path: Path) -> None:
        """ingested_at should be a recent UTC timestamp."""
        file = tmp_path / "doc.md"
        file.write_text("content", encoding="utf-8")
        before = datetime.now(timezone.utc)
        meta = extract_metadata(file)
        after = datetime.now(timezone.utc)
        assert before <= meta.ingested_at <= after

    def test_txt_extension(self, tmp_path: Path) -> None:
        """A .txt file should have extension '.txt'."""
        file = tmp_path / "plain.txt"
        file.write_text("plain text", encoding="utf-8")
        meta = extract_metadata(file)
        assert meta.file_extension == ".txt"

    def test_pdf_extension(self, tmp_path: Path) -> None:
        """A .pdf file should have extension '.pdf'."""
        file = tmp_path / "paper.pdf"
        file.write_bytes(b"%PDF-1.4")
        meta = extract_metadata(file)
        assert meta.file_extension == ".pdf"


# ── Dataclass properties ─────────────────────────────────────────────────────


class TestDocumentMetadataDataclass:
    """Tests for the DocumentMetadata dataclass properties."""

    def test_frozen_immutability(self, tmp_path: Path) -> None:
        """DocumentMetadata instances should be immutable (frozen=True)."""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        meta = extract_metadata(file)
        with pytest.raises(AttributeError):
            meta.file_name = "changed.txt"  # type: ignore[misc]

    def test_equality_same_values(self) -> None:
        """Two metadata instances with identical values should be equal."""
        ts = datetime.now(timezone.utc)
        m1 = DocumentMetadata("a.txt", "/path/a.txt", ".txt", 100, ts)
        m2 = DocumentMetadata("a.txt", "/path/a.txt", ".txt", 100, ts)
        assert m1 == m2


# ── Error cases ──────────────────────────────────────────────────────────────


class TestMetadataErrors:
    """Tests for error handling in metadata extraction."""

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Extracting metadata from a missing file should raise."""
        missing = tmp_path / "ghost.pdf"
        with pytest.raises(DocumentNotFoundError, match="file not found"):
            extract_metadata(missing)

    def test_directory_path_raises(self, tmp_path: Path) -> None:
        """Extracting metadata from a directory should raise."""
        subdir = tmp_path / "folder"
        subdir.mkdir()
        with pytest.raises(DocumentNotFoundError, match="file not found"):
            extract_metadata(subdir)
