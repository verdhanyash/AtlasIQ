"""Tests for the document embedder module.

Verifies that ``DocumentEmbedder`` correctly generates embeddings using
sentence-transformers, handles batching, validates input, and manages lazy
model loading. All tests use mocked models — no actual model downloads or GPU.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from atlasiq.backend.core.config import EmbeddingConfig
from atlasiq.backend.core.exceptions import EmbeddingError


# Mock sentence_transformers at module level before importing embedder
_mock_sentence_transformers = MagicMock()
sys.modules["sentence_transformers"] = _mock_sentence_transformers

from atlasiq.ingestion.embedder import DocumentEmbedder  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def default_config() -> EmbeddingConfig:
    """Provide default embedding configuration."""
    return EmbeddingConfig()


@pytest.fixture
def small_batch_config() -> EmbeddingConfig:
    """Provide config with small batch size for testing."""
    return EmbeddingConfig(batch_size=2)


@pytest.fixture
def mock_model() -> MagicMock:
    """Provide a mocked SentenceTransformer model.

    The mock returns fixed 768-dimensional embeddings for any input.
    """
    model = MagicMock()
    # Mock dimension property
    model.get_sentence_embedding_dimension.return_value = 768

    # Mock encode to return numpy-like arrays (lists that have .tolist())
    def mock_encode(texts: str | list[str], **kwargs: dict) -> MagicMock:
        if isinstance(texts, str):
            # Single text → single embedding
            embedding = MagicMock()
            embedding.tolist.return_value = [0.1] * 768
            return embedding
        else:
            # List of texts → list of embeddings
            embeddings = []
            for _ in texts:
                embedding = MagicMock()
                embedding.tolist.return_value = [0.1] * 768
                embeddings.append(embedding)
            return embeddings

    model.encode.side_effect = mock_encode
    return model


@pytest.fixture
def embedder_with_mock(
    default_config: EmbeddingConfig, mock_model: MagicMock
) -> DocumentEmbedder:
    """Provide an embedder with a pre-loaded mocked model."""
    # Directly inject the mocked model
    embedder = DocumentEmbedder(default_config)
    embedder._model = mock_model
    embedder._dimension = 768
    return embedder


# ── Initialisation ───────────────────────────────────────────────────────────


class TestInitialisation:
    """Tests for embedder initialisation."""

    def test_init_stores_config(self, default_config: EmbeddingConfig) -> None:
        """Initialisation should store configuration values."""
        embedder = DocumentEmbedder(default_config)
        assert embedder.model_name == default_config.model_name
        assert embedder.batch_size == default_config.batch_size
        assert embedder.device == default_config.device

    def test_init_does_not_load_model(self, default_config: EmbeddingConfig) -> None:
        """Initialisation should not load the model immediately (lazy loading)."""
        embedder = DocumentEmbedder(default_config)
        assert embedder._model is None
        assert embedder._dimension is None

    def test_custom_batch_size(self, small_batch_config: EmbeddingConfig) -> None:
        """Custom batch size should be stored correctly."""
        embedder = DocumentEmbedder(small_batch_config)
        assert embedder.batch_size == 2


# ── Dimension property ───────────────────────────────────────────────────────


class TestDimension:
    """Tests for the dimension property."""

    def test_dimension_triggers_model_load(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """Accessing dimension should trigger lazy model loading."""
        # Mock the SentenceTransformer constructor in the mocked module
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=mock_model)
        
        embedder = DocumentEmbedder(default_config)
        assert embedder._model is None  # Not loaded yet
        dim = embedder.dimension
        assert dim == 768
        assert embedder._model is not None  # Now loaded

    def test_dimension_cached(self, embedder_with_mock: DocumentEmbedder) -> None:
        """Dimension should be cached after first access."""
        dim1 = embedder_with_mock.dimension
        dim2 = embedder_with_mock.dimension
        assert dim1 == dim2 == 768
        # get_sentence_embedding_dimension should be called only once
        assert embedder_with_mock._model.get_sentence_embedding_dimension.call_count == 0  # Already cached

    def test_dimension_invalid_raises(
        self, default_config: EmbeddingConfig
    ) -> None:
        """Model returning invalid dimension should raise EmbeddingError."""
        bad_model = MagicMock()
        bad_model.get_sentence_embedding_dimension.return_value = 0
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=bad_model)
        
        embedder = DocumentEmbedder(default_config)
        with pytest.raises(EmbeddingError, match="Invalid embedding dimension"):
            _ = embedder.dimension

    def test_dimension_none_raises(self, default_config: EmbeddingConfig) -> None:
        """Model returning None dimension should raise EmbeddingError."""
        bad_model = MagicMock()
        bad_model.get_sentence_embedding_dimension.return_value = None
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=bad_model)
        
        embedder = DocumentEmbedder(default_config)
        with pytest.raises(EmbeddingError, match="Invalid embedding dimension"):
            _ = embedder.dimension


# ── embed() method ───────────────────────────────────────────────────────────


class TestEmbed:
    """Tests for the embed() method."""

    def test_embed_single_text(self, embedder_with_mock: DocumentEmbedder) -> None:
        """Embedding a single text should return one vector."""
        texts = ["This is a document chunk."]
        embeddings = embedder_with_mock.embed(texts)
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768

    def test_embed_multiple_texts(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """Embedding multiple texts should return multiple vectors."""
        texts = ["First chunk.", "Second chunk.", "Third chunk."]
        embeddings = embedder_with_mock.embed(texts)
        assert len(embeddings) == 3
        for embedding in embeddings:
            assert len(embedding) == 768

    def test_embed_adds_document_prefix(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """embed() should prepend 'search_document: ' to each text."""
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=mock_model)
        
        embedder = DocumentEmbedder(default_config)
        texts = ["Chunk one.", "Chunk two."]
        embedder.embed(texts)

        # Check that encode was called with prefixed texts
        call_args = mock_model.encode.call_args
        prefixed_texts = call_args[0][0]
        assert prefixed_texts[0] == "search_document: Chunk one."
        assert prefixed_texts[1] == "search_document: Chunk two."

    def test_embed_uses_batch_size(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """embed() should pass batch_size to the model's encode method."""
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=mock_model)
        
        embedder = DocumentEmbedder(default_config)
        texts = ["Text A", "Text B", "Text C"]
        embedder.embed(texts)

        call_args = mock_model.encode.call_args
        assert call_args[1]["batch_size"] == default_config.batch_size

    def test_embed_empty_list_raises(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """Embedding an empty list should raise EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty list"):
            embedder_with_mock.embed([])

    def test_embed_non_string_raises(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """Embedding non-string inputs should raise EmbeddingError."""
        with pytest.raises(EmbeddingError, match="must be strings"):
            embedder_with_mock.embed([123, 456])  # type: ignore[list-item]

    def test_embed_empty_string_raises(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """Embedding empty or whitespace-only strings should raise EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty or whitespace"):
            embedder_with_mock.embed(["Valid text", "", "Another valid text"])

    def test_embed_whitespace_only_raises(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """Embedding whitespace-only strings should raise EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty or whitespace"):
            embedder_with_mock.embed(["Text one", "   \n\t  ", "Text two"])

    def test_embed_model_failure_raises(
        self, default_config: EmbeddingConfig
    ) -> None:
        """Model encode failure should raise EmbeddingError."""
        bad_model = MagicMock()
        bad_model.get_sentence_embedding_dimension.return_value = 768
        bad_model.encode.side_effect = RuntimeError("GPU out of memory")
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=bad_model)
        
        embedder = DocumentEmbedder(default_config)
        with pytest.raises(EmbeddingError, match="Embedding generation failed"):
            embedder.embed(["Some text"])


# ── embed_query() method ─────────────────────────────────────────────────────


class TestEmbedQuery:
    """Tests for the embed_query() method."""

    def test_embed_query_returns_vector(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """embed_query() should return a single embedding vector."""
        query = "What is AtlasIQ?"
        embedding = embedder_with_mock.embed_query(query)
        assert len(embedding) == 768

    def test_embed_query_adds_query_prefix(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """embed_query() should prepend 'search_query: ' to the query."""
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=mock_model)
        
        embedder = DocumentEmbedder(default_config)
        query = "How does retrieval work?"
        embedder.embed_query(query)

        # Check that encode was called with prefixed query
        call_args = mock_model.encode.call_args
        prefixed_query = call_args[0][0]
        assert prefixed_query == "search_query: How does retrieval work?"

    def test_embed_query_empty_string_raises(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """embed_query() with empty string should raise EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty or whitespace"):
            embedder_with_mock.embed_query("")

    def test_embed_query_whitespace_only_raises(
        self, embedder_with_mock: DocumentEmbedder
    ) -> None:
        """embed_query() with whitespace-only string should raise EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty or whitespace"):
            embedder_with_mock.embed_query("   \n\t  ")

    def test_embed_query_model_failure_raises(
        self, default_config: EmbeddingConfig
    ) -> None:
        """Model encode failure for query should raise EmbeddingError."""
        bad_model = MagicMock()
        bad_model.get_sentence_embedding_dimension.return_value = 768
        bad_model.encode.side_effect = RuntimeError("Model error")
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=bad_model)
        
        embedder = DocumentEmbedder(default_config)
        with pytest.raises(EmbeddingError, match="Query embedding generation failed"):
            embedder.embed_query("Some query")


# ── Lazy loading ─────────────────────────────────────────────────────────────


class TestLazyLoading:
    """Tests for lazy model loading behaviour."""

    def test_model_not_loaded_on_init(
        self, default_config: EmbeddingConfig
    ) -> None:
        """Model should not be loaded during __init__."""
        embedder = DocumentEmbedder(default_config)
        assert embedder._model is None

    def test_model_loaded_on_first_embed(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """Model should be loaded on first embed() call."""
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=mock_model)
        
        embedder = DocumentEmbedder(default_config)
        assert embedder._model is None
        embedder.embed(["Test text"])
        assert embedder._model is not None

    def test_model_loaded_on_first_embed_query(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """Model should be loaded on first embed_query() call."""
        _mock_sentence_transformers.SentenceTransformer = MagicMock(return_value=mock_model)
        
        embedder = DocumentEmbedder(default_config)
        assert embedder._model is None
        embedder.embed_query("Test query")
        assert embedder._model is not None

    def test_model_loaded_only_once(
        self, default_config: EmbeddingConfig, mock_model: MagicMock
    ) -> None:
        """Model should be loaded only once across multiple calls."""
        mock_constructor = MagicMock(return_value=mock_model)
        _mock_sentence_transformers.SentenceTransformer = mock_constructor
        
        embedder = DocumentEmbedder(default_config)
        embedder.embed(["Text 1"])
        embedder.embed(["Text 2"])
        embedder.embed_query("Query")
        # SentenceTransformer constructor should be called exactly once
        assert mock_constructor.call_count == 1

    def test_import_error_raises(self, default_config: EmbeddingConfig) -> None:
        """Missing sentence-transformers package should raise EmbeddingError."""
        # Temporarily remove the mock
        original = sys.modules.get("sentence_transformers")
        del sys.modules["sentence_transformers"]
        
        try:
            embedder = DocumentEmbedder(default_config)
            with pytest.raises(EmbeddingError, match="sentence-transformers is not installed"):
                embedder.embed(["Some text"])
        finally:
            # Restore the mock
            if original:
                sys.modules["sentence_transformers"] = original

    def test_model_load_failure_raises(
        self, default_config: EmbeddingConfig
    ) -> None:
        """Model loading failure should raise EmbeddingError."""
        _mock_sentence_transformers.SentenceTransformer = MagicMock(
            side_effect=RuntimeError("Model not found")
        )
        
        embedder = DocumentEmbedder(default_config)
        with pytest.raises(EmbeddingError, match="Failed to load embedding model"):
            embedder.embed(["Some text"])


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge case inputs and scenarios."""

    def test_large_batch(self, embedder_with_mock: DocumentEmbedder) -> None:
        """Embedding a large batch of texts should work correctly."""
        texts = [f"Document chunk {i}" for i in range(100)]
        embeddings = embedder_with_mock.embed(texts)
        assert len(embeddings) == 100
        for embedding in embeddings:
            assert len(embedding) == 768

    def test_unicode_text(self, embedder_with_mock: DocumentEmbedder) -> None:
        """Unicode characters in text should be handled correctly."""
        texts = ["日本語のテキスト", "Текст на русском", "النص العربي"]
        embeddings = embedder_with_mock.embed(texts)
        assert len(embeddings) == 3

    def test_long_text(self, embedder_with_mock: DocumentEmbedder) -> None:
        """Very long text should be embedded without error."""
        text = "word " * 10000  # ~50,000 characters
        embeddings = embedder_with_mock.embed([text])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768

    def test_special_characters(self, embedder_with_mock: DocumentEmbedder) -> None:
        """Text with special characters should be handled correctly."""
        texts = [
            "Text with\nnewlines\nand\ttabs",
            "Text with symbols: @#$%^&*()",
            "Text with quotes: \"double\" and 'single'",
        ]
        embeddings = embedder_with_mock.embed(texts)
        assert len(embeddings) == 3


# ── Integration with config ──────────────────────────────────────────────────


class TestConfigIntegration:
    """Tests for integration with EmbeddingConfig."""

    def test_default_config_values(self) -> None:
        """Default config should have expected values."""
        config = EmbeddingConfig()
        assert config.model_name == "nomic-ai/nomic-embed-text-v1.5"
        assert config.batch_size == 32
        assert config.device == "cpu"

    def test_custom_config_values(self) -> None:
        """Custom config values should be respected."""
        config = EmbeddingConfig(
            model_name="custom-model",
            batch_size=16,
            device="cuda",
        )
        embedder = DocumentEmbedder(config)
        assert embedder.model_name == "custom-model"
        assert embedder.batch_size == 16
        assert embedder.device == "cuda"

    def test_device_passed_to_model(
        self, mock_model: MagicMock
    ) -> None:
        """Device setting should be passed to SentenceTransformer."""
        config = EmbeddingConfig(device="cuda")
        mock_constructor = MagicMock(return_value=mock_model)
        _mock_sentence_transformers.SentenceTransformer = mock_constructor
        
        embedder = DocumentEmbedder(config)
        embedder.embed(["Test"])
        # Check that device was passed to the constructor
        call_kwargs = mock_constructor.call_args[1]
        assert call_kwargs["device"] == "cuda"
