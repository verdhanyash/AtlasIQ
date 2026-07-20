"""Ingestion pipeline orchestrator.

Wires the ingestion collaborators — validator, change detector, parser, chunker,
embedder, and the PostgreSQL + Qdrant repositories — into a single linear flow.
This module contains **orchestration only**: it decides call order and handles
lifecycle status, but performs no validation, parsing, chunking, embedding, or
SQL of its own. Every collaborator is constructor-injected, so the pipeline is
trivially testable with mocks.

Change detection is database-backed: the file's content hash and a deterministic
document id (derived from the resolved path) decide whether a file is NEW,
MODIFIED, or UNCHANGED by consulting the document repository — no in-memory
registry, so the decision survives process restarts.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from atlasiq.backend.domain import (
    ChunkRecord,
    DocumentRecord,
    DocumentStatus,
    chunk_id,
)
from atlasiq.ingestion.change_detector import ChangeStatus
from atlasiq.ingestion.metadata import extract_metadata

if TYPE_CHECKING:
    from pathlib import Path

    from atlasiq.backend.repositories.document_repository import DocumentRepository
    from atlasiq.backend.repositories.vector_repository import ChunkVectorRepository
    from atlasiq.ingestion.change_detector import ChangeDetector
    from atlasiq.ingestion.chunker import DocumentChunker
    from atlasiq.ingestion.embedder import DocumentEmbedder
    from atlasiq.ingestion.metadata import DocumentMetadata
    from atlasiq.ingestion.parser import DocumentParser
    from atlasiq.ingestion.validator import DocumentValidator

logger = logging.getLogger(__name__)

# Fixed namespace for deterministic document-id generation. Pinned so that the
# same resolved file path always maps to the same id across processes/machines,
# which keeps a document's id stable across re-ingestions (DL-018 assumption) and
# lets the MODIFIED re-index path realign chunks by index. Never change this.
_DOCUMENT_ID_NAMESPACE = uuid.UUID("2c8f0a54-6b3d-4e7a-9c1f-8a2d5e0b7c33")


@dataclass(slots=True)
class IngestionResult:
    """Outcome of a single ``ingest`` call.

    Attributes:
        document_id: The stable id of the ingested document.
        status: Whether the document was NEW, MODIFIED, or UNCHANGED.
        chunks_created: Number of chunks written (0 when skipped).
        skipped: True when the document was UNCHANGED and no work was done.
    """

    document_id: str
    status: ChangeStatus
    chunks_created: int
    skipped: bool


class IngestionPipeline:
    """Orchestrates the end-to-end ingestion of a single document.

    Collaborators are injected; the pipeline constructs none of them. It calls
    them in a fixed order and manages the document's lifecycle status, delegating
    all real work (validation, parsing, chunking, embedding, persistence) to the
    injected components.
    """

    def __init__(
        self,
        validator: DocumentValidator,
        change_detector: ChangeDetector,
        parser: DocumentParser,
        chunker: DocumentChunker,
        embedder: DocumentEmbedder,
        document_repo: DocumentRepository,
        vector_repo: ChunkVectorRepository,
    ) -> None:
        """Initialise the pipeline with its collaborators.

        Args:
            validator: Rejects unsupported/oversized/missing files.
            change_detector: Provides content hashing (owns the hash algorithm).
            parser: Converts a file into Markdown text.
            chunker: Splits text into overlapping chunks.
            embedder: Produces embedding vectors for chunk texts.
            document_repo: PostgreSQL persistence for documents and chunk text.
            vector_repo: Qdrant persistence for chunk vectors.
        """
        self._validator = validator
        self._change_detector = change_detector
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._document_repo = document_repo
        self._vector_repo = vector_repo

    async def ingest(self, file_path: Path) -> IngestionResult:
        """Ingest a single document file.

        Validates the file, decides whether it is new/modified/unchanged, and —
        unless unchanged — parses, chunks, embeds, and persists it to both
        stores, transitioning the document status PROCESSING → COMPLETED. On any
        failure after persistence begins, the status is set to FAILED and the
        error is re-raised.

        Args:
            file_path: Path to the document file to ingest.

        Returns:
            An :class:`IngestionResult` describing what happened.

        Raises:
            DocumentValidationError: If the file fails validation.
            AtlasIQError: If any later stage fails (status set to FAILED first).
        """
        self._validator.validate(file_path)

        metadata = extract_metadata(file_path)
        file_hash = self._change_detector.compute_hash(file_path)
        document_id = self._document_id(file_path)

        existing = await self._document_repo.get_document_by_id(document_id)
        status = self._decide_status(existing, file_hash)

        if status is ChangeStatus.UNCHANGED:
            logger.info("Skipping unchanged document %s (%s)", document_id, metadata.file_name)
            return IngestionResult(document_id, status, chunks_created=0, skipped=True)

        if status is ChangeStatus.MODIFIED:
            # Safe re-indexing (DL-018): delete the document's existing chunks
            # from BOTH stores before re-inserting. Delete-then-insert ordering
            # is mandatory — it is what prevents orphaned tail chunks when the
            # new version produces fewer chunks than the previous one. The
            # document row itself is kept (id + created_at stable); only its
            # chunks are replaced.
            logger.info("Re-indexing modified document %s (%s)", document_id, metadata.file_name)
            await self._document_repo.delete_chunks_for_document(document_id)
            self._vector_repo.delete_for_document(document_id)

        chunks_created = await self._process(document_id, file_path, metadata, file_hash, existing)

        logger.info(
            "Ingested %s as %s (%d chunks)", metadata.file_name, status.value, chunks_created
        )

        from atlasiq.backend.core.dependencies import invalidate_bm25_retriever

        await invalidate_bm25_retriever()

        return IngestionResult(document_id, status, chunks_created, skipped=False)

    async def _process(
        self,
        document_id: str,
        file_path: Path,
        metadata: DocumentMetadata,
        file_hash: str,
        existing: DocumentRecord | None,
    ) -> int:
        """Parse, chunk, embed, and persist a document; manage its status.

        Shared by the NEW and MODIFIED paths. The document row is upserted as
        PROCESSING first (so a mid-pipeline failure still leaves a tracked
        record); on success it is upserted again as COMPLETED carrying the final
        ``word_count``; on any failure the status is set to FAILED and the error
        is re-raised. For a MODIFIED document the caller has already removed the
        stale chunks before this runs.

        Args:
            document_id: The document's stable id.
            file_path: Path to the source file.
            metadata: Extracted file-system metadata (name/extension/size).
            file_hash: SHA-256 content hash of the file.
            existing: The previously stored record, if any. Its ``created_at`` is
                preserved so re-ingestion does not reset the creation time.

        Returns:
            The number of chunks created.
        """
        now = datetime.now(UTC)
        document = DocumentRecord(
            id=document_id,
            filename=metadata.file_name,
            file_hash=file_hash,
            file_type=metadata.file_extension,
            file_size_bytes=metadata.file_size_bytes,
            status=DocumentStatus.PROCESSING,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            ingested_at=now,
        )
        await self._document_repo.upsert_document(document)

        try:
            text = self._parser.parse(file_path)
            chunk_texts = self._chunker.chunk(text)
            records = [
                ChunkRecord(
                    id=chunk_id(document_id, index),
                    document_id=document_id,
                    chunk_index=index,
                    content=content,
                )
                for index, content in enumerate(chunk_texts)
            ]
            vectors = self._embedder.embed(chunk_texts)

            await self._document_repo.insert_chunks(records)
            self._vector_repo.store(records, vectors)

            # Finalise: record the word count and mark COMPLETED in one upsert
            # (word_count is only known post-parse, after the PROCESSING upsert).
            document.status = DocumentStatus.COMPLETED
            document.word_count = len(text.split())
            document.updated_at = datetime.now(UTC)
            await self._document_repo.upsert_document(document)
        except Exception:
            await self._document_repo.update_status(document_id, DocumentStatus.FAILED)
            logger.exception("Ingestion failed for %s; status set to FAILED", document_id)
            raise

        return len(records)

    @staticmethod
    def _decide_status(existing: DocumentRecord | None, file_hash: str) -> ChangeStatus:
        """Classify a file as NEW, MODIFIED, or UNCHANGED.

        A document is UNCHANGED only if a completed record with the identical
        content hash already exists; an incomplete or failed prior attempt with
        the same content is treated as MODIFIED so it is re-processed.

        Args:
            existing: The stored record for this document id, if any.
            file_hash: The current file's content hash.

        Returns:
            The change status.
        """
        if existing is None:
            return ChangeStatus.NEW
        if existing.file_hash == file_hash and existing.status is DocumentStatus.COMPLETED:
            return ChangeStatus.UNCHANGED
        return ChangeStatus.MODIFIED

    @staticmethod
    def _document_id(file_path: Path) -> str:
        """Generate a deterministic document id from the resolved file path.

        The same path always yields the same id, keeping a document's id stable
        across re-ingestions (so MODIFIED re-indexing realigns chunks by index).

        Args:
            file_path: Path to the document file.

        Returns:
            A deterministic UUID string.
        """
        return str(uuid.uuid5(_DOCUMENT_ID_NAMESPACE, str(file_path.resolve())))
