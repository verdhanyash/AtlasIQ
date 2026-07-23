"""Document embedding generation for the ingestion pipeline.

Uses sentence-transformers with the nomic-embed-text-v1.5 model to generate
dense embeddings for text chunks. The model is lazily loaded on first use to
avoid cold-start costs when not needed.

Automatically prepends the required prefixes:
- ``search_document: `` for document chunks
- ``search_query: `` for user queries

All parameters are injected via ``EmbeddingConfig``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlasiq.backend.core.config import EmbeddingConfig  # noqa: TCH001
from atlasiq.backend.core.exceptions import EmbeddingError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Prefixes required by the nomic-embed-text-v1.5 model
_DOCUMENT_PREFIX = "search_document: "
_QUERY_PREFIX = "search_query: "


class DocumentEmbedder:
    """Generates embeddings for document chunks using sentence-transformers.

    The embedding model is lazily loaded on first invocation. Supports
    batched processing and automatically handles the required prefixes
    for the nomic-embed-text-v1.5 model.

    Attributes:
        model_name: HuggingFace model identifier.
        batch_size: Number of texts to embed in a single batch.
        device: Device to run the model on (cpu, cuda, mps).
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialise the embedder from configuration.

        Args:
            config: Embedding parameters (model name, batch size, device).
        """
        self.model_name: str = config.model_name
        self.batch_size: int = config.batch_size
        self.device: str = config.device

        self._model: SentenceTransformer | None = None
        self._dimension: int | None = None

        logger.info(
            "Embedder configured: model=%s, batch_size=%d, device=%s",
            self.model_name,
            self.batch_size,
            self.device,
        )

    @property
    def dimension(self) -> int:
        """Get the embedding dimension of the model.

        Returns:
            The embedding vector dimension.

        Raises:
            EmbeddingError: If the model cannot be loaded or has no dimension.
        """
        if self._dimension is None:
            self._ensure_model_loaded()
            if self._model is None:
                raise EmbeddingError("Model failed to load")

            # Extract dimension from the model's pooling configuration
            try:
                dimension = self._model.get_sentence_embedding_dimension()
                if dimension is None or dimension <= 0:
                    raise EmbeddingError(
                        f"Invalid embedding dimension: {dimension}"
                    )
                self._dimension = dimension
            except Exception as e:
                raise EmbeddingError(
                    f"Failed to get embedding dimension: {e}"
                ) from e

        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of document chunks.

        Automatically prepends ``search_document: `` to each text and
        processes them in batches.

        Args:
            texts: List of document chunks to embed.

        Returns:
            A list of embedding vectors (one per input text).

        Raises:
            EmbeddingError: If input is invalid or embedding generation fails.
        """
        if not texts:
            raise EmbeddingError("Cannot embed an empty list of texts")

        if not all(isinstance(t, str) for t in texts):
            raise EmbeddingError("All inputs must be strings")

        if any(not t.strip() for t in texts):
            raise EmbeddingError("Cannot embed empty or whitespace-only text")

        self._ensure_model_loaded()

        # Prepend the document prefix to each text
        prefixed_texts = [_DOCUMENT_PREFIX + text for text in texts]

        logger.info("Embedding %d texts in batches of %d", len(texts), self.batch_size)

        try:
            # encode returns numpy arrays; convert to Python lists
            embeddings = self._model.encode(  # type: ignore[union-attr]
                prefixed_texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            # Convert numpy array to list of lists
            result: list[list[float]] = [
                embedding.tolist() for embedding in embeddings
            ]
            return result
        except Exception as e:
            raise EmbeddingError(f"Embedding generation failed: {e}") from e

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a user query.

        Automatically prepends ``search_query: `` to the query text.

        Args:
            query: The user query text.

        Returns:
            A single embedding vector.

        Raises:
            EmbeddingError: If the query is invalid or embedding generation fails.
        """
        if not query or not query.strip():
            raise EmbeddingError("Cannot embed an empty or whitespace-only query")

        self._ensure_model_loaded()

        prefixed_query = _QUERY_PREFIX + query

        logger.info("Embedding query")

        try:
            # encode returns a numpy array; convert to Python list
            embedding = self._model.encode(  # type: ignore[union-attr]
                prefixed_query,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            result: list[float] = embedding.tolist()
            return result
        except Exception as e:
            raise EmbeddingError(f"Query embedding generation failed: {e}") from e

    def _ensure_model_loaded(self) -> None:
        """Lazy-load the sentence-transformers model on first use.

        Raises:
            EmbeddingError: If the model cannot be loaded.
        """
        if self._model is not None:
            return

        logger.info("Loading embedding model: %s", self.model_name)

        try:
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                )
            except Exception as online_err:
                logger.warning("Online load failed for '%s' (%s), attempting local cache load...", self.model_name, online_err)
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    local_files_only=True,
                )
            logger.info("Embedding model loaded successfully")
        except ImportError as e:
            raise EmbeddingError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            raise EmbeddingError(
                f"Failed to load embedding model '{self.model_name}': {e}"
            ) from e
