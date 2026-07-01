"""PostgreSQL client for AtlasIQ.

Manages async connection pooling via SQLAlchemy's async engine. Provides
connection lifecycle methods and a health check for startup validation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from atlasiq.backend.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class PostgresClient:
    """Async PostgreSQL client with connection pooling.

    Attributes:
        engine: SQLAlchemy async engine managing the connection pool.
        session_factory: Factory for creating async database sessions.
    """

    def __init__(self, dsn: str, pool_min_size: int = 2, pool_max_size: int = 10) -> None:
        """Initialize the PostgreSQL client.

        Args:
            dsn: PostgreSQL connection string (asyncpg dialect).
            pool_min_size: Minimum connections in the pool.
            pool_max_size: Maximum connections in the pool.
        """
        self.engine: AsyncEngine = create_async_engine(
            dsn,
            pool_size=pool_min_size,
            max_overflow=pool_max_size - pool_min_size,
            echo=False,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )
        logger.info("PostgreSQL client initialized: pool_min=%d, pool_max=%d", pool_min_size, pool_max_size)

    async def initialize_schema(self) -> None:
        """Execute the schema DDL to create tables if they don't exist.

        Reads and executes database/schema.sql. Safe to call multiple times
        due to IF NOT EXISTS clauses.
        """
        if not SCHEMA_PATH.exists():
            msg = f"Schema file not found at {SCHEMA_PATH}"
            raise DatabaseConnectionError(msg)

        schema_sql = SCHEMA_PATH.read_text()
        async with self.engine.begin() as conn:
            # Execute each statement separately since asyncpg doesn't support
            # multiple statements in a single execute call
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))

        logger.info("PostgreSQL schema initialized successfully")

    async def health_check(self) -> bool:
        """Check if PostgreSQL is reachable.

        Returns:
            True if the database responds to a simple query.
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            logger.exception("PostgreSQL health check failed")
            return False

    async def get_session(self) -> AsyncSession:
        """Create a new async database session.

        Returns:
            An AsyncSession instance. Caller is responsible for closing it,
            or use it as an async context manager.
        """
        return self.session_factory()

    async def close(self) -> None:
        """Close the connection pool and release all connections."""
        await self.engine.dispose()
        logger.info("PostgreSQL connection pool closed")
