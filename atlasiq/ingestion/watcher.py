"""Optional folder watcher for the ingestion pipeline.

Monitors a configured directory for new or modified files and dispatches them
to the ingestion pipeline — the **exact same pipeline** the upload API uses
(DL-005). The watcher is a secondary, optional ingestion source; it can be
disabled entirely with zero impact on the rest of the application.

``watchdog`` is imported lazily (DL-009/DL-016 pattern) so the package cost
is only paid when the watcher is actually started. The watcher bridges sync
watchdog callbacks to the async pipeline via ``asyncio.run_coroutine_threadsafe``.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from concurrent.futures import Future

    from atlasiq.ingestion.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)

# Quiet period (seconds) a file must go without further events before it is
# ingested. Coalesces the burst of events a single save produces and lets an
# in-progress write settle before the file is read. A true constant, not a
# user-facing setting.
_DEBOUNCE_SECONDS = 1.5


class FolderWatcher:
    """Watches a directory for new/modified files and triggers ingestion.

    The watcher is designed to be started and stopped explicitly — it does
    not start automatically on import. It can be wired into the app lifespan
    or started manually for local development.

    Attributes:
        watch_path: The directory being monitored.
    """

    def __init__(self, watch_path: str | Path, pipeline: IngestionPipeline) -> None:
        """Initialise the watcher.

        Args:
            watch_path: Path to the directory to monitor.
            pipeline: The ingestion pipeline to dispatch files to.
        """
        self.watch_path = Path(watch_path)
        self._pipeline = pipeline
        self._observer: Any = None
        self._handler: _IngestionHandler | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start watching the configured directory.

        The watch directory is created if it does not exist. The caller must
        pass the running event loop (typically ``asyncio.get_running_loop()``
        from the application's async lifespan) — watchdog callbacks run on a
        separate thread and hand ingestion coroutines back to this loop.

        Args:
            loop: The running event loop to schedule async pipeline calls onto.
        """
        if not self.watch_path.exists():
            self.watch_path.mkdir(parents=True, exist_ok=True)
            logger.info("Created watch directory: %s", self.watch_path)

        self._loop = loop

        observer_cls = self._get_observer_class()
        self._handler = _IngestionHandler(self._pipeline, loop)
        self._observer = observer_cls()
        self._observer.schedule(self._handler, str(self.watch_path), recursive=False)
        self._observer.start()
        logger.info("Folder watcher started on: %s", self.watch_path)

    def stop(self) -> None:
        """Stop the watcher and release resources."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Folder watcher stopped")
        if self._handler is not None:
            self._handler.cancel_all()
            self._handler = None

    @staticmethod
    def _get_observer_class() -> Any:
        """Lazily import watchdog's Observer class.

        Returns:
            The ``watchdog.observers.Observer`` class.

        Raises:
            ImportError: If watchdog is not installed.
        """
        try:
            from watchdog.observers import Observer
        except ImportError as exc:
            msg = (
                "watchdog is required for folder watching. "
                "Install it with: pip install watchdog"
            )
            raise ImportError(msg) from exc
        return Observer


class _IngestionHandler:
    """Watchdog event handler that dispatches file events to the pipeline.

    Debounces events with a per-path settle timer: each event for a path
    (re)starts a timer, and the file is ingested only once that path has been
    quiet for ``debounce_seconds``. This coalesces the burst of events a single
    save produces and avoids reading a file mid-write. When a timer fires, the
    ingestion coroutine is handed to the event loop via
    ``asyncio.run_coroutine_threadsafe`` and its result is checked so failures
    are logged rather than silently swallowed.
    """

    def __init__(
        self,
        pipeline: IngestionPipeline,
        loop: asyncio.AbstractEventLoop,
        debounce_seconds: float = _DEBOUNCE_SECONDS,
    ) -> None:
        self._pipeline = pipeline
        self._loop = loop
        self._debounce_seconds = debounce_seconds
        # Watchdog callbacks run on the observer thread, so the timer registry
        # is guarded by a lock.
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def dispatch(self, event: Any) -> None:
        """Handle a file system event by (re)scheduling a debounced ingest.

        Only processes file creation and modification events; directory events
        and deletions are ignored. The validator inside the pipeline already
        rejects unsupported file types, so this handler is permissive.

        Args:
            event: A watchdog event object.
        """
        # Import event types lazily alongside the handler
        from watchdog.events import FileCreatedEvent, FileModifiedEvent

        if not isinstance(event, (FileCreatedEvent, FileModifiedEvent)):
            return

        if event.is_directory:
            return

        self._schedule(str(event.src_path))

    def _schedule(self, path: str) -> None:
        """(Re)start the settle timer for a path, cancelling any pending one."""
        with self._lock:
            existing = self._timers.get(path)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(self._debounce_seconds, self._fire, args=[path])
            self._timers[path] = timer
            timer.start()

    def _fire(self, path: str) -> None:
        """Timer callback: hand the ingestion coroutine to the event loop."""
        with self._lock:
            self._timers.pop(path, None)

        file_path = Path(path)
        logger.info("Watcher ingesting (debounced): %s", file_path.name)
        future = asyncio.run_coroutine_threadsafe(
            self._pipeline.ingest(file_path), self._loop
        )
        future.add_done_callback(lambda f: self._log_result(f, file_path))

    @staticmethod
    def _log_result(future: Future[Any], file_path: Path) -> None:
        """Surface any exception raised by the scheduled ingestion coroutine."""
        try:
            future.result()
        except Exception:
            logger.exception("Watcher ingestion failed for %s", file_path.name)

    def cancel_all(self) -> None:
        """Cancel all pending settle timers (called on watcher shutdown)."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
