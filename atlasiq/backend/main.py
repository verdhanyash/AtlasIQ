"""AtlasIQ FastAPI application entry point.

Creates the FastAPI app with lifespan management, router registration,
CORS middleware, and global exception handling. The application follows
an app factory pattern for testability.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from atlasiq.backend.api.routes_health import router as health_router
from atlasiq.backend.core.config import Settings
from atlasiq.backend.core.dependencies import (
    get_postgres_client,
    get_qdrant_client,
    get_settings,
)
from atlasiq.backend.core.exceptions import AtlasIQError, StartupError
from atlasiq.backend.core.logging import setup_logging
from atlasiq.backend.core.startup import run_startup_checks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage application startup and shutdown lifecycle.

    On startup:
        - Configures structured logging
        - Runs all startup validation checks
        - Initializes database schemas and collections

    On shutdown:
        - Closes database connection pools
        - Releases resources
    """
    settings = get_settings()
    setup_logging(level=settings.logging.level, log_format=settings.logging.format)

    logger.info("AtlasIQ starting up...")

    postgres_client = get_postgres_client()
    qdrant_client = get_qdrant_client()

    try:
        await run_startup_checks(settings, postgres_client, qdrant_client)
    except (StartupError, Exception) as e:
        logger.critical("Startup failed: %s", e)
        raise

    logger.info("AtlasIQ is ready — serving on %s:%d", settings.server.host, settings.server.port)

    yield

    # Shutdown
    logger.info("AtlasIQ shutting down...")
    await postgres_client.close()
    qdrant_client.close()
    logger.info("AtlasIQ shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI instance with all routers and middleware.
    """
    app = FastAPI(
        title="AtlasIQ",
        description=(
            "Enterprise Knowledge Platform — continuous ingestion, hybrid retrieval, "
            "evidence-backed answers with citations and confidence scoring."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ───────────────────────────────────────────────

    @app.exception_handler(AtlasIQError)
    async def atlasiq_error_handler(request: Request, exc: AtlasIQError) -> JSONResponse:
        """Handle all AtlasIQ domain exceptions with structured error responses."""
        logger.error("Domain error: %s", exc.message)
        return JSONResponse(
            status_code=400,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions with a generic error response."""
        logger.exception("Unexpected error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "message": "An unexpected error occurred"},
        )

    # ── Routers ──────────────────────────────────────────────────────────

    app.include_router(health_router)

    # Future milestone routers will be registered here:
    # app.include_router(documents_router, prefix="/documents")
    # app.include_router(query_router, prefix="/query")
    # app.include_router(analytics_router, prefix="/analytics")
    # app.include_router(evaluation_router, prefix="/evaluation")

    return app


# Module-level app instance — used by uvicorn
app = create_app()
