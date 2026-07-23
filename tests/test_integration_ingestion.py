"""End-to-end integration test for the ingestion pipeline.

Exercises the full chain — real Validator, Parser, Chunker, and ChunkRecord
building — with only the heavy/IO dependencies (Embedder, repositories) mocked.
This proves the pipeline produces the correct number of chunks and calls stores
correctly without Docker, network, or model downloads (DL-014).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from atlasiq.backend.core.config import ChunkingConfig, IngestionConfig
from atlasiq.backend.domain import chunk_id
from atlasiq.ingestion.change_detector import ChangeDetector, ChangeStatus
from atlasiq.ingestion.chunker import DocumentChunker
from atlasiq.ingestion.embedder import DocumentEmbedder
from atlasiq.ingestion.parser import DocumentParser
from atlasiq.ingestion.pipeline import IngestionPipeline
from atlasiq.ingestion.validator import DocumentValidator

if TYPE_CHECKING:
    from pathlib import Path


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _fake_embedder() -> MagicMock:
    """Mock embedder returning deterministic fake vectors."""
    embedder = MagicMock(spec=DocumentEmbedder)
    embedder.embed = MagicMock(
        side_effect=lambda texts: [[0.1] * 4 for _ in texts]
    )
    embedder.model_name = "test-embedding-model"
    return embedder


def _fake_document_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_document_by_id = AsyncMock(return_value=None)
    repo.upsert_document = AsyncMock()
    repo.insert_chunks = AsyncMock()
    repo.update_status = AsyncMock()
    repo.delete_chunks_for_document = AsyncMock()
    return repo


def _fake_vector_repo() -> MagicMock:
    repo = MagicMock()
    repo.store = MagicMock()
    repo.delete_for_document = MagicMock()
    return repo


def _build_real_pipeline(
    document_repo: MagicMock, vector_repo: MagicMock, embedder: MagicMock
) -> IngestionPipeline:
    """Build a pipeline with real validator/parser/chunker and mocked IO deps."""
    ingestion_config = IngestionConfig(
        supported_formats=[".txt", ".md"],
        max_file_size_mb=10,
    )
    chunking_config = ChunkingConfig(
        chunk_size=100,
        chunk_overlap=20,
        separators=["\n\n", "\n", ". ", " "],
    )
    return IngestionPipeline(
        validator=DocumentValidator(ingestion_config),
        change_detector=ChangeDetector(),
        parser=DocumentParser(),
        chunker=DocumentChunker(chunking_config),
        embedder=embedder,
        document_repo=document_repo,
        vector_repo=vector_repo,
    )


# ── Integration tests ────────────────────────────────────────────────────────


class TestEndToEndIngestion:
    """Integration: real validator+parser+chunker, mocked embedder+repos."""

    @pytest.mark.asyncio
    async def test_ingests_txt_file_end_to_end(self, tmp_path: Path) -> None:
        # Create a real text file with enough content to produce multiple chunks
        content = "This is paragraph one with some content.\n\n" * 10
        file = tmp_path / "test_doc.txt"
        file.write_text(content, encoding="utf-8")

        doc_repo = _fake_document_repo()
        vec_repo = _fake_vector_repo()
        embedder = _fake_embedder()
        pipeline = _build_real_pipeline(doc_repo, vec_repo, embedder)

        result = await pipeline.ingest(file)

        assert result.status is ChangeStatus.NEW
        assert result.skipped is False
        assert result.chunks_created > 0

        # Embedder was called with the chunk texts
        embedder.embed.assert_called_once()
        embed_input = embedder.embed.call_args.args[0]
        assert len(embed_input) == result.chunks_created

        # Both stores were called
        doc_repo.insert_chunks.assert_awaited_once()
        vec_repo.store.assert_called_once()

        # Chunk ids are deterministic
        inserted_chunks = doc_repo.insert_chunks.await_args.args[0]
        for i, chunk in enumerate(inserted_chunks):
            assert chunk.id == chunk_id(result.document_id, i)
            assert chunk.document_id == result.document_id
            assert chunk.chunk_index == i
            assert len(chunk.content) > 0

    @pytest.mark.asyncio
    async def test_ingests_md_file_end_to_end(self, tmp_path: Path) -> None:
        content = "# Title\n\nSome paragraph.\n\n## Section\n\nMore text here.\n"
        file = tmp_path / "notes.md"
        file.write_text(content, encoding="utf-8")

        doc_repo = _fake_document_repo()
        vec_repo = _fake_vector_repo()
        embedder = _fake_embedder()
        pipeline = _build_real_pipeline(doc_repo, vec_repo, embedder)

        result = await pipeline.ingest(file)

        assert result.status is ChangeStatus.NEW
        assert result.chunks_created >= 1
        doc_repo.insert_chunks.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unchanged_on_second_ingest(self, tmp_path: Path) -> None:
        file = tmp_path / "stable.txt"
        file.write_text("stable content", encoding="utf-8")

        doc_repo = _fake_document_repo()
        vec_repo = _fake_vector_repo()
        embedder = _fake_embedder()
        pipeline = _build_real_pipeline(doc_repo, vec_repo, embedder)

        # First ingest — NEW
        result1 = await pipeline.ingest(file)
        assert result1.status is ChangeStatus.NEW

        # Second ingest — the doc_repo now "has" the document (simulate via mock)
        from atlasiq.backend.domain import DocumentRecord, DocumentStatus

        doc_repo.get_document_by_id = AsyncMock(
            return_value=DocumentRecord(
                id=result1.document_id,
                filename="stable.txt",
                file_hash=ChangeDetector().compute_hash(file),
                file_type=".txt",
                file_size_bytes=file.stat().st_size,
                status=DocumentStatus.COMPLETED,
            )
        )

        result2 = await pipeline.ingest(file)

        assert result2.status is ChangeStatus.UNCHANGED
        assert result2.skipped is True
        assert result2.chunks_created == 0
