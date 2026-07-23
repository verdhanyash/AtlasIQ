"""Citation builder — structured references from retrieved chunks.

Produces structured ``Citation`` objects from the hydrated chunks used during
answer generation. Each citation contains:

* Document name (for "Source: filename" display)
* Page reference (single page, page range, or ``N/A``)
* Supporting quote (the chunk content that backs the answer)

Citations are assembled **deterministically** from the retrieved chunks — no
LLM calls, no heuristics. The builder deduplicates by ``(document, page)`` so
that repeated references to the same page produce one citation (with the
highest-scoring chunk as the quote).

This satisfies the "evidence-backed answers" principle: every citation maps
directly to a chunk that was part of the prompt context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from atlasiq.retrieval.models import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Citation:
    """A structured reference to a source document and passage.

    Ready for UI display (``[Source: filename, Page: N] "quoted text"``).

    Attributes:
        document_name: Filename of the source document.
        page: Human-readable page reference (e.g. ``"12"``, ``"12-14"``,
            or ``"N/A"`` for non-paginated sources).
        quote: The supporting passage from the chunk content.
        chunk_index: Zero-based chunk index within the document.
        score: Retrieval score (RRF or final relevance score).
    """

    document_name: str
    page: str
    quote: str
    chunk_index: int = 0
    score: float = 0.0


def _format_page_range(start_page: int | None, end_page: int | None) -> str:
    """Render a chunk's page range: ``12``, ``12-14``, or ``N/A``.

    Args:
        start_page: Optional starting page number.
        end_page: Optional ending page number.

    Returns:
        A human-readable page reference string.
    """
    if start_page is None:
        return "N/A"
    if end_page is not None and end_page != start_page:
        return f"{start_page}-{end_page}"
    return str(start_page)


def _dedup_key(chunk: RetrievedChunk) -> tuple[str, str]:
    """Produce a deduplication key for a chunk: (filename, page_string).

    Multiple chunks from the same document+page are considered duplicates;
    we keep only the highest-scoring one.

    Args:
        chunk: A hydrated retrieved chunk.

    Returns:
        A tuple ``(filename, page_string)`` for dedup tracking.
    """
    page = _format_page_range(chunk.chunk.start_page, chunk.chunk.end_page)
    return (chunk.filename, page)


class CitationBuilder:
    """Builds structured citations from retrieved chunks.

    Operates on the **hydrated** chunks that were used in the prompt (the same
    chunks the LLM saw). Deduplicates by ``(document, page)`` and produces a
    list of ``Citation`` objects ready for UI rendering.

    No LLM calls, no external dependencies — pure deterministic assembly.
    """

    def build(self, chunks: Sequence[RetrievedChunk], top_k: int = 10) -> list[Citation]:
        """Build citations from the retrieved chunks.

        The chunks are deduplicated by ``(filename, page)`` — if multiple chunks
        from the same document page were retrieved, only the highest-scoring one
        is cited (presumed most relevant). The quote is taken from that chunk's
        content.

        Citations appear in the order of **first occurrence** of each unique
        ``(document, page)`` pair in the input, even when a later chunk wins
        the dedup (higher score).

        **Filtering**: Only the top-k highest-scoring chunks are considered for
        citation building. This prevents low-ranked, weakly-related chunks from
        appearing as citations. Default top_k=10 means only rank 1-10 chunks
        can be cited.

        Args:
            chunks: The hydrated retrieved chunks (the same ones shown to the
                LLM in the prompt context). Typically pre-sorted by score
                descending, but the builder handles any order.
            top_k: Maximum number of top-ranked chunks to consider for citations.
                Lower-ranked chunks (beyond top_k) are excluded from citations
                even if they were part of the retrieval context. Default 10.

        Returns:
            A list of ``Citation`` objects, deduplicated, preserving the order
            of first appearance in the input.
        """
        if not chunks:
            logger.debug("No chunks to cite — returning empty citation list")
            return []

        # Filter to only top-k highest-scoring chunks for citation
        # This prevents weakly-related chunks from being cited
        # Step 1: Identify top-k by score, filtering out weak outliers (<55% of top score)
        top_k_chunks_by_score = sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]
        top_score = top_k_chunks_by_score[0].score if top_k_chunks_by_score else 0.0

        top_k_ids = set()
        for c in top_k_chunks_by_score:
            # If top score is dominant (>= 0.02), filter out chunks scoring less than 55% of top score
            if top_score >= 0.02 and c.score < top_score * 0.55:
                continue
            top_k_ids.add(c.chunk.id)

        # Step 2: Filter original list preserving input order
        top_chunks = [c for c in chunks if c.chunk.id in top_k_ids]

        logger.debug("Building citations from %d chunk(s) (filtered to top %d)", len(chunks), len(top_chunks))


        # DIAGNOSTIC: Log top chunks being considered for citation
        logger.debug("CITATION BUILDER INPUT (top %d):", len(top_chunks))
        for idx, chunk in enumerate(top_chunks):
            key = _dedup_key(chunk)
            logger.debug(
                "  CITE_IN[%d]: file=%s, page=%s, chunk_idx=%d, score=%.6f",
                idx,
                chunk.filename,
                _format_page_range(chunk.chunk.start_page, chunk.chunk.end_page),
                chunk.chunk.chunk_index,
                chunk.score,
            )

        # Track best chunk per (filename, page) and first appearance index
        best_chunk: dict[tuple[str, str], RetrievedChunk] = {}
        first_seen: dict[tuple[str, str], int] = {}

        for idx, chunk in enumerate(top_chunks):
            key = _dedup_key(chunk)
            # Track first occurrence
            if key not in first_seen:
                first_seen[key] = idx
            # Track highest-scoring chunk
            if key not in best_chunk or chunk.score > best_chunk[key].score:
                best_chunk[key] = chunk

        # Build citations sorted by first appearance
        sorted_keys = sorted(best_chunk.keys(), key=lambda k: first_seen[k])
        citations = []
        for key in sorted_keys:
            chunk = best_chunk[key]
            page_ref = _format_page_range(chunk.chunk.start_page, chunk.chunk.end_page)
            citations.append(
                Citation(
                    document_name=chunk.filename,
                    page=page_ref,
                    quote=chunk.chunk.content.strip(),
                    chunk_index=chunk.chunk.chunk_index,
                    score=chunk.score,
                )
            )

        logger.info("Built %d citation(s) from top %d of %d chunk(s)", len(citations), len(top_chunks), len(chunks))
        return citations
