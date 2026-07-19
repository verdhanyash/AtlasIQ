"""NVIDIA Build LLM provider.

Sends chat-completion requests to NVIDIA's hosted API (OpenAI-compatible) via
the ``openai`` Python SDK.  The ``openai.OpenAI`` client is created once in the
constructor and reused for every :meth:`generate` call.

This provider is **transport-only**: it formats the API call, parses the
response, and translates SDK exceptions into :class:`LLMProviderError`.  It
does not retry, stream, validate prompts, count tokens, or post-process
answers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import openai

from atlasiq.backend.core.exceptions import LLMProviderError

if TYPE_CHECKING:
    from atlasiq.backend.core.config import LLMConfig, NvidiaConfig
    from atlasiq.retrieval.prompt_builder import BuiltPrompt

logger = logging.getLogger(__name__)


class NvidiaProvider:
    """LLM provider backed by NVIDIA Build (OpenAI-compatible endpoint).

    Satisfies the :class:`~atlasiq.retrieval.llm.base.LLMProvider` protocol
    structurally — no inheritance required.

    Attributes:
        _client: Reusable ``openai.OpenAI`` client.
        _model: Model identifier.
        _temperature: Sampling temperature.
        _max_tokens: Maximum tokens to generate.
    """

    def __init__(self, llm_config: LLMConfig, nvidia_config: NvidiaConfig) -> None:
        """Initialise the NVIDIA provider.

        Args:
            llm_config: Shared LLM settings (model, temperature, max_tokens,
                timeout_seconds).
            nvidia_config: NVIDIA-specific settings (base_url, api_key).
        """
        self._model = llm_config.model
        self._temperature = llm_config.temperature
        self._max_tokens = llm_config.max_tokens
        self._client = openai.OpenAI(
            base_url=nvidia_config.base_url,
            api_key=nvidia_config.api_key,
            timeout=llm_config.timeout_seconds,
        )
        logger.info(
            "NVIDIA provider initialised: base_url=%s, model=%s",
            nvidia_config.base_url,
            self._model,
        )

    def generate(self, prompt: BuiltPrompt) -> str:
        """Send a chat-completion request to NVIDIA and return the answer.

        Args:
            prompt: The fully rendered prompt (system + user messages).

        Returns:
            The model's answer text.

        Raises:
            LLMProviderError: On API errors, timeouts, or empty model output.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": prompt.system_prompt},
                    {"role": "user", "content": prompt.user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        except openai.APITimeoutError as exc:
            msg = f"NVIDIA request timed out: {exc}"
            raise LLMProviderError(msg) from exc
        except openai.APIError as exc:
            msg = f"NVIDIA API error: {exc}"
            raise LLMProviderError(msg) from exc

        return self._parse_response(response)

    def close(self) -> None:
        """Close the underlying ``openai.OpenAI`` client.

        Safe to call multiple times.
        """
        self._client.close()
        logger.debug("NVIDIA OpenAI client closed")

    @staticmethod
    def _parse_response(response: object) -> str:
        """Extract the assistant message from the completions response.

        Args:
            response: The ``ChatCompletion`` object returned by the SDK.

        Returns:
            The model's answer text.

        Raises:
            LLMProviderError: If no choices are returned or the content is
                empty/whitespace.
        """
        try:
            choices = response.choices  # type: ignore[attr-defined]
            if not choices:
                raise LLMProviderError("NVIDIA returned no choices.")

            content: str | None = choices[0].message.content
        except AttributeError as exc:
            msg = f"Unexpected NVIDIA response shape: {exc}"
            raise LLMProviderError(msg) from exc

        if not content or not content.strip():
            raise LLMProviderError("NVIDIA returned an empty response.")

        logger.debug("NVIDIA generation completed (%d chars)", len(content))
        return content
