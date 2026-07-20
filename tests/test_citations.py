"""Unit tests for the citation builder (M2-9).

All tests are offline — no external dependencies.

Coverage:
- Citation dataclass structure
- Page formatting: single page, page range, N/A
- Basic citation building from chunks
- Deduplication by (document, page)
- Highest-scoring chunk wins on dedup collision
- Multiple sources (different documents)
- Empty input handling
- Quote extraction and whitespace trimming
- Order preservation (first appearance)
"""

from __future__ import annotations

import pytest

from atlasiq.backend.domain.chunk import ChunkRecord
from atlasiq.retrieval.citations import Citation, CitationBuilder
from atlasiq.retrieval.models import RetrievedChunk

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def builder() -> CitationBuilder:
    """A citation builder instance."""
    return CitationBuilder()


def _make_chunk(
    filename: str,
    content: str,
    start_page: int | None = None,
    end_page: int | None = None,
    score: float = 1.0,
    chunk_index: int = 0,
) -> RetrievedChunk:
    """Helper to construct a RetrievedChunk for testing."""
    chunk_record = ChunkRecord(
        id=f"chunk-{chunk_index}",
        document_id=f"doc-{filename}",
        chunk_index=chunk_index,
        content=content,
        start_page=start_page,
        end_page=end_page,
    )
    return RetrievedChunk(chunk=chunk_record, filename=filename, score=score)


# ── Citation Dataclass ───────────────────────────────────────────────────────


