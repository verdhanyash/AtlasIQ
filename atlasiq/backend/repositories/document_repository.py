"""PostgreSQL repository for documents and chunks.

Owns all raw SQL for the ``documents`` and ``chunks`` tables. This is the only
place in the codebase that reads or writes those tables — the pipeline and API
speak in :class:`DocumentRecord` / :class:`ChunkRecord` domain objects and never
see SQL or driver types.

All queries use bound parameters (never string interpolation) to prevent SQL
injection. Every ``SQLAlchemyError`` is wrapped in ``DatabaseQueryError`` so the
driver's exception types never leak past this boundary (DL-012).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from atlasiq.backend.core.exceptions import DatabaseQueryError
from atlasiq.backend.domain import ChunkRecord, DocumentRecord, DocumentStatus

if TYPE_CHECKING:
    from sqlalchemy import RowMapping

    from atlasiq.database.postgres_client import PostgresClient

logger = logging.getLogger(__name__)

# Default pagination limit for list queries. A true constant, not a user-facing
# configurable value — callers override via the explicit ``limit`` argument.
_DEFAULT_LIST_LIMIT = 50


class DocumentRepository:
    """Async data-access layer for documents and their chunks.

    Translates between AtlasIQ domain records and the PostgreSQL ``documents``
    and ``chunks`` tables. Depends on an injected :class:`PostgresClient` for
    session management.
    """

    def __init__(self, client: PostgresClient) -> None:
        """Initialise the repository.

        Args:
            client: The PostgreSQL client providing the session factory.
        """
        self._client = client

    async def upsert_document(self, document: DocumentRecord) -> None:
        """Insert a document or update it if the id already exists.

        On conflict, updates the mutable columns (status, hashes, counts,
        timestamps) while preserving the original ``created_at``.

        Args:
            document: The document record to persist.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text(
            """
            INSERT INTO documents (
                id, filename, file_hash, file_type, file_size_bytes,
                title, author, page_count, word_count, status,
                created_at, updated_at, ingested_at
            ) VALUES (
                :id, :filename, :file_hash, :file_type, :file_size_bytes,
                :title, :author, :page_count, :word_count, :status,
                :created_at, :updated_at, :ingested_at
            )
            ON CONFLICT (id) DO UPDATE SET
                filename = EXCLUDED.filename,
                file_hash = EXCLUDED.file_hash,
                file_type = EXCLUDED.file_type,
                file_size_bytes = EXCLUDED.file_size_bytes,
                title = EXCLUDED.title,
                author = EXCLUDED.author,
                page_count = EXCLUDED.page_count,
                word_count = EXCLUDED.word_count,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at,
                ingested_at = EXCLUDED.ingested_at
            """
        )
        params = {
            "id": document.id,
            "filename": document.filename,
            "file_hash": document.file_hash,
            "file_type": document.file_type,
            "file_size_bytes": document.file_size_bytes,
            "title": document.title,
            "author": document.author,
            "page_count": document.page_count,
            "word_count": document.word_count,
            "status": document.status.value,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "ingested_at": document.ingested_at,
        }

        try:
            async with self._client.session_factory() as session:
                await session.execute(sql, params)
                await session.commit()
        except SQLAlchemyError as exc:
            msg = f"Failed to upsert document '{document.id}': {exc}"
            raise DatabaseQueryError(msg) from exc

        logger.info("Upserted document %s (status=%s)", document.id, document.status.value)

    async def get_document_by_id(self, document_id: str) -> DocumentRecord | None:
        """Fetch a document by its id.

        Args:
            document_id: The document id to look up.

        Returns:
            The matching :class:`DocumentRecord`, or ``None`` if not found.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text("SELECT * FROM documents WHERE id = :id")
        try:
            async with self._client.session_factory() as session:
                result = await session.execute(sql, {"id": document_id})
                row = result.mappings().first()
        except SQLAlchemyError as exc:
            msg = f"Failed to fetch document '{document_id}': {exc}"
            raise DatabaseQueryError(msg) from exc

        return self._row_to_document(row) if row else None

    async def get_document_by_hash(self, file_hash: str) -> DocumentRecord | None:
        """Fetch a document by its content hash.

        Used by the ingestion pipeline to decide whether a file is new,
        modified, or unchanged without maintaining a separate registry.

        Args:
            file_hash: The SHA-256 hex digest to look up.

        Returns:
            The matching :class:`DocumentRecord`, or ``None`` if not found.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text("SELECT * FROM documents WHERE file_hash = :file_hash LIMIT 1")
        try:
            async with self._client.session_factory() as session:
                result = await session.execute(sql, {"file_hash": file_hash})
                row = result.mappings().first()
        except SQLAlchemyError as exc:
            msg = f"Failed to fetch document by hash: {exc}"
            raise DatabaseQueryError(msg) from exc

        return self._row_to_document(row) if row else None

    async def update_status(self, document_id: str, status: DocumentStatus) -> None:
        """Update the lifecycle status of a document.

        Args:
            document_id: The document to update.
            status: The new status.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text(
            "UPDATE documents SET status = :status, updated_at = NOW() WHERE id = :id"
        )
        try:
            async with self._client.session_factory() as session:
                await session.execute(sql, {"status": status.value, "id": document_id})
                await session.commit()
        except SQLAlchemyError as exc:
            msg = f"Failed to update status for document '{document_id}': {exc}"
            raise DatabaseQueryError(msg) from exc

        logger.info("Updated document %s status to %s", document_id, status.value)

    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None:
        """Insert a batch of chunks in a single transaction.

        Args:
            chunks: The chunk records to insert. An empty list is a no-op.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        if not chunks:
            return

        sql = text(
            """
            INSERT INTO chunks (
                id, document_id, chunk_index, content,
                token_count, start_page, end_page, metadata_json
            ) VALUES (
                :id, :document_id, :chunk_index, :content,
                :token_count, :start_page, :end_page,
                CAST(:metadata_json AS JSONB)
            )
            """
        )
        params = [
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "start_page": chunk.start_page,
                "end_page": chunk.end_page,
                "metadata_json": json.dumps(chunk.metadata),
            }
            for chunk in chunks
        ]

        try:
            async with self._client.session_factory() as session:
                await session.execute(sql, params)
                await session.commit()
        except SQLAlchemyError as exc:
            msg = f"Failed to insert {len(chunks)} chunks: {exc}"
            raise DatabaseQueryError(msg) from exc

        logger.info("Inserted %d chunks", len(chunks))

    async def delete_chunks_for_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a document.

        Used by the re-index path when a document has been modified, before
        inserting the freshly generated chunks.

        Args:
            document_id: The owning document id.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text("DELETE FROM chunks WHERE document_id = :document_id")
        try:
            async with self._client.session_factory() as session:
                await session.execute(sql, {"document_id": document_id})
                await session.commit()
        except SQLAlchemyError as exc:
            msg = f"Failed to delete chunks for document '{document_id}': {exc}"
            raise DatabaseQueryError(msg) from exc

        logger.info("Deleted chunks for document %s", document_id)

    async def count_chunks_for_document(self, document_id: str) -> int:
        """Count the chunks belonging to a document.

        Args:
            document_id: The owning document id.

        Returns:
            The number of chunks stored for the document (0 if none).

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text("SELECT COUNT(*) FROM chunks WHERE document_id = :document_id")
        try:
            async with self._client.session_factory() as session:
                result = await session.execute(sql, {"document_id": document_id})
                count = result.scalar()
        except SQLAlchemyError as exc:
            msg = f"Failed to count chunks for document '{document_id}': {exc}"
            raise DatabaseQueryError(msg) from exc

        return int(count) if count is not None else 0

    async def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[ChunkRecord]:
        """Fetch chunks by their ids, preserving the requested order.

        Used to hydrate retrieval results: a retriever returns ranked chunk ids,
        and this method resolves them to full chunk records (content + pages) for
        prompting and citation. The returned list follows the order of
        ``chunk_ids`` (not the arbitrary order the database returns), so the
        retrieval ranking is preserved. Ids with no matching row are dropped.

        Args:
            chunk_ids: The chunk ids to fetch, in ranked order. Empty is a no-op.

        Returns:
            The matching :class:`ChunkRecord` objects in ``chunk_ids`` order.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        if not chunk_ids:
            return []

        sql = text("SELECT * FROM chunks WHERE id = ANY(:ids)")
        try:
            async with self._client.session_factory() as session:
                result = await session.execute(sql, {"ids": chunk_ids})
                rows = result.mappings().all()
        except SQLAlchemyError as exc:
            msg = f"Failed to fetch chunks by ids: {exc}"
            raise DatabaseQueryError(msg) from exc

        by_id = {row["id"]: self._row_to_chunk(row) for row in rows}
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    async def list_all_chunks(self) -> list[ChunkRecord]:
        """Fetch every chunk in the store, ordered by document then position.

        Used to build the in-memory BM25 lexical index over the whole corpus.
        For the focused V1 corpus this is a cheap full read; it is intentionally
        not paginated.

        Returns:
            All :class:`ChunkRecord` objects, ordered by ``document_id`` then
            ``chunk_index``.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text("SELECT * FROM chunks ORDER BY document_id, chunk_index")
        try:
            async with self._client.session_factory() as session:
                result = await session.execute(sql)
                rows = result.mappings().all()
        except SQLAlchemyError as exc:
            msg = f"Failed to list all chunks: {exc}"
            raise DatabaseQueryError(msg) from exc

        return [self._row_to_chunk(row) for row in rows]

    async def list_documents(
        self, limit: int = _DEFAULT_LIST_LIMIT, offset: int = 0
    ) -> list[DocumentRecord]:
        """List documents ordered by creation time (newest first).

        Args:
            limit: Maximum number of documents to return.
            offset: Number of documents to skip (for pagination).

        Returns:
            A list of :class:`DocumentRecord` objects.

        Raises:
            DatabaseQueryError: If the query fails.
        """
        sql = text(
            "SELECT * FROM documents ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        )
        try:
            async with self._client.session_factory() as session:
                result = await session.execute(sql, {"limit": limit, "offset": offset})
                rows = result.mappings().all()
        except SQLAlchemyError as exc:
            msg = f"Failed to list documents: {exc}"
            raise DatabaseQueryError(msg) from exc

        return [self._row_to_document(row) for row in rows]

    @staticmethod
    def _row_to_document(row: RowMapping) -> DocumentRecord:
        """Map a database row mapping to a :class:`DocumentRecord`.

        Args:
            row: A SQLAlchemy row mapping from the ``documents`` table.

        Returns:
            The reconstructed domain record.
        """
        return DocumentRecord(
            id=row["id"],
            filename=row["filename"],
            file_hash=row["file_hash"],
            file_type=row["file_type"],
            file_size_bytes=row["file_size_bytes"],
            status=DocumentStatus(row["status"]),
            title=row["title"],
            author=row["author"],
            page_count=row["page_count"],
            word_count=row["word_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            ingested_at=row["ingested_at"],
        )

    @staticmethod
    def _row_to_chunk(row: RowMapping) -> ChunkRecord:
        """Map a database row mapping to a :class:`ChunkRecord`.

        The ``metadata_json`` JSONB column may come back either already decoded
        to a ``dict`` or as a raw JSON ``str`` depending on the driver codec, so
        both are handled defensively.

        Args:
            row: A SQLAlchemy row mapping from the ``chunks`` table.

        Returns:
            The reconstructed domain record.
        """
        raw_metadata = row["metadata_json"]
        if isinstance(raw_metadata, str):
            metadata = json.loads(raw_metadata) if raw_metadata else {}
        elif isinstance(raw_metadata, dict):
            metadata = raw_metadata
        else:
            metadata = {}

        return ChunkRecord(
            id=row["id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            token_count=row["token_count"],
            start_page=row["start_page"],
            end_page=row["end_page"],
            metadata=metadata,
        )
