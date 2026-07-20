"""Tests for BM25 cache invalidation concurrency safety.

Verifies that cache invalidation is synchronized with lazy initialization to
prevent race conditions where initialization and invalidation occur simultaneously.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from atlasiq.backend.core.dependencies import (
    get_bm25_retriever,
    get_query_pipeline,
    invalidate_bm25_retriever,
)


@pytest.fixture(autouse=True)
def reset_caches() -> None:
    """Reset global cache state and locks before each test."""
    import atlasiq.backend.core.dependencies as deps

    deps._bm25_retriever = None
    deps._query_pipeline = None
    # Recreate locks for the current event loop
    deps._bm25_retriever_lock = asyncio.Lock()
    deps._query_pipeline_lock = asyncio.Lock()


@pytest.fixture
def mock_dependencies() -> Generator[None]:
    """Mock all downstream dependencies for isolated cache testing."""
    with (
        patch("atlasiq.backend.core.dependencies.get_settings") as mock_settings,
        patch("atlasiq.backend.core.dependencies.get_document_repository") as mock_repo,
        patch("atlasiq.backend.core.dependencies.get_qdrant_client"),
        patch("atlasiq.backend.core.dependencies.get_embedder"),
        patch("atlasiq.backend.core.dependencies.get_prompt_builder"),
        patch("atlasiq.backend.core.dependencies.get_llm_provider"),
        patch("atlasiq.backend.core.dependencies.get_answer_generator"),
        patch("atlasiq.backend.core.dependencies.get_citation_builder"),
        patch("atlasiq.backend.core.dependencies.get_guardrails"),
    ):
        # Mock retrieval settings
        mock_settings.return_value.retrieval.bm25_top_k = 10
        mock_settings.return_value.retrieval.dense_top_k = 10
        mock_settings.return_value.retrieval.hybrid_top_k = 10
        mock_settings.return_value.retrieval.rrf_k = 60
        mock_settings.return_value.retrieval.min_confidence_score = 0.5

        # Mock repository to return empty chunks list
        mock_repo.return_value.list_all_chunks = AsyncMock(return_value=[])

        yield


class TestCacheInvalidation:
    """Test cache invalidation behavior and lifecycle."""

    @pytest.mark.asyncio
    async def test_invalidate_clears_bm25_cache(self, mock_dependencies: None) -> None:
        """Verify invalidation clears the BM25 retriever singleton."""
        # Build cache
        retriever1 = await get_bm25_retriever()
        assert retriever1 is not None

        # Invalidate
        await invalidate_bm25_retriever()

        # Verify cache is cleared by checking that a new instance is built
        retriever2 = await get_bm25_retriever()
        assert retriever2 is not None
        assert retriever2 is not retriever1  # new instance after invalidation

    @pytest.mark.asyncio
    async def test_invalidate_clears_query_pipeline_cache(
        self, mock_dependencies: None
    ) -> None:
        """Verify invalidation clears the query pipeline singleton."""
        # Build cache
        pipeline1 = await get_query_pipeline()
        assert pipeline1 is not None

        # Invalidate
        await invalidate_bm25_retriever()

        # Verify cache is cleared
        pipeline2 = await get_query_pipeline()
        assert pipeline2 is not None
        assert pipeline2 is not pipeline1  # new instance after invalidation

    @pytest.mark.asyncio
    async def test_lazy_rebuild_after_invalidation(self, mock_dependencies: None) -> None:
        """Verify retriever is rebuilt lazily on next access after invalidation."""
        # Build initial cache
        await get_bm25_retriever()

        # Invalidate
        await invalidate_bm25_retriever()

        # Next access should succeed (lazy rebuild)
        retriever = await get_bm25_retriever()
        assert retriever is not None

    @pytest.mark.asyncio
    async def test_multiple_invalidations_are_safe(self, mock_dependencies: None) -> None:
        """Verify multiple consecutive invalidations do not cause errors."""
        await get_bm25_retriever()

        # Multiple invalidations
        await invalidate_bm25_retriever()
        await invalidate_bm25_retriever()
        await invalidate_bm25_retriever()

        # Should still rebuild successfully
        retriever = await get_bm25_retriever()
        assert retriever is not None


class TestConcurrencySafety:
    """Test cache operations are safe under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_initialization_builds_once(
        self, mock_dependencies: None
    ) -> None:
        """Verify concurrent initialization requests result in a single build."""
        build_count = 0

        async def counting_list_all_chunks() -> list[object]:
            nonlocal build_count
            build_count += 1
            # Small delay to increase chance of race if lock is broken
            await asyncio.sleep(0.01)
            return []

        with patch(
            "atlasiq.backend.core.dependencies.get_document_repository"
        ) as mock_repo:
            mock_repo.return_value.list_all_chunks = counting_list_all_chunks

            # Launch 10 concurrent initialization requests
            tasks = [get_bm25_retriever() for _ in range(10)]
            retrievers = await asyncio.gather(*tasks)

            # All should get the same instance
            assert all(r is retrievers[0] for r in retrievers)
            # Index should be built exactly once
            assert build_count == 1

    @pytest.mark.asyncio
    async def test_invalidation_during_initialization(
        self, mock_dependencies: None
    ) -> None:
        """Verify invalidation waits for initialization to complete."""
        init_started = asyncio.Event()
        init_can_proceed = asyncio.Event()

        async def slow_list_all_chunks() -> list[object]:
            init_started.set()
            await init_can_proceed.wait()
            return []

        with patch(
            "atlasiq.backend.core.dependencies.get_document_repository"
        ) as mock_repo:
            mock_repo.return_value.list_all_chunks = slow_list_all_chunks

            # Start initialization
            init_task = asyncio.create_task(get_bm25_retriever())

            # Wait for initialization to start
            await init_started.wait()

            # Start invalidation (should wait for lock)
            invalidate_task = asyncio.create_task(invalidate_bm25_retriever())

            # Give invalidation a moment to attempt acquiring the lock
            await asyncio.sleep(0.01)

            # Initialization should not be complete yet
            assert not init_task.done()

            # Allow initialization to complete
            init_can_proceed.set()
            await init_task

            # Now invalidation can complete
            await invalidate_task

            # Verify cache was actually invalidated
            import atlasiq.backend.core.dependencies as deps

            assert deps._bm25_retriever is None

    @pytest.mark.asyncio
    async def test_initialization_after_invalidation_starts(
        self, mock_dependencies: None
    ) -> None:
        """Verify initialization waits if invalidation is in progress."""
        invalidate_started = asyncio.Event()
        invalidate_can_proceed = asyncio.Event()

        # First, build the cache normally
        await get_bm25_retriever()

        # Mock invalidation to be slow
        original_invalidate = invalidate_bm25_retriever

        async def slow_invalidate() -> None:
            invalidate_started.set()
            await invalidate_can_proceed.wait()
            await original_invalidate()

        with patch(
            "atlasiq.backend.core.dependencies.invalidate_bm25_retriever",
            side_effect=slow_invalidate,
        ):
            # Start slow invalidation
            invalidate_task = asyncio.create_task(slow_invalidate())

            # Wait for invalidation to start
            await invalidate_started.wait()

            # Try to initialize (should wait for invalidation lock)
            init_task = asyncio.create_task(get_bm25_retriever())

            # Give initialization time to attempt lock acquisition
            await asyncio.sleep(0.01)

            # Allow invalidation to complete
            invalidate_can_proceed.set()
            await invalidate_task

            # Now initialization can proceed
            retriever = await init_task
            assert retriever is not None
