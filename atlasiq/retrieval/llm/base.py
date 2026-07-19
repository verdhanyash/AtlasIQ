"""LLM provider protocol.

Defines the structural contract that every LLM provider must satisfy.  The
interface accepts a :class:`BuiltPrompt` (produced by :class:`PromptBuilder`)
and returns the model's answer as a plain string.  Providers are transport-only:
they send the request, parse the response, and translate failures into
:class:`LLMProviderError`.  No retries, streaming, validation, or
post-processing belongs here.

The protocol is structural (like :class:`atlasiq.retrieval.protocols.Retriever`)
so concrete implementations satisfy it by shape — no explicit inheritance
required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from atlasiq.retrieval.prompt_builder import BuiltPrompt


@runtime_checkable
class LLMProvider(Protocol):
    """A component that generates an answer from a fully rendered prompt."""

    def generate(self, prompt: BuiltPrompt) -> str:
        """Send a prompt to the language model and return the answer text.

        Args:
            prompt: The fully rendered prompt (system + user messages).

        Returns:
            The model's answer as a plain string.

        Raises:
            LLMProviderError: If the provider is unreachable, the request
                fails, or the model returns an empty/unusable response.
        """
        ...

    def close(self) -> None:
        """Release underlying HTTP/transport resources.

        Called by the composition root during shutdown.  Safe to call
        multiple times.
        """
        ...