class TestCitationDataclass:
    """Tests for the :class:`Citation` value object."""

    def test_fields(self) -> None:
        """Citation has document_name, page, and quote fields."""
        citation = Citation(
            document_name="report.pdf", page="12", quote="Evidence text."
        )
        assert citation.document_name == "report.pdf"
        assert citation.page == "12"
        assert citation.quote == "Evidence text."

    def test_frozen_immutability(self) -> None:
        """Citation is frozen (fields cannot be mutated after creation)."""
        citation = Citation(
            document_name="doc.pdf", page="5", quote="Some text."
        )
        with pytest.raises(AttributeError):
            citation.document_name = "other.pdf"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Two citations with identical values are equal."""
        c1 = Citation(document_name="a.pdf", page="1", quote="text")
        c2 = Citation(document_name="a.pdf", page="1", quote="text")
        assert c1 == c2


# ── Page Formatting ──────────────────────────────────────────────────────────


class TestPageFormatting:
    """Tests for page reference formatting."""

    def test_single_page(self, builder: CitationBuilder) -> None:
        """start_page only → renders as a single page number."""
        chunk = _make_chunk("doc.pdf", "Content.", start_page=12, end_page=12)
        citations = builder.build([chunk])
        assert len(citations) == 1
        assert citations[0].page == "12"

    def test_page_range(self, builder: CitationBuilder) -> None:
        """start_page != end_page → renders as a range."""
        chunk = _make_chunk("doc.pdf", "Content.", start_page=12, end_page=14)
        citations = builder.build([chunk])
        assert len(citations) == 1
        assert citations[0].page == "12-14"

    def test_no_page_info(self, builder: CitationBuilder) -> None:
        """start_page is None → renders as N/A."""
        chunk = _make_chunk("doc.txt", "Content.", start_page=None, end_page=None)
        citations = builder.build([chunk])
        assert len(citations) == 1
        assert citations[0].page == "N/A"

    def test_only_end_page_is_ignored(self, builder: CitationBuilder) -> None:
        """If start_page is None but end_page is set, treat as N/A."""
        chunk = _make_chunk("doc.pdf", "Content.", start_page=None, end_page=10)
        citations = builder.build([chunk])
        assert citations[0].page == "N/A"


# ── Basic Citation Building ──────────────────────────────────────────────────


class TestBasicCitationBuilding:
    """Tests for building citations from single/multiple chunks."""

    def test_single_chunk(self, builder: CitationBuilder) -> None:
        """A single chunk produces one citation."""
        chunk = _make_chunk("report.pdf", "Chunk content.", start_page=5)
        citations = builder.build([chunk])

        assert len(citations) == 1
        assert citations[0].document_name == "report.pdf"
        assert citations[0].page == "5"
        assert citations[0].quote == "Chunk content."

    def test_multiple_chunks_different_documents(
        self, builder: CitationBuilder
    ) -> None:
        """Chunks from different documents produce separate citations."""
        chunk1 = _make_chunk("doc1.pdf", "First content.", start_page=1, score=0.9)
        chunk2 = _make_chunk("doc2.pdf", "Second content.", start_page=2, score=0.8)

        citations = builder.build([chunk1, chunk2])
        assert len(citations) == 2
        assert citations[0].document_name == "doc1.pdf"
        assert citations[1].document_name == "doc2.pdf"

    def test_multiple_chunks_different_pages_same_doc(
        self, builder: CitationBuilder
    ) -> None:
        """Multiple chunks from the same document but different pages."""
        chunk1 = _make_chunk("doc.pdf", "Content A.", start_page=1)
        chunk2 = _make_chunk("doc.pdf", "Content B.", start_page=2)

        citations = builder.build([chunk1, chunk2])
        assert len(citations) == 2
        assert citations[0].page == "1"
        assert citations[0].quote == "Content A."
        assert citations[1].page == "2"
        assert citations[1].quote == "Content B."

    def test_empty_input(self, builder: CitationBuilder) -> None:
        """Empty chunk list produces empty citation list."""
        citations = builder.build([])
        assert citations == []


# ── Deduplication ────────────────────────────────────────────────────────────


class TestDeduplication:
    """Tests for deduplication by (document, page)."""

    def test_duplicate_document_and_page_deduped(
        self, builder: CitationBuilder
    ) -> None:
        """Multiple chunks from the same document+page produce one citation."""
        chunk1 = _make_chunk("doc.pdf", "First chunk.", start_page=5, score=0.8)
        chunk2 = _make_chunk("doc.pdf", "Second chunk.", start_page=5, score=0.7)

        citations = builder.build([chunk1, chunk2])
        assert len(citations) == 1
        # Highest-scoring chunk (chunk1) should be cited
        assert citations[0].quote == "First chunk."

    def test_highest_score_wins_on_collision(
        self, builder: CitationBuilder
    ) -> None:
        """When deduping, the chunk with the highest score is kept."""
        chunk1 = _make_chunk("doc.pdf", "Low score.", start_page=10, score=0.5)
        chunk2 = _make_chunk("doc.pdf", "High score.", start_page=10, score=0.9)
        chunk3 = _make_chunk("doc.pdf", "Medium score.", start_page=10, score=0.7)

        citations = builder.build([chunk1, chunk2, chunk3])
        assert len(citations) == 1
        assert citations[0].quote == "High score."

    def test_dedup_respects_page_range(self, builder: CitationBuilder) -> None:
        """Chunks with different page ranges are not considered duplicates."""
        chunk1 = _make_chunk("doc.pdf", "Pages 5-6.", start_page=5, end_page=6)
        chunk2 = _make_chunk("doc.pdf", "Page 5 only.", start_page=5, end_page=5)

        citations = builder.build([chunk1, chunk2])
        # "5-6" and "5" are different page references → 2 citations
        assert len(citations) == 2

    def test_dedup_na_pages(self, builder: CitationBuilder) -> None:
        """Multiple chunks with N/A pages from the same doc are deduped."""
        chunk1 = _make_chunk("doc.txt", "Chunk A.", start_page=None, score=0.8)
        chunk2 = _make_chunk("doc.txt", "Chunk B.", start_page=None, score=0.6)

        citations = builder.build([chunk1, chunk2])
        assert len(citations) == 1
        assert citations[0].page == "N/A"
        assert citations[0].quote == "Chunk A."  # higher score


# ── Quote Extraction ─────────────────────────────────────────────────────────


class TestQuoteExtraction:
    """Tests for extracting and formatting the quote text."""

    def test_quote_is_chunk_content(self, builder: CitationBuilder) -> None:
        """The quote field is the chunk's content."""
        chunk = _make_chunk("doc.pdf", "This is the chunk text.", start_page=1)
        citations = builder.build([chunk])
        assert citations[0].quote == "This is the chunk text."

    def test_quote_whitespace_trimmed(self, builder: CitationBuilder) -> None:
        """Leading/trailing whitespace in the chunk content is stripped."""
        chunk = _make_chunk("doc.pdf", "  \n Content  \n  ", start_page=1)
        citations = builder.build([chunk])
        assert citations[0].quote == "Content"

    def test_quote_preserves_internal_whitespace(
        self, builder: CitationBuilder
    ) -> None:
        """Internal whitespace (newlines, multiple spaces) is preserved."""
        chunk = _make_chunk(
            "doc.pdf", "Line one.\n\nLine two with  spaces.", start_page=1
        )
        citations = builder.build([chunk])
        assert citations[0].quote == "Line one.\n\nLine two with  spaces."


