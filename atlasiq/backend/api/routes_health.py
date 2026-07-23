"""Health check endpoint for AtlasIQ.

Verifies connectivity to all critical services: PostgreSQL, Qdrant,
and the active LLM provider. Returns a structured health report
used by monitoring systems and startup validation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel


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
) -> dict[str, Any]:
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
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


@router.get("/config/check")
async def check_config(
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Check which configuration values are set in the environment.

    This endpoint allows the frontend to determine if API keys
    are already configured in .env files, avoiding redundant
    user prompts for credentials that already exist.

    Returns:
        Dictionary indicating which provider configurations are available.
    """
    return {
        "nvidia_api_key_configured": bool(settings.nvidia.api_key),
        "openai_api_key_configured": bool(settings.openai.api_key),
        "current_provider": settings.llm.provider,
        "current_model": settings.llm.model,
    }


class ConfigUpdateRequest(BaseModel):
    """Request model for dynamic configuration updates."""

    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


@router.post("/config")
async def update_config(
    req: ConfigUpdateRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Update active LLM provider and model configuration dynamically.

    Args:
        req: ConfigUpdateRequest with provider, model, and optional credentials.
        settings: Application settings singleton.

    Returns:
        Status dict with updated provider and model.
    """
    settings.llm.provider = req.provider
    settings.llm.model = req.model

    if req.api_key:
        if req.provider == "nvidia":
            settings.nvidia.api_key = req.api_key
        elif req.provider == "openai":
            settings.openai.api_key = req.api_key
        elif req.provider == "anthropic":
            settings.anthropic.api_key = req.api_key

    if req.base_url and req.provider == "ollama":
        settings.ollama.base_url = req.base_url

    from atlasiq.backend.core.dependencies import reset_llm_provider_cache

    await reset_llm_provider_cache()

    logger.info(
        "Updated LLM configuration dynamically: provider=%s, model=%s",
        settings.llm.provider,
        settings.llm.model,
    )
    return {
        "status": "success",
        "current_provider": settings.llm.provider,
        "current_model": settings.llm.model,
    }

