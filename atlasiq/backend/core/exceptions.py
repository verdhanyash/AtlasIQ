"""Custom exception hierarchy for AtlasIQ.

All application-specific exceptions inherit from AtlasIQError, making it
possible to catch all domain errors with a single except clause. Each
exception carries a human-readable message suitable for API error responses.
"""

from __future__ import annotations


class AtlasIQError(Exception):
    """Base exception for all AtlasIQ domain errors."""

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(self.message)


# ── Configuration & Startup ──────────────────────────────────────────────────


class ConfigurationError(AtlasIQError):
    """Raised when application configuration is invalid or incomplete."""


class StartupError(AtlasIQError):
    """Raised when a required service or resource is unavailable at startup."""


# ── Document Ingestion ───────────────────────────────────────────────────────


class DocumentValidationError(AtlasIQError):
    """Raised when a document fails validation (unsupported type, too large, etc.)."""


class DocumentParsingError(AtlasIQError):
    """Raised when a document cannot be parsed into text."""


class ChunkingError(AtlasIQError):
    """Raised when text chunking fails."""


class EmbeddingError(AtlasIQError):
    """Raised when embedding generation fails."""


class DocumentNotFoundError(AtlasIQError):
    """Raised when a requested document does not exist."""


# ── Retrieval & Query ────────────────────────────────────────────────────────


class RetrievalError(AtlasIQError):
    """Raised when the retrieval pipeline encounters an error."""


class LLMProviderError(AtlasIQError):
    """Raised when the LLM provider returns an error or is unreachable."""


class PromptTemplateError(AtlasIQError):
    """Raised when a prompt template is missing or malformed."""


# ── Database ─────────────────────────────────────────────────────────────────


class DatabaseConnectionError(AtlasIQError):
    """Raised when a database (PostgreSQL or Qdrant) connection fails."""


class DatabaseQueryError(AtlasIQError):
    """Raised when a database query fails unexpectedly."""