# ── Order Preservation ───────────────────────────────────────────────────────


class TestOrderPreservation:
    """Tests for preserving input order in the output."""

    def test_output_order_matches_input_order(
        self, builder: CitationBuilder
    ) -> None:
        """Citations appear in the same order as their first occurrence in input."""
        chunk1 = _make_chunk("a.pdf", "First.", start_page=1, score=0.7)
        chunk2 = _make_chunk("b.pdf", "Second.", start_page=2, score=0.9)
        chunk3 = _make_chunk("c.pdf", "Third.", start_page=3, score=0.8)

        citations = builder.build([chunk1, chunk2, chunk3])
        assert len(citations) == 3
        assert citations[0].document_name == "a.pdf"
        assert citations[1].document_name == "b.pdf"
        assert citations[2].document_name == "c.pdf"

    def test_dedup_preserves_first_appearance_order(
        self, builder: CitationBuilder
    ) -> None:
        """When dedup occurs, the citation appears at the first chunk's position."""
        chunk1 = _make_chunk("a.pdf", "A content.", start_page=1, score=0.5)
        chunk2 = _make_chunk("b.pdf", "B content.", start_page=2, score=0.9)
        chunk3 = _make_chunk("a.pdf", "A again.", start_page=1, score=0.8)

        citations = builder.build([chunk1, chunk2, chunk3])
        # chunk1 and chunk3 deduplicate; chunk3 wins (higher score)
        # but appears at chunk1's position (first)
        assert len(citations) == 2
        assert citations[0].document_name == "a.pdf"
        assert citations[0].quote == "A again."  # higher score wins
        assert citations[1].document_name == "b.pdf"


# ── Realistic Scenario ───────────────────────────────────────────────────────


class TestRealisticScenario:
    """End-to-end scenario resembling real retrieval output."""

    def test_mixed_documents_with_dedup(self, builder: CitationBuilder) -> None:
        """Realistic mix: multiple documents, some dedup, some distinct."""
        chunks = [
            _make_chunk("report.pdf", "Main finding.", start_page=12, score=0.95),
            _make_chunk("guide.pdf", "Explanation.", start_page=5, score=0.90),
            _make_chunk("report.pdf", "Details.", start_page=12, score=0.85),
            _make_chunk("data.csv", "Numbers.", start_page=None, score=0.80),
            _make_chunk("report.pdf", "More info.", start_page=13, score=0.75),
        ]

        citations = builder.build(chunks)

        # Expected: 4 citations
        # - report.pdf page 12 (dedup chunk 1 + 3, keep chunk 1)
        # - guide.pdf page 5
        # - data.csv N/A
        # - report.pdf page 13
        assert len(citations) == 4
        assert citations[0].document_name == "report.pdf"
        assert citations[0].page == "12"
        assert citations[0].quote == "Main finding."
        assert citations[1].document_name == "guide.pdf"
        assert citations[2].document_name == "data.csv"
        assert citations[2].page == "N/A"
        assert citations[3].document_name == "report.pdf"
        assert citations[3].page == "13"
