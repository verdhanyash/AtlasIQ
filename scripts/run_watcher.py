"""Run the optional folder watcher — DEV/DEMO tool.

Starts :class:`FolderWatcher` on the configured ``watched_documents/`` directory
and ingests any file dropped into it through the real ingestion pipeline
(validate → parse → chunk → embed → store). This is the manual entry point for
the optional watcher whose app-lifespan wiring is deferred (DL-005/8C).

Prerequisites:
    * PostgreSQL + Qdrant running:  docker compose up -d postgres qdrant
    * Internet on first run (downloads the ~550 MB embedding model)

Usage:
    python scripts/run_watcher.py      # then drop files into watched_documents/
    # Ctrl+C to stop.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from atlasiq.backend.core.config import load_settings
from atlasiq.backend.core.dependencies import (
    get_ingestion_pipeline,
    get_postgres_client,
    get_qdrant_client,
)
from atlasiq.ingestion.watcher import FolderWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("run_watcher")


async def _main() -> None:
    settings = load_settings()

    # Make sure the stores are ready before we start watching.
    postgres = get_postgres_client()
    await postgres.initialize_schema()
    qdrant = get_qdrant_client()
    qdrant.ensure_collection()

    pipeline = get_ingestion_pipeline()  # reuses the same client singletons
    watcher = FolderWatcher(settings.ingestion.watched_folder, pipeline)
    watcher.start(asyncio.get_running_loop())

    logger.info(
        "Watching '%s' — drop a file there to ingest it. Press Ctrl+C to stop.",
        settings.ingestion.watched_folder,
    )
    try:
        await asyncio.Event().wait()  # run until interrupted
    finally:
        watcher.stop()
        await postgres.close()
        qdrant.close()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_main())
