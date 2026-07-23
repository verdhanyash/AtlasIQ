"""Test script to check if documents exist in database."""
import asyncio

from atlasiq.backend.core.config import load_settings
from atlasiq.backend.repositories.document_repository import DocumentRepository
from atlasiq.database.postgres_client import PostgresClient


async def main():
    settings = load_settings()
    pg_client = PostgresClient(
        dsn=settings.database.dsn,
        pool_min_size=settings.database.pool_min_size,
        pool_max_size=settings.database.pool_max_size,
    )

    async with pg_client:
        repo = DocumentRepository(pg_client)

        print("Fetching documents from database...")
        documents = await repo.list_all_documents()

        print(f"\n✓ Found {len(documents)} documents:\n")

        for i, doc in enumerate(documents, 1):
            print(f"{i}. {doc.filename}")
            print(f"   ID: {doc.id}")
            print(f"   Status: {doc.status}")
            print(f"   Uploaded: {doc.upload_time}")
            print()

if __name__ == "__main__":
    asyncio.run(main())
