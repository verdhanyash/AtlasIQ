"""Unit tests for the LLM provider layer (M2-7).

All tests are offline — no network calls, no model downloads.  HTTP clients
are mocked at the transport boundary.

Coverage:
- OllamaProvider: request shape, message order, response parsing, error wrapping
- NvidiaProvider: client construction, call args, response parsing, error wrapping
- Factory: correct provider selection, unknown provider error
- Protocol: both providers satisfy the LLMProvider protocol
- Client reuse: clients are created once, not per-request
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest

from atlasiq.backend.core.config import LLMConfig, NvidiaConfig, OllamaConfig
from atlasiq.backend.core.exceptions import ConfigurationError, LLMProviderError
from atlasiq.retrieval.llm.base import LLMProvider
from atlasiq.retrieval.llm.factory import create_llm_provider
from atlasiq.retrieval.llm.nvidia_provider import NvidiaProvider
from atlasiq.retrieval.llm.ollama_provider import OllamaProvider
from atlasiq.retrieval.prompt_builder import BuiltPrompt

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def llm_config() -> LLMConfig:
    """Minimal LLM config for testing."""
    return LLMConfig(
        provider="ollama",
        model="test-model",
        temperature=0.5,
        max_tokens=256,
        timeout_seconds=10,
    )


@pytest.fixture()
def ollama_config() -> OllamaConfig:
    return OllamaConfig(base_url="http://localhost:11434")


@pytest.fixture()
def nvidia_config() -> NvidiaConfig:
    return NvidiaConfig(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="test-api-key",
    )


@pytest.fixture()
def prompt() -> BuiltPrompt:
    """A sample built prompt."""
    return BuiltPrompt(
        system_prompt="You are a helpful assistant.",
        user_prompt="What is AtlasIQ?",
    )


def _ollama_success_response(content: str = "AtlasIQ is great.") -> httpx.Response:
    """Build a mock successful Ollama /api/chat response."""


    return httpx.Response(
        status_code=200,
        json={"message": {"role": "assistant", "content": content}},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )


# ── OllamaProvider ──────────────────────────────────────────────────────────


class TestOllamaProvider:
    """Tests for :class:`OllamaProvider`."""

    def test_generate_sends_correct_request(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """The POST body has the right model, messages, and options."""
        with patch.object(httpx.Client, "post", return_value=_ollama_success_response()) as mock_post:
            provider = OllamaProvider(llm_config, ollama_config)
            provider.generate(prompt)

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs.args[0] == "http://localhost:11434/api/chat"

            body = call_kwargs.kwargs["json"]
            assert body["model"] == "test-model"
            assert body["stream"] is False
            assert body["options"]["temperature"] == 0.5
            assert body["options"]["num_predict"] == 256

    def test_message_order_system_first_user_second(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """System message must come first, user message second."""
        with patch.object(httpx.Client, "post", return_value=_ollama_success_response()):
            provider = OllamaProvider(llm_config, ollama_config)
            provider.generate(prompt)

            body = httpx.Client.post.call_args.kwargs["json"]  # type: ignore[attr-defined]
            messages = body["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == prompt.system_prompt
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == prompt.user_prompt

    def test_generate_returns_content(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """Successful generation returns the model's content string."""
        with patch.object(
            httpx.Client, "post", return_value=_ollama_success_response("The answer.")
        ):
            provider = OllamaProvider(llm_config, ollama_config)
            result = provider.generate(prompt)
            assert result == "The answer."

    def test_timeout_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        with patch.object(httpx.Client, "post", side_effect=httpx.ReadTimeout("timeout")):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="timed out"):
                provider.generate(prompt)

    def test_connection_error_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("refused")):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="request failed"):
                provider.generate(prompt)

    def test_http_error_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """Non-2xx status codes are wrapped in LLMProviderError."""
        error_response = httpx.Response(
            status_code=500,
            request=httpx.Request("POST", "http://localhost:11434/api/chat"),
        )
        with patch.object(httpx.Client, "post", return_value=error_response):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="HTTP 500"):
                provider.generate(prompt)

    def test_malformed_json_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """If Ollama returns non-JSON, we get LLMProviderError."""
        bad_response = httpx.Response(
            status_code=200,
            content=b"not json",
            request=httpx.Request("POST", "http://localhost:11434/api/chat"),
        )
        with patch.object(httpx.Client, "post", return_value=bad_response):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="invalid JSON"):
                provider.generate(prompt)

    def test_missing_content_key_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        response = httpx.Response(
            status_code=200,
            json={"unexpected": "shape"},
            request=httpx.Request("POST", "http://localhost:11434/api/chat"),
        )
        with patch.object(httpx.Client, "post", return_value=response):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="message.content"):
                provider.generate(prompt)

    def test_empty_content_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """Empty/whitespace model output is treated as a generation failure."""
        with patch.object(httpx.Client, "post", return_value=_ollama_success_response("   ")):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="empty response"):
                provider.generate(prompt)

    def test_null_content_raises_llm_provider_error(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """Null message.content is treated as a generation failure."""
        response = httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": None}},
            request=httpx.Request("POST", "http://localhost:11434/api/chat"),
        )
        with patch.object(httpx.Client, "post", return_value=response):
            provider = OllamaProvider(llm_config, ollama_config)
            with pytest.raises(LLMProviderError, match="empty response"):
                provider.generate(prompt)

    def test_client_reused_across_calls(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, prompt: BuiltPrompt
    ) -> None:
        """The httpx.Client is created once and reused, not recreated per request."""
        with patch.object(httpx.Client, "post", return_value=_ollama_success_response()):
            provider = OllamaProvider(llm_config, ollama_config)
            client_id = id(provider._client)

            provider.generate(prompt)
            provider.generate(prompt)

            assert id(provider._client) == client_id

    def test_trailing_slash_in_base_url(
        self, llm_config: LLMConfig, prompt: BuiltPrompt
    ) -> None:
        """Trailing slash in base_url is stripped to avoid double slashes."""
        config = OllamaConfig(base_url="http://localhost:11434/")
        with patch.object(httpx.Client, "post", return_value=_ollama_success_response()) as mock_post:
            provider = OllamaProvider(llm_config, config)
            provider.generate(prompt)
            assert mock_post.call_args.args[0] == "http://localhost:11434/api/chat"

    def test_close_is_idempotent(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig
    ) -> None:
        """Calling close() multiple times does not raise."""
        provider = OllamaProvider(llm_config, ollama_config)
        provider.close()
        provider.close()  # second call must not raise


