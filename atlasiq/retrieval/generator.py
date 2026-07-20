"""Answer generator — thin coordinator for LLM generation.

Receives a :class:`BuiltPrompt` (produced by :class:`PromptBuilder`), delegates
to the injected :class:`LLMProvider`, and returns the raw answer text.  Kept as
a separate component so generation is independently testable and the
:class:`QueryPipeline` (M2-11) only orchestrates, never calls the LLM directly.

This module is **coordination-only**: it does not validate prompts, post-process
answers, build citations, or apply guardrails.  Those responsibilities belong to
their own components.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlasiq.backend.core.exceptions import LLMProviderError

if TYPE_CHECKING:
    from atlasiq.retrieval.llm.base import LLMProvider
    from atlasiq.retrieval.prompt_builder import BuiltPrompt

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates an answer from a fully rendered prompt via an LLM provider.

    Satisfies the single-responsibility principle: this class owns the
    generate-and-return step.  The pipeline owns the orchestration around it.

    Attributes:
        _llm_provider: The injected LLM provider used for text generation.
    """

    def __init__(self, llm_provider: LLMProvider) -> None:
        """Initialise the answer generator.

        Args:
            llm_provider: A concrete provider satisfying the
                :class:`LLMProvider` protocol (e.g. Ollama, NVIDIA).
        """
        self._llm_provider = llm_provider
        logger.info("AnswerGenerator initialised")

    def generate(self, prompt: BuiltPrompt) -> str:
        """Generate an answer from the given prompt.

        Args:
            prompt: The fully rendered prompt (system + user messages)
                produced by :class:`PromptBuilder`.

        Returns:
            The model's answer as a plain string.

        Raises:
            LLMProviderError: If the underlying provider fails (network,
                timeout, empty response, etc.).
        """
        logger.debug("Generating answer via LLM provider")
        try:
            answer = self._llm_provider.generate(prompt)
        except LLMProviderError:
            logger.exception("LLM generation failed")
            raise

        logger.info("Answer generated (%d chars)", len(answer))
        return answer
