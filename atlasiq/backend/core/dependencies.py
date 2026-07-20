"""FastAPI dependency injection providers.

Centralized dependency factories for database clients, services, and
configuration. FastAPI routes use `Depends()` to receive these — keeping
route handlers free of construction logic.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from atlasiq.backend.core.config import Settings, load_settings
from atlasiq.backend.repositories.document_repository import DocumentRepository
from atlasiq.backend.repositories.vector_repository import ChunkVectorRepository
from atlasiq.database.postgres_client import PostgresClient
from atlasiq.database.qdrant_client import QdrantVectorClient
from atlasiq.ingestion.change_detector import ChangeDetector
from atlasiq.ingestion.chunker import DocumentChunker
from atlasiq.ingestion.embedder import DocumentEmbedder
from atlasiq.ingestion.parser import DocumentParser
from atlasiq.ingestion.pipeline import IngestionPipeline
from atlasiq.ingestion.validator import DocumentValidator
from atlasiq.retrieval.bm25_retriever import BM25Retriever
from atlasiq.retrieval.citations import CitationBuilder
from atlasiq.retrieval.dense_retriever import DenseRetriever
from atlasiq.retrieval.generator import AnswerGenerator
from atlasiq.retrieval.guardrails import Guardrails
from atlasiq.retrieval.hybrid_retriever import HybridRetriever
from atlasiq.retrieval.llm.factory import create_llm_provider
from atlasiq.retrieval.prompt_builder import PromptBuilder
from atlasiq.retrieval.qa_pipeline import QueryPipeline

if TYPE_CHECKING:
    from atlasiq.retrieval.llm.base import LLMProvider

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Provide the application settings singleton.

    Returns:
        The Settings instance, loaded once and cached.
    """
    return load_settings()


@lru_cache(maxsize=1)
def get_postgres_client() -> PostgresClient:
    """Provide the PostgreSQL client singleton.

    Returns:
        A configured PostgresClient instance.
    """
    settings = get_settings()
    return PostgresClient(
        dsn=settings.database.dsn,
        pool_min_size=settings.database.pool_min_size,
        pool_max_size=settings.database.pool_max_size,
    )


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantVectorClient:
    """Provide the Qdrant client singleton.

    Returns:
        A configured QdrantVectorClient instance.
    """
    settings = get_settings()
    return QdrantVectorClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        collection_name=settings.qdrant.collection_name,
        vector_size=settings.qdrant.vector_size,
    )


@lru_cache(maxsize=1)
def get_document_repository() -> DocumentRepository:
    """Provide the document repository singleton.

    Returns:
        A DocumentRepository wired to the PostgreSQL client.
    """
    return DocumentRepository(get_postgres_client())


@lru_cache(maxsize=1)
def get_ingestion_pipeline() -> IngestionPipeline:
    """Provide the ingestion pipeline singleton.

    Composes all pipeline collaborators from existing client singletons and
    configuration. This is the only place where the full pipeline is assembled.

    Returns:
        A fully wired IngestionPipeline.
    """
    settings = get_settings()
    return IngestionPipeline(
        validator=DocumentValidator(settings.ingestion),
        change_detector=ChangeDetector(),
        parser=DocumentParser(),
        chunker=DocumentChunker(settings.chunking),
        embedder=DocumentEmbedder(settings.embedding),
        document_repo=get_document_repository(),
        vector_repo=ChunkVectorRepository(get_qdrant_client()),
    )


# ── Retrieval & QA Dependencies ──────────────────────────────────────────────


_bm25_retriever: BM25Retriever | None = None
_bm25_retriever_lock = asyncio.Lock()


@lru_cache(maxsize=1)
def get_embedder() -> DocumentEmbedder:
    """Provide the document embedder singleton."""
    return DocumentEmbedder(get_settings().embedding)


@lru_cache(maxsize=1)
def get_dense_retriever() -> DenseRetriever:
    """Provide the dense semantic retriever singleton."""
    settings = get_settings()
    return DenseRetriever(
        qdrant_client=get_qdrant_client(),
        embedder=get_embedder(),
        default_top_k=settings.retrieval.dense_top_k,
    )


