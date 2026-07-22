"""BM25 lexical (sparse) retriever.

Ranks chunks by keyword overlap with the query using Okapi BM25
(``rank_bm25.BM25Okapi``) and emits the same :class:`ScoredChunkRef` shape as
the dense retriever, so the hybrid retriever (M2-5) can fuse dense + lexical
results uniformly.

The retriever is intentionally **pure**: it indexes and searches an
already-provided corpus and never touches PostgreSQL, Qdrant, or the network.
The composition root supplies the corpus (``await repo.list_all_chunks()`` →
``bm25.index(chunks)``); loading data is not this component's responsibility
(SRP). The index is in-memory only — no persistence, no incremental updates.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from atlasiq.backend.core.exceptions import RetrievalError
from atlasiq.retrieval.models import ScoredChunkRef

if TYPE_CHECKING:
    from atlasiq.backend.domain import ChunkRecord

logger = logging.getLogger(__name__)

# Common English stop words to filter out of BM25 index.
# These are high-frequency words that rarely carry semantic meaning and cause
# false lexical matches (e.g., "India" in "Distribution: India, China" should not
# match queries about "president of india" when other context words don't match).
# This is a minimal curated list focused on reducing false positives while
# preserving legitimate keyword searches.
_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "will", "with", "the", "this", "but", "they", "have",
    "had", "what", "when", "where", "who", "which", "why", "how",
})

# Tokenizer shared by corpus and query: lowercase, split on word characters,
# filter common stop words. BM25's IDF still handles term frequency, but
# removing stop words prevents spurious matches on high-frequency function words.
_TOKEN_PATTERN = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase word tokens, filtering stop words.

    Args:
        text: The text to tokenize.

    Returns:
        A list of lowercase ``\\w+`` tokens with common stop words removed.
    """
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


class BM25Retriever:
    """Lexical retriever over an in-memory Okapi BM25 index.

    The corpus is supplied via :meth:`index`; the retriever performs no data
    access of its own. ``default_top_k`` sets the result count when a caller
    does not override it per query.
    """

    def __init__(self, default_top_k: int) -> None:
        """Initialise the retriever.

        Args:
            default_top_k: Default number of results when ``top_k`` is omitted.
        """
        self._default_top_k = default_top_k
        self._bm25: Any = None
        self._chunks: list[ChunkRecord] = []
        self._indexed = False

    def index(self, chunks: list[ChunkRecord]) -> None:
        """(Re)build the in-memory BM25 index over the given chunks.

        Fully replaces any previous index, tokenized corpus, and chunk mapping.
        An empty corpus is valid: the retriever becomes "indexed but empty" and
        subsequent :meth:`retrieve` calls return an empty list.

        Args:
            chunks: The chunks to index (their ``content`` is tokenized).
        """
        self._chunks = list(chunks)
        if self._chunks:
            tokenized_corpus = [_tokenize(chunk.content) for chunk in self._chunks]
            self._bm25 = BM25Okapi(tokenized_corpus)
        else:
            self._bm25 = None
        self._indexed = True
        logger.info("BM25 index built over %d chunks", len(self._chunks))

    def retrieve(self, question: str, top_k: int | None = None) -> list[ScoredChunkRef]:
        """Retrieve chunks lexically most relevant to the question.

        Args:
            question: The natural-language query.
            top_k: Maximum results to return; falls back to the configured
                default when ``None``.

        Returns:
            Scored chunk references in descending score order (ties broken by
            corpus position for determinism). Only positive-score chunks are
            returned; the list may be shorter than ``top_k`` (or empty).

        Raises:
            RetrievalError: If called before :meth:`index`.
        """
        if not self._indexed:
            msg = "BM25 index not built; call index() before retrieve()"
            raise RetrievalError(msg)

        if self._bm25 is None or not self._chunks:
            return []

        query_tokens = _tokenize(question)
        if not query_tokens:
            return []

        k = top_k if top_k is not None else self._default_top_k

        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(
            ((position, float(score)) for position, score in enumerate(scores) if score > 0.0),
            key=lambda pair: (-pair[1], pair[0]),
        )

        return [self._to_ref(self._chunks[position], score) for position, score in ranked[:k]]

    @staticmethod
    def _to_ref(chunk: ChunkRecord, score: float) -> ScoredChunkRef:
        """Map an indexed chunk and its score to a :class:`ScoredChunkRef`."""
        return ScoredChunkRef(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            score=score,
        )
