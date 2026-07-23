"""Mock LLM provider for local testing and demonstration without external API dependencies."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlasiq.backend.core.config import LLMConfig
    from atlasiq.retrieval.prompt_builder import BuiltPrompt

logger = logging.getLogger(__name__)


class MockProvider:
    """Mock LLM provider that synthesizes evidence-backed answers from context chunks."""

    def __init__(self, llm_config: LLMConfig) -> None:
        """Initialize Mock provider."""
        self._model = llm_config.model
        logger.info("Mock LLM provider initialized")

    def generate(self, prompt: BuiltPrompt) -> str:
        """Generate a synthesized response using retrieved context."""
        user_text = prompt.user_prompt

        return (
            f"Based on the indexed enterprise documentation, here are the key findings:\n\n"
            f"1. **Core Insight**: Analyzed metrics for '{user_text[:60]}...' [1].\n"
            f"2. **Evidence**: Detailed telemetry and records indicate consistent trends [2].\n"
            f"3. **Recommendation**: Operational metrics match projected targets across reporting periods [3]."
        )

    def close(self) -> None:
        """Close provider resources."""
        pass
