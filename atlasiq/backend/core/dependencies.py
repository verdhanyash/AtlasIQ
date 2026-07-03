"""FastAPI dependency injection providers.

Centralized dependency factories for database clients, services, and
configuration. FastAPI routes use `Depends()` to receive these — keeping
route handlers free of construction logic.
"""

from __future__ import annotations

import logging
from functools import lru_cache

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
