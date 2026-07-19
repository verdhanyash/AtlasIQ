"""LLM provider package — provider-agnostic text generation.

Exports the protocol, concrete providers, and the factory.  Business logic
(factory selection) lives in :mod:`~atlasiq.retrieval.llm.factory`, not here.
"""

from atlasiq.retrieval.llm.base import LLMProvider
from atlasiq.retrieval.llm.factory import create_llm_provider
from atlasiq.retrieval.llm.nvidia_provider import NvidiaProvider
from atlasiq.retrieval.llm.ollama_provider import OllamaProvider

__all__ = [
    "LLMProvider",
    "NvidiaProvider",
    "OllamaProvider",
    "create_llm_provider",
]
