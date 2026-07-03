"""Tests for the optional folder watcher.

Simulates watchdog events by calling the handler directly — no real filesystem
watching in tests (DL-014). Verifies event dispatch, non-file event filtering,
and lazy watchdog import.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from atlasiq.ingestion.watcher import FolderWatcher, _IngestionHandler

# ── Fixtures ─────────────────────────────────────────────────────────────────


def _mock_pipeline() -> MagicMock:
    pipeline = MagicMock()
    pipeline.ingest = AsyncMock()
    return pipeline


def _make_handler(debounce: float = 999.0) -> tuple[_IngestionHandler, MagicMock]:
    """Build a handler with a long debounce so timers never fire mid-test."""
    pipeline = _mock_pipeline()
    loop = asyncio.new_event_loop()
    handler = _IngestionHandler(pipeline, loop, debounce_seconds=debounce)
    return handler, pipeline


# ── _IngestionHandler: event filtering + scheduling ──────────────────────────


class TestIngestionHandlerScheduling:
    """Tests for _IngestionHandler.dispatch and debounce scheduling."""

    def test_file_created_schedules_timer(self) -> None:
        from watchdog.events import FileCreatedEvent

        handler, _ = _make_handler()
        handler.dispatch(FileCreatedEvent(src_path="/tmp/doc.txt"))

        assert "/tmp/doc.txt" in handler._timers
        handler.cancel_all()

    def test_file_modified_schedules_timer(self) -> None:
        from watchdog.events import FileModifiedEvent

        handler, _ = _make_handler()
        handler.dispatch(FileModifiedEvent(src_path="/tmp/doc.txt"))

        assert "/tmp/doc.txt" in handler._timers
        handler.cancel_all()

    def test_ignores_directory_events(self) -> None:
        from watchdog.events import DirCreatedEvent

        handler, _ = _make_handler()
        handler.dispatch(DirCreatedEvent(src_path="/tmp/subdir"))

        assert handler._timers == {}

    def test_ignores_delete_events(self) -> None:
        from watchdog.events import FileDeletedEvent

        handler, _ = _make_handler()
        handler.dispatch(FileDeletedEvent(src_path="/tmp/doc.txt"))

        assert handler._timers == {}

    def test_debounce_coalesces_rapid_events(self) -> None:
        from watchdog.events import FileModifiedEvent

        handler, _ = _make_handler()
        handler.dispatch(FileModifiedEvent(src_path="/tmp/doc.txt"))
        first = handler._timers["/tmp/doc.txt"]
        handler.dispatch(FileModifiedEvent(src_path="/tmp/doc.txt"))
        second = handler._timers["/tmp/doc.txt"]

        # the second event must replace and cancel the first timer
        assert first is not second
        assert first.finished.is_set()  # cancelled
        handler.cancel_all()


# ── _IngestionHandler: firing + failure logging ──────────────────────────────


class TestIngestionHandlerFiring:
    """Tests for _fire (loop hand-off) and _log_result (failure surfacing)."""

    def test_fire_schedules_coroutine_and_registers_callback(self) -> None:
        handler, _ = _make_handler()

        fake_future = MagicMock()
        with patch.object(
            asyncio, "run_coroutine_threadsafe", return_value=fake_future
        ) as mock_sched:
            handler._fire("/tmp/doc.txt")

        mock_sched.assert_called_once()
        coro = mock_sched.call_args.args[0]
        coro.close()  # avoid "coroutine was never awaited" warning
        fake_future.add_done_callback.assert_called_once()

    def test_log_result_surfaces_exception(self) -> None:
        handler, _ = _make_handler()
        future: Future[None] = Future()
        future.set_exception(ValueError("boom"))

        # Must not raise — the failure is caught and logged
        handler._log_result(future, Path("/tmp/doc.txt"))


# ── FolderWatcher ────────────────────────────────────────────────────────────


class TestFolderWatcher:
    """Tests for FolderWatcher lifecycle."""

    def test_lazy_import_of_observer(self) -> None:
        # Should not raise — watchdog is installed in the dev deps
        cls = FolderWatcher._get_observer_class()
        # The class name varies by platform (Observer, WindowsApiObserver, etc.)
        assert "Observer" in cls.__name__

    def test_start_creates_watch_directory(self, tmp_path: Path) -> None:
        watch_dir = tmp_path / "watch_me"
        pipeline = _mock_pipeline()
        watcher = FolderWatcher(watch_dir, pipeline)

        loop = asyncio.new_event_loop()
        watcher.start(loop)

        assert watch_dir.exists()
        watcher.stop()
        loop.close()

    def test_stop_is_idempotent(self, tmp_path: Path) -> None:
        pipeline = _mock_pipeline()
        watcher = FolderWatcher(tmp_path, pipeline)

        # stop without start should not raise
        watcher.stop()
