"""Tests for the query API (POST /query).

Uses FastAPI TestClient with the QueryPipeline mocked — no real LLM providers,
no database, and no network/qdrant calls.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from atlasiq.backend.core.exceptions import (
    DatabaseQueryError,
    LLMProviderError,
    PromptTemplateError,
    RetrievalError,
)
from atlasiq.backend.main import create_app
from atlasiq.retrieval.citations import Citation
from atlasiq.retrieval.qa_pipeline import QueryResponse


@pytest.fixture
def mock_query_pipeline() -> MagicMock:
    """Provide a mock QueryPipeline."""
    pipeline = MagicMock()
    # Default success response
    pipeline.answer = AsyncMock(
        return_value=QueryResponse(
            answer="This is a generated answer.",
            citations=[
                Citation(
                    document_name="test_doc.pdf",
                    page="3",
                    quote="This is the matching passage.",
                )
            ],
            confidence_score=0.85,
            refusal_reason=None,
        )
    )
    return pipeline


@pytest.fixture
def client(mock_query_pipeline: MagicMock) -> TestClient:
    """Provide a TestClient with overridden get_query_pipeline dependency."""
    from atlasiq.backend.core.dependencies import get_query_pipeline

    app = create_app()
    app.dependency_overrides[get_query_pipeline] = lambda: mock_query_pipeline
    return TestClient(app)


class TestQueryEndpoint:
    """Tests for POST /query endpoint."""

    def test_happy_path(self, client: TestClient, mock_query_pipeline: MagicMock) -> None:
        """A successful query returns answer, citations, confidence, and sources."""
        resp = client.post("/query", json={"question": "What is AtlasIQ?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "This is a generated answer."
        assert len(body["citations"]) == 1
        assert body["citations"][0]["document_name"] == "test_doc.pdf"
        assert body["citations"][0]["page"] == "3"
        assert body["citations"][0]["quote"] == "This is the matching passage."
        assert body["confidence"] == 0.85
        assert body["sources"] == ["test_doc.pdf"]
        assert body["refusal_reason"] is None

        mock_query_pipeline.answer.assert_awaited_once_with("What is AtlasIQ?")

    @pytest.mark.parametrize(
        "invalid_question",
        [
            "",
            "   ",
            "\n\t",
        ],
    )
    def test_invalid_questions_rejected(self, client: TestClient, invalid_question: str) -> None:
        """Empty or whitespace-only questions return 422 validation error."""
        resp = client.post("/query", json={"question": invalid_question})
        assert resp.status_code == 422
        # Verify it mentions question validation
        assert "question" in resp.text

    def test_missing_question_field_rejected(self, client: TestClient) -> None:
        """Missing the question field in payload returns 422 validation error."""
        resp = client.post("/query", json={})
        assert resp.status_code == 422

    def test_guardrail_refusal_is_200(self, client: TestClient, mock_query_pipeline: MagicMock) -> None:
        """A guardrail refusal returns HTTP 200 with low confidence and empty citations."""
        mock_query_pipeline.answer.return_value = QueryResponse(
            answer="I don't have enough information to answer this question based on the available documents.",
            citations=[],
            confidence_score=0.0,
            refusal_reason="no_retrieval_results",
        )

        resp = client.post("/query", json={"question": "Out of corpus question?"})

        assert resp.status_code == 200
        body = resp.json()
        assert "I don't have enough information" in body["answer"]
        assert body["citations"] == []
        assert body["confidence"] == 0.0
        assert body["sources"] == []
        assert body["refusal_reason"] == "no_retrieval_results"

    def test_retrieval_error_mapped_to_503(self, client: TestClient, mock_query_pipeline: MagicMock) -> None:
        """RetrievalError is mapped to HTTP 503 Service Unavailable."""
        mock_query_pipeline.answer.side_effect = RetrievalError("Qdrant connection failed")

        resp = client.post("/query", json={"question": "Any question?"})

        assert resp.status_code == 503
        body = resp.json()
        assert body["error"] == "RetrievalError"
        assert "Qdrant connection failed" in body["message"]

    def test_llm_provider_error_mapped_to_502(self, client: TestClient, mock_query_pipeline: MagicMock) -> None:
        """LLMProviderError is mapped to HTTP 502 Bad Gateway."""
        mock_query_pipeline.answer.side_effect = LLMProviderError("Ollama host unreachable")

        resp = client.post("/query", json={"question": "Any question?"})

        assert resp.status_code == 502
        body = resp.json()
        assert body["error"] == "LLMProviderError"
        assert "Ollama host unreachable" in body["message"]

    def test_prompt_template_error_mapped_to_500(self, client: TestClient, mock_query_pipeline: MagicMock) -> None:
        """PromptTemplateError is mapped to HTTP 500 Internal Server Error."""
        mock_query_pipeline.answer.side_effect = PromptTemplateError("qa_template.txt not found")

        resp = client.post("/query", json={"question": "Any question?"})

        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] == "PromptTemplateError"
        assert "qa_template.txt not found" in body["message"]

    def test_generic_database_error_mapped_to_400(self, client: TestClient, mock_query_pipeline: MagicMock) -> None:
        """DatabaseQueryError is mapped to HTTP 400 Bad Request via the base AtlasIQError handler."""
        mock_query_pipeline.answer.side_effect = DatabaseQueryError("Postgres syntax error")

        resp = client.post("/query", json={"question": "Any question?"})

        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "DatabaseQueryError"
        assert "Postgres syntax error" in body["message"]


class TestBM25CacheInvalidation:
    """Tests for the BM25 retriever cache invalidation lifecycle."""

    @pytest.mark.asyncio
    async def test_cache_lifecycle(self) -> None:
        """Cache invalidation clears the singleton, next query rebuilds, and subsequent reuse cache."""
        from unittest.mock import AsyncMock, patch

        from atlasiq.backend.core import dependencies
        from atlasiq.backend.core.dependencies import (
            get_bm25_retriever,
            invalidate_bm25_retriever,
        )

        # Reset any active singletons to start clean
        dependencies._bm25_retriever = None
        dependencies._query_pipeline = None

        mock_repo = MagicMock()
        mock_repo.list_all_chunks = AsyncMock(return_value=[])

        # Patch get_document_repository and get_settings to return mock repo and settings
        with patch("atlasiq.backend.core.dependencies.get_document_repository", return_value=mock_repo), \
             patch("atlasiq.backend.core.dependencies.get_settings") as mock_get_settings:

            mock_settings = MagicMock()
            mock_settings.retrieval.bm25_top_k = 5
            mock_get_settings.return_value = mock_settings

            # 1. First retrieval should trigger build (list_all_chunks called once)
            retriever1 = await get_bm25_retriever()
            assert retriever1 is not None
            mock_repo.list_all_chunks.assert_called_once()

            # 2. Repeated retrieval should reuse the cached instance (list_all_chunks count remains 1)
            retriever2 = await get_bm25_retriever()
            assert retriever2 is retriever1
            assert mock_repo.list_all_chunks.call_count == 1

            # 3. Invalidation should clear the cached instances
            await invalidate_bm25_retriever()
            assert dependencies._bm25_retriever is None
            assert dependencies._query_pipeline is None

            # 4. Next retrieval should rebuild the index (list_all_chunks called again)
            retriever3 = await get_bm25_retriever()
            assert retriever3 is not None
            assert retriever3 is not retriever1
            assert mock_repo.list_all_chunks.call_count == 2

            # 5. Repeated queries after rebuild should reuse the new cache
            retriever4 = await get_bm25_retriever()
            assert retriever4 is retriever3
            assert mock_repo.list_all_chunks.call_count == 2

    @pytest.mark.asyncio
    async def test_ingestion_triggers_invalidation(self, tmp_path: Path) -> None:
        """A successful ingestion triggers cache invalidation."""
        from unittest.mock import AsyncMock, patch

        from atlasiq.backend.core import dependencies
        from atlasiq.ingestion.pipeline import IngestionPipeline

        # Create a dummy file that actually exists
        dummy_file = tmp_path / "dummy.pdf"
        dummy_file.write_bytes(b"dummy pdf content")

        # Set a dummy cached retriever
        dummy_retriever = MagicMock()
        dependencies._bm25_retriever = dummy_retriever
        dependencies._query_pipeline = MagicMock()

        # Mock all ingestion pipeline collaborators
        mock_validator = MagicMock()
        mock_change_detector = MagicMock()
        mock_change_detector.compute_hash.return_value = "hash123"
        mock_parser = MagicMock()
        mock_chunker = MagicMock()
        mock_embedder = MagicMock()
        mock_document_repo = MagicMock()
        mock_document_repo.get_document_by_id = AsyncMock(return_value=None)
        mock_vector_repo = MagicMock()

        pipeline = IngestionPipeline(
            validator=mock_validator,
            change_detector=mock_change_detector,
            parser=mock_parser,
            chunker=mock_chunker,
            embedder=mock_embedder,
            document_repo=mock_document_repo,
            vector_repo=mock_vector_repo,
        )

        # Mock internal process to succeed and return chunks created
        with patch.object(pipeline, "_process", AsyncMock(return_value=(3, {"test": "metadata"}))):
            result = await pipeline.ingest(dummy_file)

            # Verify ingestion successfully occurred (not skipped)
            assert result.skipped is False

            # Verify cache was invalidated
            assert dependencies._bm25_retriever is None
            assert dependencies._query_pipeline is None

