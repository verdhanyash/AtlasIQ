"""Recursive text chunker for the ingestion pipeline.

Splits parsed document text into overlapping chunks using a configurable
list of separators, ordered from most to least desirable split point.
The algorithm tries the first separator; if any resulting piece exceeds
``chunk_size``, it recurses with the next separator.  This preserves
semantic boundaries (paragraphs → lines → sentences → words) as much as
possible while guaranteeing every chunk fits within the size limit.

All parameters are injected via ``ChunkingConfig``.
"""

from __future__ import annotations

import logging
from typing import List

from atlasiq.backend.core.config import ChunkingConfig
from atlasiq.backend.core.exceptions import ChunkingError

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Splits text into overlapping chunks using recursive character splitting.

    Attributes:
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of characters shared between consecutive chunks.
        separators: Ordered list of separator strings to try when splitting.
    """

    def __init__(self, config: ChunkingConfig) -> None:
        """Initialise the chunker from configuration.

        Args:
            config: Chunking parameters (size, overlap, separators).

        Raises:
            ChunkingError: If the configuration values are invalid.
        """
        if config.chunk_size <= 0:
            raise ChunkingError("chunk_size must be positive")
        if config.chunk_overlap < 0:
            raise ChunkingError("chunk_overlap must be non-negative")
        if config.chunk_overlap >= config.chunk_size:
            raise ChunkingError("chunk_overlap must be less than chunk_size")

        self.chunk_size: int = config.chunk_size
        self.chunk_overlap: int = config.chunk_overlap
        self.separators: list[str] = list(config.separators)

    def chunk(self, text: str) -> List[str]:
        """Split text into overlapping chunks.

        Args:
            text: The full document text to split.

        Returns:
            A list of non-empty text chunks.

        Raises:
            ChunkingError: If the input text is empty or whitespace-only.
        """
        if not text or not text.strip():
            raise ChunkingError("Cannot chunk empty or whitespace-only text")

        pieces = self._split_recursive(text, self.separators)
        chunks = self._merge_with_overlap(pieces)

        logger.info(
            "Chunked text into %d chunks (size=%d, overlap=%d)",
            len(chunks),
            self.chunk_size,
            self.chunk_overlap,
        )
        return chunks

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy.

        Tries the first separator.  For any resulting piece that still
        exceeds ``chunk_size``, recurses with the remaining separators.
        If no separators remain, the text is split by character count as
        a last resort.

        Args:
            text: The text to split.
            separators: Remaining separators to try (most to least desirable).

        Returns:
            A flat list of text pieces, each at most ``chunk_size`` characters.
        """
        if len(text) <= self.chunk_size:
            stripped = text.strip()
            return [stripped] if stripped else []

        if not separators:
            return self._split_by_characters(text)

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            return self._split_by_characters(text)

        parts = text.split(separator)
        result: list[str] = []

        for part in parts:
            stripped = part.strip()
            if not stripped:
                continue
            if len(stripped) <= self.chunk_size:
                result.append(stripped)
            else:
                result.extend(
                    self._split_recursive(stripped, remaining_separators)
                )

        return result

    def _split_by_characters(self, text: str) -> list[str]:
        """Split text into fixed-size pieces as a last resort.

        Args:
            text: The text to split by character count.

        Returns:
            A list of text pieces, each at most ``chunk_size`` characters.
        """
        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)
            start = end
        return pieces

    def _merge_with_overlap(self, pieces: list[str]) -> list[str]:
        """Merge small pieces into chunks with overlap.

        Combines consecutive pieces into chunks that approach but do not
        exceed ``chunk_size``.  Each chunk overlaps with the previous one
        by up to ``chunk_overlap`` characters (taken from the tail of the
        preceding chunk).

        Args:
            pieces: Pre-split text pieces from the recursive splitter.

        Returns:
            A list of merged, overlapping text chunks.
        """
        if not pieces:
            return []

        chunks: list[str] = []
        current_parts: list[str] = []
        current_length = 0

        for piece in pieces:
            # Would adding this piece exceed the chunk size?
            added_length = len(piece) + (1 if current_parts else 0)

            if current_length + added_length > self.chunk_size and current_parts:
                # Finalise the current chunk
                chunk_text = " ".join(current_parts)
                chunks.append(chunk_text)

                # Build overlap: keep trailing parts that fit within overlap
                if self.chunk_overlap > 0:
                    overlap_parts: list[str] = []
                    overlap_len = 0
                    for part in reversed(current_parts):
                        part_len = len(part) + (1 if overlap_parts else 0)
                        if overlap_len + part_len <= self.chunk_overlap:
                            overlap_parts.insert(0, part)
                            overlap_len += part_len
                        else:
                            break
                    current_parts = overlap_parts
                    current_length = overlap_len
                else:
                    current_parts = []
                    current_length = 0

            current_parts.append(piece)
            current_length += len(piece) + (1 if len(current_parts) > 1 else 0)

        # Flush the last chunk
        if current_parts:
            chunk_text = " ".join(current_parts)
            chunks.append(chunk_text)

        return chunks
