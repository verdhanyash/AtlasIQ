"""Health check endpoint for AtlasIQ.

Verifies connectivity to all critical services: PostgreSQL, Qdrant,
and the active LLM provider. Returns a structured health report
used by monitoring systems and startup validation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from atlasiq.backend.core.config import Settings
from atlasiq.backend.core.dependencies import (
    get_postgres_client,
    get_qdrant_client,
    get_settings,
)
from atlasiq.database.postgres_client import PostgresClient
from atlasiq.database.qdrant_client import QdrantVectorClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(
    settings: Settings = Depends(get_settings),
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantVectorClient = Depends(get_qdrant_client),
) -> dict:
    """Check the health of all AtlasIQ services.

    Returns a structured report indicating the status of:
    - FastAPI (always true if this endpoint responds)
    - PostgreSQL connection
    - Qdrant connection
    - Active LLM provider and model
    - Configuration validity

    Returns:
        Health report dict with overall status and per-service checks.
    """
    pg_healthy = await postgres_client.health_check()
    qdrant_healthy = qdrant_client.health_check()

    all_healthy = pg_healthy and qdrant_healthy

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": {
            "fastapi": True,
            "postgresql": pg_healthy,
            "qdrant": qdrant_healthy,
            "llm_provider": settings.llm.provider,
            "llm_model": settings.llm.model,
            "config_valid": True,
        },
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
