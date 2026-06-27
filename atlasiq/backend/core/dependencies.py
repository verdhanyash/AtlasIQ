"""FastAPI dependency injection providers.

Centralized dependency factories for database clients, services, and
configuration. FastAPI routes use `Depends()` to receive these — keeping
route handlers free of construction logic.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from atlasiq.backend.core.config import Settings, load_settings
from atlasiq.database.postgres_client import PostgresClient
from atlasiq.database.qdrant_client import QdrantVectorClient

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
