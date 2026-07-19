"""LLM provider factory.

Selects and constructs the correct :class:`LLMProvider` implementation based on
the ``provider`` field in :class:`LLMConfig`.  This module is the single place
where provider selection happens — callers (DI providers, tests) never need to
import concrete provider classes directly.

Separated from ``__init__.py`` because factory logic tends to grow as new
providers are added; keeping it in its own module follows SRP.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlasiq.backend.core.exceptions import ConfigurationError
from atlasiq.retrieval.llm.nvidia_provider import NvidiaProvider
from atlasiq.retrieval.llm.ollama_provider import OllamaProvider

if TYPE_CHECKING:
    from atlasiq.backend.core.config import LLMConfig, NvidiaConfig, OllamaConfig
    from atlasiq.retrieval.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def create_llm_provider(
    llm_config: LLMConfig,
    ollama_config: OllamaConfig,
    nvidia_config: NvidiaConfig,
) -> LLMProvider:
    """Create an LLM provider based on the configured provider name.

    Args:
        llm_config: Shared LLM settings including ``provider`` selector.
        ollama_config: Ollama-specific settings (used when provider is
            ``"ollama"``).
        nvidia_config: NVIDIA-specific settings (used when provider is
            ``"nvidia"``).

    Returns:
        A concrete provider satisfying the :class:`LLMProvider` protocol.

    Raises:
        ConfigurationError: If ``llm_config.provider`` is not a supported
            value.
    """
    provider = llm_config.provider

    if provider == "ollama":
        logger.info("Creating Ollama LLM provider")
        return OllamaProvider(llm_config, ollama_config)

    if provider == "nvidia":
        logger.info("Creating NVIDIA LLM provider")
        return NvidiaProvider(llm_config, nvidia_config)

    msg = (
        f"Unsupported LLM provider: '{provider}'. "
        f"Supported providers: 'ollama', 'nvidia'."
    )
    raise ConfigurationError(msg)
