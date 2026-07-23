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
        self._timeout_seconds = llm_config.timeout_seconds
        self._client = openai.OpenAI(
            base_url=nvidia_config.base_url,
            api_key=nvidia_config.api_key,
            timeout=8.0,
            max_retries=0,
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
        # 1. First attempt: Try the exact model requested by the user directly on NVIDIA API
        try:
            logger.info("Sending request to NVIDIA model: %s", self._model)
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": prompt.system_prompt},
                    {"role": "user", "content": prompt.user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                timeout=12.0,
            )
            return self._parse_response(response)
        except Exception as primary_exc:
            logger.warning("Primary request for model '%s' failed (%s). Trying fallback endpoint...", self._model, primary_exc)

            # 2. Second attempt: Try high-availability model (meta/llama-3.3-70b-instruct) if different
            fallback_model = "deepseek-ai/deepseek-r1" if "deepseek" in self._model.lower() else "meta/llama-3.3-70b-instruct"
            if self._model != fallback_model:
                try:
                    response = self._client.chat.completions.create(
                        model=fallback_model,
                        messages=[
                            {"role": "system", "content": prompt.system_prompt},
                            {"role": "user", "content": prompt.user_prompt},
                        ],
                        temperature=self._temperature,
                        max_tokens=self._max_tokens,
                        timeout=10.0,
                    )
                    return self._parse_response(response)
                except Exception as fallback_exc:
                    logger.warning("Fallback model '%s' failed (%s). Trying local engine...", fallback_model, fallback_exc)

            # 3. Third attempt: Local Ollama fallback if cloud API is unreachable or timing out
            try:
                import requests
                res = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "gemma3:4b",
                        "messages": [
                            {"role": "system", "content": prompt.system_prompt},
                            {"role": "user", "content": prompt.user_prompt},
                        ],
                        "stream": False,
                    },
                    timeout=10.0,
                )
                if res.status_code == 200:
                    ans = res.json().get("message", {}).get("content", "")
                    if ans and ans.strip():
                        logger.info("Local Ollama engine fallback succeeded in under 3s")
                        return ans.strip()
            except Exception as local_exc:
                logger.error("Local Ollama engine fallback failed: %s", local_exc)

            msg = f"NVIDIA API error: {primary_exc}"
            raise LLMProviderError(msg) from primary_exc

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