async def get_bm25_retriever() -> BM25Retriever:
    """Provide the in-memory BM25 retriever indexed with all document chunks."""
    global _bm25_retriever
    if _bm25_retriever is not None:
        logger.debug("Reusing cached BM25Retriever instance")
        return _bm25_retriever

    # The BM25 index is in-memory only and requires a full database read to populate.
    # We use an async lock to serialize initialization across concurrent requests on
    # first startup, preventing redundant DB reads and index rebuilding. Once populated,
    # the retriever is cached as a singleton for sub-millisecond retrieval latency.
    async with _bm25_retriever_lock:
        if _bm25_retriever is not None:
            logger.debug("Reusing cached BM25Retriever instance")
            return _bm25_retriever

        logger.debug("Building BM25 index")
        settings = get_settings()
        repo = get_document_repository()

        retriever = BM25Retriever(default_top_k=settings.retrieval.bm25_top_k)
        all_chunks = await repo.list_all_chunks()
        retriever.index(all_chunks)

        logger.info("BM25 index rebuilt")
        _bm25_retriever = retriever
        return _bm25_retriever


async def get_hybrid_retriever() -> HybridRetriever:
    """Provide the hybrid retriever combining dense and BM25 search."""
    settings = get_settings()
    dense_retriever = get_dense_retriever()
    bm25_retriever = await get_bm25_retriever()
    return HybridRetriever(
        retrievers=[dense_retriever, bm25_retriever],
        rrf_k=settings.retrieval.rrf_k,
        default_top_k=settings.retrieval.hybrid_top_k,
    )


@lru_cache(maxsize=1)
def get_prompt_builder() -> PromptBuilder:
    """Provide the prompt builder singleton."""
    settings = get_settings()
    prompts_dir = Path(settings.prompts.directory)
    if not prompts_dir.is_absolute():
        from atlasiq.backend.core.config import PROJECT_ROOT

        prompts_dir = PROJECT_ROOT / prompts_dir
    return PromptBuilder(
        prompts_dir=prompts_dir,
        qa_template=settings.prompts.qa_template,
        system_template=settings.prompts.system_template,
    )


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Provide the LLM provider singleton."""
    settings = get_settings()
    return create_llm_provider(
        llm_config=settings.llm,
        ollama_config=settings.ollama,
        nvidia_config=settings.nvidia,
    )


@lru_cache(maxsize=1)
def get_answer_generator() -> AnswerGenerator:
    """Provide the answer generator singleton."""
    return AnswerGenerator(llm_provider=get_llm_provider())


@lru_cache(maxsize=1)
def get_citation_builder() -> CitationBuilder:
    """Provide the citation builder singleton."""
    return CitationBuilder()


@lru_cache(maxsize=1)
def get_guardrails() -> Guardrails:
    """Provide the guardrails singleton."""
    settings = get_settings()
    return Guardrails(min_confidence_score=settings.retrieval.min_confidence_score)


_query_pipeline: QueryPipeline | None = None
_query_pipeline_lock = asyncio.Lock()


async def get_query_pipeline() -> QueryPipeline:
    """Provide the query pipeline singleton."""
    global _query_pipeline
    if _query_pipeline is not None:
        return _query_pipeline

    async with _query_pipeline_lock:
        if _query_pipeline is not None:
            return _query_pipeline

        hybrid_retriever = await get_hybrid_retriever()
        document_repo = get_document_repository()
        prompt_builder = get_prompt_builder()
        answer_generator = get_answer_generator()
        citation_builder = get_citation_builder()
        guardrails = get_guardrails()
        _query_pipeline = QueryPipeline(
            hybrid_retriever=hybrid_retriever,
            document_repo=document_repo,
            prompt_builder=prompt_builder,
            answer_generator=answer_generator,
            citation_builder=citation_builder,
            guardrails=guardrails,
        )
        return _query_pipeline


async def invalidate_bm25_retriever() -> None:
    """Clear the cached BM25 retriever and query pipeline singletons.

    Forces a lazy rebuild of the BM25 index and QueryPipeline on the next query
    using the updated corpus database state.

    This operation is synchronized with the initialization locks to prevent race
    conditions where invalidation occurs while initialization is in progress.
    """
    global _bm25_retriever, _query_pipeline

    # Acquire both locks in a consistent order to prevent races with initialization
    async with _bm25_retriever_lock, _query_pipeline_lock:
        _bm25_retriever = None
        _query_pipeline = None
        logger.debug("BM25 cache invalidation completed under synchronization")

    logger.info("BM25 cache invalidated")
