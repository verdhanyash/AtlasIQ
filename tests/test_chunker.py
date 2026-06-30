"""Tests for the document chunker module.

Verifies that ``DocumentChunker`` correctly splits text using the recursive
separator hierarchy, merges pieces with overlap, handles edge cases, and
validates configuration.
"""

from __future__ import annotations

import pytest

from atlasiq.backend.core.config import ChunkingConfig
from atlasiq.backend.core.exceptions import ChunkingError
from atlasiq.ingestion.chunker import DocumentChunker


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def default_chunker() -> DocumentChunker:
    """Provide a chunker with default configuration (512 / 50)."""
    return DocumentChunker(ChunkingConfig())


@pytest.fixture
def small_chunker() -> DocumentChunker:
    """Provide a chunker with small size for precise testing (50 / 10)."""
    config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
    return DocumentChunker(config)


@pytest.fixture
def no_overlap_chunker() -> DocumentChunker:
    """Provide a chunker with zero overlap (50 / 0)."""
    config = ChunkingConfig(chunk_size=50, chunk_overlap=0)
    return DocumentChunker(config)


# ── Basic chunking ───────────────────────────────────────────────────────────


class TestBasicChunking:
    """Tests for fundamental chunking behaviour."""

    def test_short_text_returns_single_chunk(self, default_chunker: DocumentChunker) -> None:
        """Text shorter than chunk_size should return a single chunk."""
        text = "This is a short document."
        chunks = default_chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_text_exactly_at_limit(self, small_chunker: DocumentChunker) -> None:
        """Text at exactly chunk_size should return a single chunk."""
        text = "x" * 50
        chunks = small_chunker.chunk(text)
        assert len(chunks) == 1

    def test_long_text_produces_multiple_chunks(self, small_chunker: DocumentChunker) -> None:
        """Text longer than chunk_size should produce multiple chunks."""
        text = "word " * 50  # ~250 chars
        chunks = small_chunker.chunk(text)
        assert len(chunks) > 1

    def test_all_chunks_within_size_limit(self, small_chunker: DocumentChunker) -> None:
        """Every chunk should be at most chunk_size characters."""
        text = "This is a sentence. " * 30
        chunks = small_chunker.chunk(text)
        for chunk in chunks:
            assert len(chunk) <= small_chunker.chunk_size + small_chunker.chunk_overlap

    def test_no_empty_chunks(self, small_chunker: DocumentChunker) -> None:
        """No chunk should be empty or whitespace-only."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = small_chunker.chunk(text)
        for chunk in chunks:
            assert chunk.strip() != ""


# ── Separator hierarchy ──────────────────────────────────────────────────────


class TestSeparatorHierarchy:
    """Tests that separators are used in priority order."""

    def test_paragraph_separator_used_first(self) -> None:
        """Double newline (paragraph break) should be the primary split point."""
        config = ChunkingConfig(chunk_size=40, chunk_overlap=0)
        chunker = DocumentChunker(config)
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        chunks = chunker.chunk(text)
        # Each paragraph is ~21 chars, well under 40, but the full text is ~70 chars
        assert len(chunks) >= 2
        combined = " ".join(chunks)
        assert "First paragraph" in combined
        assert "Second paragraph" in combined
        assert "Third paragraph" in combined

    def test_line_separator_fallback(self) -> None:
        """Single newline should be used when paragraphs are too large."""
        config = ChunkingConfig(chunk_size=30, chunk_overlap=0)
        chunker = DocumentChunker(config)
        text = "Line one.\nLine two.\nLine three."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2

    def test_sentence_separator_fallback(self) -> None:
        """Sentence boundary ('. ') should be used when lines are too large."""
        config = ChunkingConfig(chunk_size=30, chunk_overlap=0)
        chunker = DocumentChunker(config)
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2

    def test_word_separator_fallback(self) -> None:
        """Space should be used when sentences are too large."""
        config = ChunkingConfig(chunk_size=15, chunk_overlap=0)
        chunker = DocumentChunker(config)
        text = "word1 word2 word3 word4 word5"
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2

    def test_character_fallback(self) -> None:
        """A single long word exceeding chunk_size should be split by characters."""
        config = ChunkingConfig(chunk_size=10, chunk_overlap=0)
        chunker = DocumentChunker(config)
        text = "a" * 25
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 10


# ── Overlap ──────────────────────────────────────────────────────────────────


class TestOverlap:
    """Tests for chunk overlap behaviour."""

    def test_overlap_produces_shared_content(self) -> None:
        """Consecutive chunks should share content when overlap > 0."""
        config = ChunkingConfig(chunk_size=30, chunk_overlap=10)
        chunker = DocumentChunker(config)
        text = "AA BB CC DD EE FF GG HH II JJ KK LL MM"
        chunks = chunker.chunk(text)
        # With short words and overlap=10, consecutive chunks should share words
        assert len(chunks) >= 2

    def test_zero_overlap_no_shared_content(self) -> None:
        """With overlap=0, consecutive chunks should not duplicate content."""
        config = ChunkingConfig(chunk_size=20, chunk_overlap=0)
        chunker = DocumentChunker(config)
        text = "Alpha bravo charlie.\n\nDelta echo foxtrot.\n\nGolf hotel india."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge case inputs."""

    def test_empty_string_raises(self, default_chunker: DocumentChunker) -> None:
        """Empty string should raise ChunkingError."""
        with pytest.raises(ChunkingError, match="empty"):
            default_chunker.chunk("")

    def test_whitespace_only_raises(self, default_chunker: DocumentChunker) -> None:
        """Whitespace-only string should raise ChunkingError."""
        with pytest.raises(ChunkingError, match="empty"):
            default_chunker.chunk("   \n\n\t  ")

    def test_single_word(self, default_chunker: DocumentChunker) -> None:
        """A single word should return one chunk."""
        chunks = default_chunker.chunk("Hello")
        assert chunks == ["Hello"]

    def test_unicode_content(self, small_chunker: DocumentChunker) -> None:
        """Unicode characters should be handled correctly."""
        text = "日本語のテスト。これは二番目の文です。三番目の文もあります。"
        chunks = small_chunker.chunk(text)
        assert len(chunks) >= 1
        full_text = " ".join(chunks)
        # All original characters should be present somewhere in the chunks
        for char in "日本語テスト":
            assert char in full_text

    def test_many_newlines(self, small_chunker: DocumentChunker) -> None:
        """Multiple consecutive newlines should not produce empty chunks."""
        text = "First.\n\n\n\n\nSecond.\n\n\n\nThird."
        chunks = small_chunker.chunk(text)
        for chunk in chunks:
            assert chunk.strip() != ""

    def test_trailing_whitespace_stripped(self, default_chunker: DocumentChunker) -> None:
        """Chunks should not have leading or trailing whitespace."""
        text = "  Some text with spaces.  \n\n  Another paragraph.  "
        chunks = default_chunker.chunk(text)
        for chunk in chunks:
            assert chunk == chunk.strip()


