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
    """

    document_name: str
    page: str
    quote: str


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

    def build(self, chunks: Sequence[RetrievedChunk]) -> list[Citation]:
        """Build citations from the retrieved chunks.

        The chunks are deduplicated by ``(filename, page)`` — if multiple chunks
        from the same document page were retrieved, only the highest-scoring one
        is cited (presumed most relevant). The quote is taken from that chunk's
        content.

        Citations appear in the order of **first occurrence** of each unique
        ``(document, page)`` pair in the input, even when a later chunk wins
        the dedup (higher score).

        Args:
            chunks: The hydrated retrieved chunks (the same ones shown to the
                LLM in the prompt context). Typically pre-sorted by score
                descending, but the builder handles any order.

        Returns:
            A list of ``Citation`` objects, deduplicated, preserving the order
            of first appearance in the input.
        """
        if not chunks:
            logger.debug("No chunks to cite — returning empty citation list")
            return []

        logger.debug("Building citations from %d chunk(s)", len(chunks))

        # Track best chunk per (filename, page) and first appearance index
        best_chunk: dict[tuple[str, str], RetrievedChunk] = {}
        first_seen: dict[tuple[str, str], int] = {}

        for idx, chunk in enumerate(chunks):
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
                )
            )

        logger.info("Built %d citation(s) from %d chunk(s)", len(citations), len(chunks))
        return citations
