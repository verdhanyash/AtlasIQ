"""Unit tests for the answer generator (M2-8).

All tests are offline — the LLM provider is mocked.

Coverage:
- Prompt passed through to the provider unchanged
- Answer returned from the provider unchanged
- LLMProviderError propagated without swallowing
- Unrelated exceptions (programming bugs) are NOT caught
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from atlasiq.backend.core.exceptions import LLMProviderError
from atlasiq.retrieval.generator import AnswerGenerator
from atlasiq.retrieval.prompt_builder import BuiltPrompt

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def prompt() -> BuiltPrompt:
    return BuiltPrompt(
        system_prompt="You are a helpful assistant.",
        user_prompt="What is AtlasIQ?",
    )


@pytest.fixture()
def mock_provider() -> MagicMock:
    """A mock LLM provider with a default successful response."""
    provider = MagicMock()
    provider.generate.return_value = "AtlasIQ is a RAG system."
    return provider


# ── Happy Path ───────────────────────────────────────────────────────────────


class TestGenerate:
    """Tests for :meth:`AnswerGenerator.generate`."""

    def test_returns_provider_answer(
        self, mock_provider: MagicMock, prompt: BuiltPrompt
    ) -> None:
        """The generator returns the exact string from the provider."""
        generator = AnswerGenerator(mock_provider)
        result = generator.generate(prompt)
        assert result == "AtlasIQ is a RAG system."

    def test_passes_prompt_to_provider(
        self, mock_provider: MagicMock, prompt: BuiltPrompt
    ) -> None:
        """The BuiltPrompt is forwarded to the provider unchanged."""
        generator = AnswerGenerator(mock_provider)
        generator.generate(prompt)

        mock_provider.generate.assert_called_once_with(prompt)

    def test_provider_called_exactly_once(
        self, mock_provider: MagicMock, prompt: BuiltPrompt
    ) -> None:
        """The provider is invoked exactly once per generate() call."""
        generator = AnswerGenerator(mock_provider)
        generator.generate(prompt)
        generator.generate(prompt)

        assert mock_provider.generate.call_count == 2


# ── Error Propagation ────────────────────────────────────────────────────────


class TestErrorPropagation:
    """Tests for error handling in :class:`AnswerGenerator`."""

    def test_llm_provider_error_propagates(
        self, prompt: BuiltPrompt
    ) -> None:
        """LLMProviderError from the provider propagates to the caller."""
        provider = MagicMock()
        provider.generate.side_effect = LLMProviderError("model unreachable")

        generator = AnswerGenerator(provider)
        with pytest.raises(LLMProviderError, match="model unreachable"):
            generator.generate(prompt)

    def test_unexpected_errors_not_swallowed(
        self, prompt: BuiltPrompt
    ) -> None:
        """Programming bugs (TypeError, etc.) are NOT caught by the generator."""
        provider = MagicMock()
        provider.generate.side_effect = TypeError("bad argument")

        generator = AnswerGenerator(provider)
        with pytest.raises(TypeError, match="bad argument"):
            generator.generate(prompt)