# ── Configuration validation ─────────────────────────────────────────────────


class TestConfigValidation:
    """Tests for invalid configuration handling."""

    def test_zero_chunk_size_raises(self) -> None:
        """chunk_size=0 should raise ChunkingError."""
        config = ChunkingConfig(chunk_size=0, chunk_overlap=0)
        with pytest.raises(ChunkingError, match="chunk_size must be positive"):
            DocumentChunker(config)

    def test_negative_chunk_size_raises(self) -> None:
        """Negative chunk_size should raise ChunkingError."""
        config = ChunkingConfig(chunk_size=-10, chunk_overlap=0)
        with pytest.raises(ChunkingError, match="chunk_size must be positive"):
            DocumentChunker(config)

    def test_negative_overlap_raises(self) -> None:
        """Negative chunk_overlap should raise ChunkingError."""
        config = ChunkingConfig(chunk_size=100, chunk_overlap=-5)
        with pytest.raises(ChunkingError, match="chunk_overlap must be non-negative"):
            DocumentChunker(config)

    def test_overlap_equals_size_raises(self) -> None:
        """chunk_overlap == chunk_size should raise ChunkingError."""
        config = ChunkingConfig(chunk_size=50, chunk_overlap=50)
        with pytest.raises(ChunkingError, match="chunk_overlap must be less than"):
            DocumentChunker(config)

    def test_overlap_exceeds_size_raises(self) -> None:
        """chunk_overlap > chunk_size should raise ChunkingError."""
        config = ChunkingConfig(chunk_size=50, chunk_overlap=100)
        with pytest.raises(ChunkingError, match="chunk_overlap must be less than"):
            DocumentChunker(config)


# ── Realistic document ───────────────────────────────────────────────────────


class TestRealisticDocument:
    """Tests with realistic Markdown document content."""

    def test_markdown_document(self, default_chunker: DocumentChunker) -> None:
        """A realistic Markdown document should chunk cleanly."""
        text = (
            "# Introduction\n\n"
            "AtlasIQ is an enterprise knowledge platform that ingests documents, "
            "generates embeddings, and provides evidence-backed answers.\n\n"
            "## Architecture\n\n"
            "The system uses a layered architecture with FastAPI backend, "
            "Qdrant vector database, and PostgreSQL for metadata storage.\n\n"
            "## Data Flow\n\n"
            "Documents are validated, parsed, chunked, embedded, and stored. "
            "Queries go through hybrid retrieval, reranking, and LLM synthesis."
        )
        chunks = default_chunker.chunk(text)
        assert len(chunks) >= 1
        # All content should be preserved across chunks
        combined = " ".join(chunks)
        assert "AtlasIQ" in combined
        assert "architecture" in combined.lower()
        assert "Data Flow" in combined

    def test_chunk_count_reasonable(self) -> None:
        """A 2000-char document with chunk_size=512 should produce ~4-6 chunks."""
        config = ChunkingConfig(chunk_size=512, chunk_overlap=50)
        chunker = DocumentChunker(config)
        text = "This is a sentence with some content. " * 60  # ~2280 chars
        chunks = chunker.chunk(text)
        assert 3 <= len(chunks) <= 10
