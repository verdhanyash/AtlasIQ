"""Ollama LLM provider.

Sends chat-completion requests to a local Ollama instance via its
``/api/chat`` REST endpoint.  The ``httpx.Client`` is created once in the
constructor and reused for every :meth:`generate` call.

This provider is **transport-only**: it formats the HTTP request, parses the
JSON response, and translates transport or API failures into
:class:`LLMProviderError`.  It does not retry, stream, validate prompts, count
tokens, or post-process answers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from atlasiq.backend.core.exceptions import LLMProviderError

if TYPE_CHECKING:
    from atlasiq.backend.core.config import LLMConfig, OllamaConfig
    from atlasiq.retrieval.prompt_builder import BuiltPrompt

logger = logging.getLogger(__name__)


class OllamaProvider:
    """LLM provider backed by a local Ollama server.

    Satisfies the :class:`~atlasiq.retrieval.llm.base.LLMProvider` protocol
    structurally — no inheritance required.

    Attributes:
        _client: Reusable ``httpx.Client`` for all requests.
        _chat_url: Full URL to Ollama's ``/api/chat`` endpoint.
        _model: Model identifier (e.g. ``gemma3:4b``).
        _temperature: Sampling temperature.
        _max_tokens: Maximum tokens to generate (Ollama's ``num_predict``).
    """

    def __init__(self, llm_config: LLMConfig, ollama_config: OllamaConfig) -> None:
        """Initialise the Ollama provider.

        Args:
            llm_config: Shared LLM settings (model, temperature, max_tokens,
                timeout_seconds).
            ollama_config: Ollama-specific settings (base_url).
        """
        base_url = ollama_config.base_url.rstrip("/")
        self._chat_url = f"{base_url}/api/chat"
        self._model = llm_config.model
        self._temperature = llm_config.temperature
        self._max_tokens = llm_config.max_tokens
        self._client = httpx.Client(timeout=llm_config.timeout_seconds)
        logger.info(
            "Ollama provider initialised: url=%s, model=%s",
            self._chat_url,
            self._model,
        )

    def generate(self, prompt: BuiltPrompt) -> str:
        """Send a chat-completion request to Ollama and return the answer.

        Args:
            prompt: The fully rendered prompt (system + user messages).

        Returns:
            The model's answer text.

        Raises:
            LLMProviderError: On network/timeout errors, non-2xx responses,
                malformed JSON, or empty model output.
        """
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }

        try:
            response = self._client.post(self._chat_url, json=body)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            msg = f"Ollama request timed out: {exc}"
            raise LLMProviderError(msg) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                msg = (
                    f"Ollama returned HTTP 404 for model '{self._model}'. "
                    f"Please pull the model using `ollama pull {self._model}` in your terminal, "
                    f"or set ATLASIQ_LLM__PROVIDER=mock in environment/config for local demo mode."
                )
            else:
                msg = f"Ollama returned HTTP {exc.response.status_code}: {exc}"
            raise LLMProviderError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"Ollama request failed: {exc}"
            raise LLMProviderError(msg) from exc

        return self._parse_response(response)

    def close(self) -> None:
        """Close the underlying ``httpx.Client``.

        Safe to call multiple times.
        """
        self._client.close()
        logger.debug("Ollama HTTP client closed")

    @staticmethod
    def _parse_response(response: httpx.Response) -> str:
        """Extract the assistant message from Ollama's JSON response.

        Args:
            response: A successful HTTP response from ``/api/chat``.

        Returns:
            The model's answer text.

        Raises:
            LLMProviderError: If the JSON is malformed, the expected keys are
                missing, or the content is empty/whitespace.
        """
        try:
            data = response.json()
        except Exception as exc:
            msg = f"Ollama returned invalid JSON: {exc}"
            raise LLMProviderError(msg) from exc

        try:
            content: str | None = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            msg = f"Ollama response missing 'message.content': {data}"
            raise LLMProviderError(msg) from exc

        if not content or not content.strip():
            raise LLMProviderError("Ollama returned an empty response.")

        logger.debug("Ollama generation completed (%d chars)", len(content))
        return content