# ── NvidiaProvider ───────────────────────────────────────────────────────────


class TestNvidiaProvider:
    """Tests for :class:`NvidiaProvider`."""

    @staticmethod
    def _mock_completion(content: str = "NVIDIA answer.") -> MagicMock:
        """Build a mock ChatCompletion response."""
        message = MagicMock()
        message.content = content

        choice = MagicMock()
        choice.message = message

        completion = MagicMock()
        completion.choices = [choice]
        return completion

    def test_generate_calls_create_with_correct_args(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        """Verify the SDK create() call receives the right arguments."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_completion()

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            provider.generate(prompt)

            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["model"] == "test-model"
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["max_tokens"] == 256

    def test_message_order_system_first_user_second(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        """System message must come first, user message second."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_completion()

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            provider.generate(prompt)

            messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == prompt.system_prompt
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == prompt.user_prompt

    def test_generate_returns_content(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_completion("The NVIDIA answer.")

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            result = provider.generate(prompt)
            assert result == "The NVIDIA answer."

    def test_client_constructed_with_config(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig
    ) -> None:
        """The OpenAI client is constructed with base_url, api_key, and timeout."""
        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI") as mock_openai:
            NvidiaProvider(llm_config, nvidia_config)
            mock_openai.assert_called_once_with(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key="test-api-key",
                timeout=10,
            )

    def test_api_timeout_raises_llm_provider_error(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            with pytest.raises(LLMProviderError, match="timed out"):
                provider.generate(prompt)

    def test_api_error_raises_llm_provider_error(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIStatusError(
            message="server error",
            response=MagicMock(status_code=500),
            body=None,
        )

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            with pytest.raises(LLMProviderError, match="API error"):
                provider.generate(prompt)

    def test_empty_content_raises_llm_provider_error(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        """Empty/whitespace model output is treated as a generation failure."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_completion("  ")

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            with pytest.raises(LLMProviderError, match="empty response"):
                provider.generate(prompt)

    def test_null_content_raises_llm_provider_error(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        """Null message.content is treated as a generation failure."""
        mock_client = MagicMock()
        completion = self._mock_completion()
        completion.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = completion

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            with pytest.raises(LLMProviderError, match="empty response"):
                provider.generate(prompt)

    def test_no_choices_raises_llm_provider_error(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        mock_client = MagicMock()
        empty_completion = MagicMock()
        empty_completion.choices = []
        mock_client.chat.completions.create.return_value = empty_completion

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            with pytest.raises(LLMProviderError, match="no choices"):
                provider.generate(prompt)

    def test_client_reused_across_calls(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig, prompt: BuiltPrompt
    ) -> None:
        """The openai.OpenAI client is created once and reused, not recreated per request."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_completion()

        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client) as mock_ctor:
            provider = NvidiaProvider(llm_config, nvidia_config)
            provider.generate(prompt)
            provider.generate(prompt)

            # Constructor called exactly once (at __init__), not per generate()
            mock_ctor.assert_called_once()

    def test_close_is_idempotent(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig
    ) -> None:
        """Calling close() multiple times does not raise."""
        mock_client = MagicMock()
        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI", return_value=mock_client):
            provider = NvidiaProvider(llm_config, nvidia_config)
            provider.close()
            provider.close()  # second call must not raise
            assert mock_client.close.call_count == 2


# ── Factory ──────────────────────────────────────────────────────────────────


class TestFactory:
    """Tests for :func:`create_llm_provider`."""

    def test_ollama_selection(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig, nvidia_config: NvidiaConfig
    ) -> None:
        with patch.object(httpx, "Client"):
            provider = create_llm_provider(llm_config, ollama_config, nvidia_config)
            assert isinstance(provider, OllamaProvider)

    def test_nvidia_selection(
        self, ollama_config: OllamaConfig, nvidia_config: NvidiaConfig
    ) -> None:
        config = LLMConfig(provider="nvidia", model="m", temperature=0.1, max_tokens=64, timeout_seconds=5)
        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI"):
            provider = create_llm_provider(config, ollama_config, nvidia_config)
            assert isinstance(provider, NvidiaProvider)

    def test_unknown_provider_raises_configuration_error(
        self, ollama_config: OllamaConfig, nvidia_config: NvidiaConfig
    ) -> None:
        # LLMConfig validates provider against an allowlist, so we bypass it.
        config = MagicMock(spec=LLMConfig)
        config.provider = "unknown"
        with pytest.raises(ConfigurationError, match="Unsupported LLM provider"):
            create_llm_provider(config, ollama_config, nvidia_config)


# ── Protocol Conformance ────────────────────────────────────────────────────


class TestProtocolConformance:
    """Both providers satisfy the :class:`LLMProvider` protocol."""

    def test_ollama_satisfies_protocol(
        self, llm_config: LLMConfig, ollama_config: OllamaConfig
    ) -> None:
        with patch.object(httpx, "Client"):
            provider = OllamaProvider(llm_config, ollama_config)
            assert isinstance(provider, LLMProvider)

    def test_nvidia_satisfies_protocol(
        self, llm_config: LLMConfig, nvidia_config: NvidiaConfig
    ) -> None:
        with patch("atlasiq.retrieval.llm.nvidia_provider.openai.OpenAI"):
            provider = NvidiaProvider(llm_config, nvidia_config)
            assert isinstance(provider, LLMProvider)
