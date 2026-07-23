"""Ingestion API routes for AtlasIQ.

Provides the primary document upload endpoint (``POST /upload``) and the
status/listing endpoints (``GET /status/{document_id}``, ``GET /documents``).
Routes delegate orchestration to the injected :class:`IngestionPipeline`
and read state from :class:`DocumentRepository` — they contain no business
logic of their own.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, UploadFile

from atlasiq.backend.core.config import Settings
from atlasiq.backend.core.dependencies import (
    get_document_repository,
    get_ingestion_pipeline,
    get_qdrant_client,
    get_settings,
)
from atlasiq.backend.core.exceptions import (
    AtlasIQError,
    DocumentNotFoundError,
    DocumentValidationError,
)
from atlasiq.backend.repositories.document_repository import DocumentRepository
from atlasiq.backend.repositories.vector_repository import ChunkVectorRepository
from atlasiq.ingestion.pipeline import IngestionPipeline, IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])

# Read uploads in 1 MB chunks so a large file is never fully buffered in memory.
_UPLOAD_CHUNK_SIZE = 1024 * 1024

# Bounds for the document-listing pagination parameters.
_MAX_LIST_LIMIT = 200


# ── Upload endpoint ──────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Upload and ingest a document.

    Saves the uploaded file under the configured storage directory, runs the
    full ingestion pipeline (validate → parse → chunk → embed → persist), and
    returns the ingestion result.

    Args:
        file: The uploaded file.
        pipeline: The injected ingestion pipeline.
        settings: Application settings (for storage directory).

    Returns:
        JSON with ``document_id``, ``status``, ``chunks_created``, ``skipped``.
    """
    storage_dir = Path(settings.ingestion.storage_dir)
    max_bytes = settings.ingestion.max_file_size_mb * 1024 * 1024
    saved_path = await _save_upload(file, storage_dir, max_bytes)

    # If ingestion fails, remove the file we just saved so failed uploads don't
    # accumulate as orphaned files on disk.
    try:
        result: IngestionResult = await pipeline.ingest(saved_path)
    except AtlasIQError:
        saved_path.unlink(missing_ok=True)
        raise

    return {
        "document_id": result.document_id,
        "status": result.status.value,
        "chunks_created": result.chunks_created,
        "skipped": result.skipped,
        "metadata": result.metadata or {},
    }


# ── Status endpoints ─────────────────────────────────────────────────────────


@router.get("/status/{document_id}")
async def get_document_status(
    document_id: str,
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> dict[str, Any]:
    """Get the ingestion status of a document.

    Args:
        document_id: The document's unique identifier.
        document_repo: The injected document repository.

    Returns:
        JSON with document metadata and status.

    Raises:
        DocumentNotFoundError: If no document with the given id exists.
    """
    document = await document_repo.get_document_by_id(document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    chunk_count = await document_repo.count_chunks_for_document(document_id)

    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status.value,
        "file_type": document.file_type,
        "file_size_bytes": document.file_size_bytes,
        "word_count": document.word_count,
        "chunk_count": chunk_count,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }


@router.get("/documents")
async def list_documents(
    limit: int = Query(default=50, ge=1, le=_MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> dict[str, Any]:
    """List ingested documents with pagination.

    Args:
        limit: Maximum number of documents to return (1–200, default: 50).
        offset: Number of documents to skip (>= 0, default: 0).
        document_repo: The injected document repository.

    Returns:
        JSON with ``documents`` list and pagination metadata.
    """
    documents = await document_repo.list_documents(limit=limit, offset=offset)

    return {
        "documents": [
            {
                "document_id": doc.id,
                "filename": doc.filename,
                "status": doc.status.value,
                "file_type": doc.file_type,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
        "limit": limit,
        "offset": offset,
        "count": len(documents),
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> dict[str, Any]:
    """Delete a document and all its associated data.

    Removes the document record, all its chunks from PostgreSQL, and all
    its vectors from Qdrant.

    Args:
        document_id: The document's unique identifier.
        document_repo: The injected document repository.

    Returns:
        JSON confirmation of deletion.

    Raises:
        DocumentNotFoundError: If no document with the given id exists.
    """
    # Check if document exists
    document = await document_repo.get_document_by_id(document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    # Delete chunks from PostgreSQL
    await document_repo.delete_chunks_for_document(document_id)

    # Delete vectors from Qdrant
    qdrant_client = get_qdrant_client()
    vector_repo = ChunkVectorRepository(qdrant_client)
    vector_repo.delete_for_document(document_id)

    # Delete document record
    await document_repo.delete_document(document_id)

    logger.info("Deleted document: %s", document_id)

    return {
        "message": "Document deleted successfully",
        "document_id": document_id,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _save_upload(file: UploadFile, storage_dir: Path, max_bytes: int) -> Path:
    """Save an uploaded file to the storage directory with sanitized filename.

    Streams the upload to disk in bounded chunks, aborting (and removing the
    partial file) as soon as the cumulative size exceeds ``max_bytes`` — so an
    oversized upload is never fully buffered in memory. The filename is reduced
    to its basename and rejected if it resolves to a path-traversal token.

    Args:
        file: The uploaded file from the request.
        storage_dir: The target directory to save the file into.
        max_bytes: Maximum allowed file size in bytes.

    Returns:
        The resolved path to the saved file.

    Raises:
        DocumentValidationError: If the filename is unsafe/missing, or the file
            exceeds ``max_bytes``.
    """
    if not file.filename:
        raise DocumentValidationError("Uploaded file has no filename")

    # Sanitize: keep only the basename; reject bare traversal tokens / absolute paths.
    filename = Path(file.filename).name
    if filename in {"", ".", ".."} or filename.startswith(("/", "\\")):
        raise DocumentValidationError(f"Unsafe filename: {file.filename}")

    storage_dir.mkdir(parents=True, exist_ok=True)
    target = storage_dir / filename

    written = 0
    try:
        with target.open("wb") as buffer:
            while chunk := await file.read(_UPLOAD_CHUNK_SIZE):
                written += len(chunk)
                if written > max_bytes:
                    raise DocumentValidationError(
                        f"File too large: exceeds limit of {max_bytes // (1024 * 1024)} MB"
                    )
                buffer.write(chunk)
    except DocumentValidationError:
        target.unlink(missing_ok=True)  # remove the partial file
        raise

    logger.info("Saved upload: %s (%d bytes)", filename, written)
    return target
