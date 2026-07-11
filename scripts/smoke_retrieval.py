"""Manual retrieval smoke test — DEV-ONLY, not part of the automated suite.

Runs the real Dense, BM25, and Hybrid (RRF) retrievers against a live
Qdrant + PostgreSQL with an already-ingested corpus and prints, per sample
question, the ranked results of each retriever side by side — so a developer can
visually compare retrieval quality **before** any LLM stage exists.

This intentionally lives outside ``tests/`` because it needs real services and
downloads the embedding model — it must never run in the offline unit suite
(DL-014). It performs no assertions and can be deleted once retrieval is
verified.

Usage (services running, corpus ingested):
    python scripts/smoke_retrieval.py                 # built-in sample questions
    python scripts/smoke_retrieval.py "your question"  # ask a specific question
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from atlasiq.backend.core.config import load_settings
from atlasiq.backend.repositories.document_repository import DocumentRepository
from atlasiq.database.postgres_client import PostgresClient
from atlasiq.database.qdrant_client import QdrantVectorClient
from atlasiq.ingestion.embedder import DocumentEmbedder
from atlasiq.retrieval.bm25_retriever import BM25Retriever
from atlasiq.retrieval.dense_retriever import DenseRetriever
from atlasiq.retrieval.hybrid_retriever import HybridRetriever

if TYPE_CHECKING:
    from atlasiq.backend.domain import ChunkRecord
    from atlasiq.retrieval.models import ScoredChunkRef

_SAMPLE_QUESTIONS = [
    "What is the main topic of this document?",
    "Summarize the key points.",
]

_PREVIEW_CHARS = 160
_DISPLAY_LIMIT = 8  # cap results shown per section for readability


def _show(label: str, refs: list[ScoredChunkRef], by_id: dict[str, ChunkRecord]) -> None:
    """Print a labelled, ranked section of retrieval results."""
    print(f"\n{label}")
    print("-" * len(label))
    if not refs:
        print("  (no results)")
        return
    for rank, ref in enumerate(refs[:_DISPLAY_LIMIT], start=1):
        chunk = by_id.get(ref.chunk_id)
        preview = (
            chunk.content[:_PREVIEW_CHARS].replace("\n", " ") + "…"
            if chunk
            else "<chunk text not found in PostgreSQL>"
        )
        print(f"  [{rank:>2}] score={ref.score:.4f} doc={ref.document_id} idx={ref.chunk_index}")
        print(f"       {preview}")


async def _run(questions: list[str]) -> None:
    settings = load_settings()

    qdrant = QdrantVectorClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        collection_name=settings.qdrant.collection_name,
        vector_size=settings.qdrant.vector_size,
    )
    embedder = DocumentEmbedder(settings.embedding)
    postgres = PostgresClient(
        dsn=settings.database.dsn,
        pool_min_size=settings.database.pool_min_size,
        pool_max_size=settings.database.pool_max_size,
    )
    repo = DocumentRepository(postgres)

    dense = DenseRetriever(qdrant, embedder, settings.retrieval.dense_top_k)

    # BM25 indexes the full corpus in memory; keep the chunks for text previews.
    all_chunks = await repo.list_all_chunks()
    by_id = {chunk.id: chunk for chunk in all_chunks}
    bm25 = BM25Retriever(settings.retrieval.bm25_top_k)
    bm25.index(all_chunks)

    hybrid = HybridRetriever(
        retrievers=[dense, bm25],
        rrf_k=settings.retrieval.rrf_k,
        default_top_k=settings.retrieval.hybrid_top_k,
    )

    try:
        for question in questions:
            print("\n" + "=" * 70)
            print("QUESTION")
            print("--------")
            print(question)
            _show("DENSE", dense.retrieve(question), by_id)
            _show("BM25", bm25.retrieve(question), by_id)
            _show("HYBRID", hybrid.retrieve(question), by_id)
    finally:
        await postgres.close()
        qdrant.close()


def main() -> None:
    args = sys.argv[1:]
    questions = args if args else _SAMPLE_QUESTIONS
    asyncio.run(_run(questions))


if __name__ == "__main__":
    main()
