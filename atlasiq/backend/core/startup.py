"""Startup validation for AtlasIQ.

Verifies all required services, configuration, and resources before the
application begins serving requests. Fails fast with clear error messages
so misconfigurations are caught immediately rather than at runtime.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from atlasiq.backend.core.config import PROJECT_ROOT, Settings
from atlasiq.backend.core.exceptions import ConfigurationError, StartupError

if TYPE_CHECKING:
    from atlasiq.database.postgres_client import PostgresClient
    from atlasiq.database.qdrant_client import QdrantVectorClient

logger = logging.getLogger(__name__)


async def validate_configuration(settings: Settings) -> None:
    """Validate that configuration values are consistent and complete.

    Args:
        settings: The application settings to validate.

    Raises:
        ConfigurationError: If any configuration is invalid.
    """
    # Validate LLM provider has required API key
    provider = settings.llm.provider

    if provider == "nvidia" and not settings.nvidia.api_key:
        raise ConfigurationError(
            "NVIDIA Build provider selected but ATLASIQ_NVIDIA__API_KEY is not set. "
            "Set it in your .env file or environment."
        )

    if provider == "openai" and not settings.openai.api_key:
        raise ConfigurationError(
            "OpenAI provider selected but ATLASIQ_OPENAI__API_KEY is not set. "
            "Set it in your .env file or environment."
        )

    logger.info("Configuration validated: provider=%s, model=%s", provider, settings.llm.model)


def validate_prompt_templates(settings: Settings) -> None:
    """Verify that all required prompt template files exist.

    Args:
        settings: The application settings containing prompt paths.

    Raises:
        ConfigurationError: If any prompt template file is missing.
    """
    prompts_dir = PROJECT_ROOT / settings.prompts.directory

    required_templates = [
        settings.prompts.qa_template,
        settings.prompts.system_template,
    ]

    for template_name in required_templates:
        template_path = prompts_dir / template_name
        if not template_path.exists():
            raise ConfigurationError(
                f"Required prompt template not found: {template_path}. "
                f"Create it or check prompts.directory in configs/default.yaml."
            )

    logger.info("Prompt templates validated: %d templates found", len(required_templates))


def validate_directories(settings: Settings) -> None:
    """Ensure required directories exist, creating them if necessary.

    Creates the primary document storage directory (for API uploads) and
    the optional watched folder (for the directory watcher ingestion source).

    Args:
        settings: The application settings containing directory paths.
    """
    # Primary storage directory — destination for uploaded documents
    storage_dir = Path(settings.ingestion.storage_dir)
    if not storage_dir.is_absolute():
        storage_dir = PROJECT_ROOT / storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Document storage directory ready: %s", storage_dir)

    # Optional watched folder — for directory watcher ingestion source
    watched_folder = Path(settings.ingestion.watched_folder)
    if not watched_folder.is_absolute():
        watched_folder = PROJECT_ROOT / watched_folder
    watched_folder.mkdir(parents=True, exist_ok=True)
    logger.info("Watched folder ready: %s", watched_folder)


async def validate_postgres(postgres_client: PostgresClient) -> None:
    """Verify PostgreSQL is reachable and schema is initialized.

    Args:
        postgres_client: The PostgreSQL client to check.

    Raises:
        StartupError: If PostgreSQL is unreachable.
    """
    healthy = await postgres_client.health_check()
    if not healthy:
        raise StartupError(
            "PostgreSQL is unreachable. Check ATLASIQ_DATABASE__HOST and "
            "ATLASIQ_DATABASE__PORT, and ensure the database is running."
        )

    await postgres_client.initialize_schema()
    logger.info("PostgreSQL is healthy and schema is initialized")


def validate_qdrant(qdrant_client: QdrantVectorClient) -> None:
    """Verify Qdrant is reachable and the collection is ready.

    Args:
        qdrant_client: The Qdrant client to check.

    Raises:
        StartupError: If Qdrant is unreachable.
    """
    healthy = qdrant_client.health_check()
    if not healthy:
        raise StartupError(
            "Qdrant is unreachable. Check ATLASIQ_QDRANT__HOST and "
            "ATLASIQ_QDRANT__PORT, and ensure Qdrant is running."
        )

    qdrant_client.ensure_collection()
    logger.info("Qdrant is healthy and collection is ready")


async def run_startup_checks(
    settings: Settings,
    postgres_client: PostgresClient,
    qdrant_client: QdrantVectorClient,
) -> None:
    """Run all startup validation checks in sequence.

    This is called during the FastAPI lifespan startup event. If any check
    fails, the application will not start.

    Args:
        settings: Application settings.
        postgres_client: PostgreSQL client.
        qdrant_client: Qdrant client.

    Raises:
        ConfigurationError: If configuration is invalid.
        StartupError: If a required service is unavailable.
    """
    logger.info("Running startup validation checks...")

    await validate_configuration(settings)
    validate_prompt_templates(settings)
    validate_directories(settings)
    await validate_postgres(postgres_client)
    validate_qdrant(qdrant_client)

    logger.info("All startup checks passed — AtlasIQ is ready to serve")
