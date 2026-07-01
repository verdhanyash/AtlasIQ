"""Tests for the document parser module.

Tests verify that DocumentParser correctly reads plain-text files and
delegates rich-format parsing to Docling.  Docling itself is mocked to
avoid requiring the heavy dependency (and model downloads) in CI / local
test runs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from atlasiq.backend.core.exceptions import DocumentParsingError
from atlasiq.ingestion.parser import DocumentParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> DocumentParser:
    """Provide a fresh DocumentParser instance."""
    return DocumentParser()


# ── Plain-text parsing ───────────────────────────────────────────────────────


class TestPlaintextParsing:
    """Tests for .txt and .md file parsing (no Docling needed)."""

    def test_parse_txt_file(self, parser: DocumentParser, tmp_path: Path) -> None:
        """A .txt file should be read directly and returned as-is."""
        file = tmp_path / "readme.txt"
        file.write_text("Hello, AtlasIQ!", encoding="utf-8")
        result = parser.parse(file)
        assert result == "Hello, AtlasIQ!"

    def test_parse_md_file(self, parser: DocumentParser, tmp_path: Path) -> None:
        """A .md file should be read directly and returned as-is."""
        file = tmp_path / "notes.md"
        content = "# Title\n\nSome paragraph text."
        file.write_text(content, encoding="utf-8")
        result = parser.parse(file)
        assert result == content

    def test_multiline_content(self, parser: DocumentParser, tmp_path: Path) -> None:
        """Multi-line content should be preserved."""
        file = tmp_path / "multi.txt"
        lines = "Line 1\nLine 2\nLine 3"
        file.write_text(lines, encoding="utf-8")
        result = parser.parse(file)
        assert result == lines

    def test_unicode_content(self, parser: DocumentParser, tmp_path: Path) -> None:
        """Unicode characters should be handled correctly."""
        file = tmp_path / "unicode.md"
        content = "日本語テスト — émojis: 🎉🚀"
        file.write_text(content, encoding="utf-8")
        result = parser.parse(file)
        assert result == content


# ── Empty file detection ─────────────────────────────────────────────────────


class TestEmptyFileDetection:
    """Tests for empty or whitespace-only files."""

    def test_empty_file_raises(self, parser: DocumentParser, tmp_path: Path) -> None:
        """An empty file should raise DocumentParsingError."""
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")
        with pytest.raises(DocumentParsingError, match="empty"):
            parser.parse(file)

    def test_whitespace_only_file_raises(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """A file containing only whitespace should raise DocumentParsingError."""
        file = tmp_path / "blank.md"
        file.write_text("   \n\n\t  ", encoding="utf-8")
        with pytest.raises(DocumentParsingError, match="empty"):
            parser.parse(file)


# ── Unsupported extension ────────────────────────────────────────────────────


class TestUnsupportedExtension:
    """Tests for file extensions the parser doesn't handle."""

    def test_unsupported_extension_raises(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """A .csv file should raise DocumentParsingError."""
        file = tmp_path / "data.csv"
        file.write_text("a,b,c", encoding="utf-8")
        with pytest.raises(DocumentParsingError, match="does not handle"):
            parser.parse(file)


# ── Docling integration (mocked) ─────────────────────────────────────────────


class TestDoclingIntegration:
    """Tests for PDF/DOCX parsing via mocked Docling DocumentConverter."""

    def _make_mock_converter(self, markdown_output: str) -> MagicMock:
        """Create a mock Docling converter that returns the given markdown."""
        mock_converter = MagicMock()
        mock_result = SimpleNamespace(
            document=SimpleNamespace(export_to_markdown=lambda: markdown_output)
        )
        mock_converter.convert.return_value = mock_result
        return mock_converter

    def test_parse_pdf_via_docling(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """A .pdf file should be parsed via the Docling converter."""
        file = tmp_path / "report.pdf"
        file.write_bytes(b"%PDF-1.4 fake content")

        expected_md = "# Report\n\nThis is the parsed content."
        mock_converter = self._make_mock_converter(expected_md)
        parser._converter = mock_converter

        result = parser.parse(file)
        assert result == expected_md
        mock_converter.convert.assert_called_once_with(str(file))

    def test_parse_docx_via_docling(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """A .docx file should be parsed via the Docling converter."""
        file = tmp_path / "paper.docx"
        file.write_bytes(b"PK fake docx content")

        expected_md = "# Paper\n\nDocx content here."
        mock_converter = self._make_mock_converter(expected_md)
        parser._converter = mock_converter

        result = parser.parse(file)
        assert result == expected_md
        mock_converter.convert.assert_called_once_with(str(file))

    def test_docling_empty_output_raises(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """If Docling returns empty text, raise DocumentParsingError."""
        file = tmp_path / "blank.pdf"
        file.write_bytes(b"%PDF-1.4 empty")

        mock_converter = self._make_mock_converter("")
        parser._converter = mock_converter

        with pytest.raises(DocumentParsingError, match="empty"):
            parser.parse(file)

    def test_docling_exception_wraps_as_parsing_error(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """If Docling raises, it should be wrapped in DocumentParsingError."""
        file = tmp_path / "corrupt.pdf"
        file.write_bytes(b"not a real pdf")

        mock_converter = MagicMock()
        mock_converter.convert.side_effect = RuntimeError("Docling exploded")
        parser._converter = mock_converter

        with pytest.raises(DocumentParsingError, match="Failed to parse"):
            parser.parse(file)

    def test_docling_not_installed_raises(self, tmp_path: Path) -> None:
        """If docling is not installed, _get_converter should raise."""
        file = tmp_path / "test.pdf"
        file.write_bytes(b"%PDF-1.4 fake")

        with patch.dict("sys.modules", {"docling": None, "docling.document_converter": None}):
            fresh_parser = DocumentParser()
            with pytest.raises(DocumentParsingError, match="Docling is required"):
                fresh_parser.parse(file)


# ── Lazy initialisation ──────────────────────────────────────────────────────


class TestLazyInitialisation:
    """Tests verifying that Docling is only loaded when needed."""

    def test_converter_not_created_for_txt(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """Parsing a .txt file should not trigger Docling initialisation."""
        file = tmp_path / "simple.txt"
        file.write_text("Just text.", encoding="utf-8")
        parser.parse(file)
        assert parser._converter is None

    def test_converter_not_created_for_md(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        """Parsing a .md file should not trigger Docling initialisation."""
        file = tmp_path / "simple.md"
        file.write_text("# Just markdown", encoding="utf-8")
        parser.parse(file)
        assert parser._converter is None
