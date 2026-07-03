"""Tests for the ingestion API (upload, status, document listing).

Uses FastAPI TestClient with the pipeline and repository mocked — no real
database, no Qdrant, no filesystem persistence beyond tmp_path (DL-014).
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pathlib import Path

from atlasiq.backend.domain import DocumentRecord, DocumentStatus
from atlasiq.backend.main import create_app
from atlasiq.ingestion.change_detector import ChangeStatus
from atlasiq.ingestion.pipeline import IngestionResult

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_pipeline() -> MagicMock:
    pipeline = MagicMock()
    pipeline.ingest = AsyncMock(
        return_value=IngestionResult(
            document_id="doc-123",
            status=ChangeStatus.NEW,
            chunks_created=5,
            skipped=False,
        )
    )
    return pipeline


@pytest.fixture
def mock_document_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_document_by_id = AsyncMock(return_value=None)
    repo.list_documents = AsyncMock(return_value=[])
    repo.count_chunks_for_document = AsyncMock(return_value=0)
    return repo


def _fake_settings(storage_dir: Path, max_mb: int = 50) -> MagicMock:
    settings = MagicMock()
    settings.ingestion.storage_dir = str(storage_dir)
    settings.ingestion.max_file_size_mb = max_mb
    return settings


@pytest.fixture
def client(
    mock_pipeline: MagicMock, mock_document_repo: MagicMock, tmp_path: Path
) -> TestClient:
    from atlasiq.backend.core.dependencies import (
        get_document_repository,
        get_ingestion_pipeline,
        get_settings,
    )

    app = create_app()
    app.dependency_overrides[get_ingestion_pipeline] = lambda: mock_pipeline
    app.dependency_overrides[get_document_repository] = lambda: mock_document_repo
    app.dependency_overrides[get_settings] = lambda: _fake_settings(tmp_path)
    return TestClient(app)


def _get_pipeline_dep() -> Any:
    from atlasiq.backend.core.dependencies import get_ingestion_pipeline

    return get_ingestion_pipeline


def _get_repo_dep() -> Any:
    from atlasiq.backend.core.dependencies import get_document_repository

    return get_document_repository


# ── Upload (Step 8A) ─────────────────────────────────────────────────────────


class TestUpload:
    """Tests for POST /ingest/upload."""

    def test_happy_path(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        resp = client.post(
            "/ingest/upload",
            files={"file": ("report.txt", BytesIO(b"hello"), "text/plain")},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["document_id"] == "doc-123"
        assert body["status"] == "new"
        assert body["chunks_created"] == 5
        assert body["skipped"] is False
        mock_pipeline.ingest.assert_awaited_once()

    def test_path_traversal_rejected(self, client: TestClient) -> None:
        # A filename consisting solely of ".." is unsafe (Path("..").name == "..")
        resp = client.post(
            "/ingest/upload",
            files={"file": ("..", BytesIO(b"x"), "text/plain")},
        )

        assert resp.status_code == 422
        assert "Unsafe filename" in resp.json()["message"]

    def test_empty_filename_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/ingest/upload",
            files={"file": ("", BytesIO(b"x"), "text/plain")},
        )

        assert resp.status_code == 422

    def test_validation_error_returns_422_and_cleans_up(
        self, client: TestClient, mock_pipeline: MagicMock, tmp_path: Path
    ) -> None:
        from atlasiq.backend.core.exceptions import DocumentValidationError

        mock_pipeline.ingest.side_effect = DocumentValidationError("bad file type")

        resp = client.post(
            "/ingest/upload",
            files={"file": ("report.exe", BytesIO(b"x"), "application/octet-stream")},
        )

        assert resp.status_code == 422
        assert "bad file type" in resp.json()["message"]
        # orphaned upload must be removed when ingestion fails
        assert not (tmp_path / "report.exe").exists()

    def test_oversized_file_rejected(
        self, mock_pipeline: MagicMock, mock_document_repo: MagicMock, tmp_path: Path
    ) -> None:
        from atlasiq.backend.core.dependencies import (
            get_document_repository,
            get_ingestion_pipeline,
            get_settings,
        )

        app = create_app()
        app.dependency_overrides[get_ingestion_pipeline] = lambda: mock_pipeline
        app.dependency_overrides[get_document_repository] = lambda: mock_document_repo
        app.dependency_overrides[get_settings] = lambda: _fake_settings(tmp_path, max_mb=0)
        local_client = TestClient(app)

        resp = local_client.post(
            "/ingest/upload",
            files={"file": ("big.txt", BytesIO(b"x" * 4096), "text/plain")},
        )

        assert resp.status_code == 422
        assert "too large" in resp.json()["message"].lower()
        # partial file must not be left behind
        assert not (tmp_path / "big.txt").exists()
        mock_pipeline.ingest.assert_not_called()


# ── Status (Step 8B) ─────────────────────────────────────────────────────────


class TestStatus:
    """Tests for GET /ingest/status/{document_id}."""

    def test_found(self, client: TestClient, mock_document_repo: MagicMock) -> None:
        now = datetime.now(UTC)
        mock_document_repo.get_document_by_id = AsyncMock(
            return_value=DocumentRecord(
                id="doc-123",
                filename="report.pdf",
                file_hash="abc",
                file_type=".pdf",
                file_size_bytes=2048,
                status=DocumentStatus.COMPLETED,
                word_count=500,
                created_at=now,
                updated_at=now,
            )
        )
        mock_document_repo.count_chunks_for_document = AsyncMock(return_value=7)

        resp = client.get("/ingest/status/doc-123")

        assert resp.status_code == 200
        body = resp.json()
        assert body["document_id"] == "doc-123"
        assert body["status"] == "completed"
        assert body["word_count"] == 500
        assert body["chunk_count"] == 7

    def test_not_found(self, client: TestClient, mock_document_repo: MagicMock) -> None:
        mock_document_repo.get_document_by_id = AsyncMock(return_value=None)

        resp = client.get("/ingest/status/missing-id")

        assert resp.status_code == 404
        assert "not found" in resp.json()["message"].lower()


# ── Document listing (Step 8B) ───────────────────────────────────────────────


class TestListDocuments:
    """Tests for GET /ingest/documents."""

    def test_returns_paginated_list(
        self, client: TestClient, mock_document_repo: MagicMock
    ) -> None:
        now = datetime.now(UTC)
        mock_document_repo.list_documents = AsyncMock(
            return_value=[
                DocumentRecord(
                    id="doc-1",
                    filename="a.txt",
                    file_hash="h1",
                    file_type=".txt",
                    file_size_bytes=10,
                    status=DocumentStatus.COMPLETED,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )

        resp = client.get("/ingest/documents?limit=10&offset=5")

        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 10
        assert body["offset"] == 5
        assert body["count"] == 1
        assert body["documents"][0]["document_id"] == "doc-1"

    def test_default_pagination(
        self, client: TestClient, mock_document_repo: MagicMock
    ) -> None:
        mock_document_repo.list_documents = AsyncMock(return_value=[])

        resp = client.get("/ingest/documents")

        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 50
        assert body["offset"] == 0
