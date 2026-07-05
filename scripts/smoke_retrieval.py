"""Manual retrieval smoke test — DEV-ONLY, not part of the automated suite.

Runs the real :class:`DenseRetriever` against a live Qdrant + PostgreSQL with an
already-ingested corpus and prints the retrieved chunks for sample questions, so
a developer can eyeball retrieval quality **before** any LLM stage exists.

This intentionally lives outside ``tests/`` because it needs real services and
downloads the embedding model — it must never run in the offline unit suite
(DL-014). It can be deleted once retrieval is verified.

Usage (services running, corpus ingested):
    python scripts/smoke_retrieval.py                 # built-in sample questions
    python scripts/smoke_retrieval.py "your question"  # ask a specific question
"""

from __future__ import annotations

import asyncio
import sys

from atlasiq.backend.core.config import load_settings
from atlasiq.backend.repositories.document_repository import DocumentRepository
from atlasiq.database.postgres_client import PostgresClient
from atlasiq.database.qdrant_client import QdrantVectorClient
from atlasiq.ingestion.embedder import DocumentEmbedder
from atlasiq.retrieval.dense_retriever import DenseRetriever

_SAMPLE_QUESTIONS = [
    "What is the main topic of this document?",
    "Summarize the key points.",
]

_PREVIEW_CHARS = 200


async def _run(questions: list[str]) -> None:
    settings = load_settings()

    qdrant = QdrantVectorClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        collection_name=settings.qdrant.collection_name,
        vector_size=settings.qdrant.vector_size,
    )
    embedder = DocumentEmbedder(settings.embedding)
    retriever = DenseRetriever(qdrant, embedder, settings.retrieval.dense_top_k)

    postgres = PostgresClient(
        dsn=settings.database.dsn,
        pool_min_size=settings.database.pool_min_size,
        pool_max_size=settings.database.pool_max_size,
    )
    repo = DocumentRepository(postgres)

    try:
        for question in questions:
            print(f"\n=== Q: {question} ===")
            refs = retriever.retrieve(question)
            if not refs:
                print("  (no chunks retrieved)")
                continue

            chunks = await repo.get_chunks_by_ids([ref.chunk_id for ref in refs])
            by_id = {chunk.id: chunk for chunk in chunks}

            for rank, ref in enumerate(refs, start=1):
                chunk = by_id.get(ref.chunk_id)
                preview = (
                    chunk.content[:_PREVIEW_CHARS].replace("\n", " ") + "…"
                    if chunk
                    else "<chunk text not found in PostgreSQL>"
                )
                print(
                    f"  [{rank:>2}] score={ref.score:.4f} "
                    f"doc={ref.document_id} idx={ref.chunk_index}"
                )
                print(f"       {preview}")
    finally:
        await postgres.close()
        qdrant.close()


def main() -> None:
    args = sys.argv[1:]
    questions = args if args else _SAMPLE_QUESTIONS
    asyncio.run(_run(questions))


if __name__ == "__main__":
    main()
