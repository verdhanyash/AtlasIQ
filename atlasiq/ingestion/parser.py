"""Document parser for the ingestion pipeline.

Converts validated document files into Markdown text using IBM Docling for
rich formats (PDF, DOCX) and direct file reads for plain-text formats
(Markdown, TXT).  This module is the second stage of the ingestion pipeline,
sitting between the validator and the chunker.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from atlasiq.backend.core.exceptions import DocumentParsingError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Extensions that can be read directly without Docling.
_PLAINTEXT_EXTENSIONS: frozenset[str] = frozenset({".md", ".txt"})

# Extensions that require Docling for structured parsing.
_RICH_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})


class DocumentParser:
    """Parses document files into Markdown text.

    Plain-text files (.md, .txt) are read directly from disk.
    Rich formats (.pdf, .docx) are parsed via IBM Docling's DocumentConverter,
    which extracts text, tables, and structure into clean Markdown.

    This class lazily initialises the Docling converter on first use to avoid
    import / model-download overhead when only plain-text files are processed.
    """

    def __init__(self) -> None:
        """Initialise the parser.  Docling converter is created lazily."""
        self._converter: Any = None

    def parse(self, file_path: Path) -> str:
        """Parse a document file into Markdown text.

        Args:
            file_path: Path to a validated document file.

        Returns:
            The document content as a Markdown-formatted string.

        Raises:
            DocumentParsingError: If parsing fails for any reason.
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix in _PLAINTEXT_EXTENSIONS:
                text = self._read_plaintext(file_path)
            elif suffix in _RICH_EXTENSIONS:
                text = self._parse_with_docling(file_path)
            else:
                msg = f"Parser does not handle extension: '{suffix}'"
                raise DocumentParsingError(msg)
        except DocumentParsingError:
            raise
        except Exception as exc:
            msg = f"Failed to parse '{file_path.name}': {exc}"
            raise DocumentParsingError(msg) from exc

        if not text or not text.strip():
            msg = f"Parsed document is empty: '{file_path.name}'"
            raise DocumentParsingError(msg)

        logger.info("Parsed %s (%d chars)", file_path.name, len(text))
        return text

    # ── Private helpers ──────────────────────────────────────────────────

    @staticmethod
    def _read_plaintext(file_path: Path) -> str:
        """Read a plain-text file and return its contents."""
        return file_path.read_text(encoding="utf-8")

    def _parse_with_docling(self, file_path: Path) -> str:
        """Parse a rich document via IBM Docling and return Markdown."""
        converter = self._get_converter()
        result = converter.convert(str(file_path))
        return str(result.document.export_to_markdown())

    def _get_converter(self) -> Any:
        """Lazily create and cache the Docling DocumentConverter.

        Returns:
            An instance of ``docling.document_converter.DocumentConverter``.

        Raises:
            DocumentParsingError: If Docling is not installed.
        """
        if self._converter is None:
            try:
                from docling.datamodel.base_models import InputFormat
                from docling.datamodel.pipeline_options import PdfPipelineOptions
                from docling.document_converter import (
                    DocumentConverter,
                    PdfFormatOption,
                )
            except ImportError as exc:
                msg = (
                    "IBM Docling is required for PDF/DOCX parsing. "
                    "Install it with: pip install docling"
                )
                raise DocumentParsingError(msg) from exc

            # Disable OCR: AtlasIQ targets digital documents that already have a
            # real text layer (textbooks, papers, reports). OCR pulls in heavy,
            # environment-fragile engines (e.g. PaddleOCR) that aren't needed for
            # text-based PDFs and can fail to initialise. Scanned-image support
            # would be a separate, opt-in concern.
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = False
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
                }
            )
            logger.info("Docling DocumentConverter initialised (OCR disabled)")
        return self._converter
