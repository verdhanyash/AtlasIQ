"""Retrieval domain models.

Framework-independent value objects that describe retrieval results as they
move through the query pipeline (consistent with the domain-record approach in
DL-017 — no persistence behaviour, no knowledge of Qdrant or PostgreSQL).

Two shapes, reflecting the retrieval → hydration boundary:

* :class:`ScoredChunkRef` — what a retriever emits: a reference to a chunk plus
  its relevance score, *before* the chunk text is fetched. Retrievers only know
  identity + score because the Qdrant payload stores just ``document_id`` and
  ``chunk_index``.
* :class:`RetrievedChunk` — the hydrated form: the full :class:`ChunkRecord`
  (content + page range) joined with its owning document's filename and score,
  ready for prompt construction and citation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlasiq.backend.domain import ChunkRecord


@dataclass(frozen=True, slots=True)
class ScoredChunkRef:
    """A reference to a retrieved chunk plus its relevance score.

    Emitted by the dense, BM25, and hybrid retrievers before hydration. Carries
    only what a retriever knows; the chunk text and page metadata are fetched
    later from PostgreSQL (the source of truth).

    Attributes:
        chunk_id: The chunk's deterministic id (the join key across both stores).
        document_id: Id of the owning document.
        chunk_index: Zero-based position of the chunk within the document.
        score: Relevance score assigned by the retriever (higher is better).
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A hydrated retrieval result, ready for prompting and citation.

    Pairs the full chunk record (content, page numbers, metadata) with the
    owning document's filename and the retriever's relevance score. The prompt
    builder formats this into context; the citation builder turns it into
    ``[Source: file, Page: N]`` references.

    Attributes:
        chunk: The full chunk record (content + page range).
        filename: Filename of the owning document (for citations/display).
        score: Relevance score carried over from retrieval.
    """

    chunk: ChunkRecord
    filename: str
    score: float
