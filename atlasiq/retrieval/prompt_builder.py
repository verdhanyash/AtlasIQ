"""Prompt construction for grounded question answering.

Turns a question plus the hydrated retrieved chunks into a ready-to-send LLM
prompt, using the templates in ``prompts/``. This component is **pure and
single-purpose**: it does not call an LLM, apply guardrails, decide refusals,
generate citations, or perform retrieval. Its only job is:

    (question + RetrievedChunks) --> BuiltPrompt

Templates are loaded and validated once at construction (fail fast). Placeholder
substitution uses ``str.replace`` rather than ``str.format`` so retrieved text
(or the question) containing literal braces cannot break rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from atlasiq.backend.core.exceptions import PromptTemplateError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from atlasiq.retrieval.models import RetrievedChunk

_CONTEXT_PLACEHOLDER = "{context}"
_QUESTION_PLACEHOLDER = "{question}"
_EMPTY_CONTEXT = "(No retrieved context.)"
_CHUNK_SEPARATOR = "=" * 32


def _format_page(start_page: int | None, end_page: int | None) -> str:
    """Render a chunk's page range: ``12``, ``12-14``, or ``N/A``."""
    if start_page is None:
        return "N/A"
    if end_page is not None and end_page != start_page:
        return f"{start_page}-{end_page}"
    return str(start_page)


@dataclass(frozen=True, slots=True)
class BuiltPrompt:
    """A fully rendered prompt, ready for the LLM provider.

    Attributes:
        system_prompt: The system message (role/rules).
        user_prompt: The QA template with context and question substituted in.
    """

    system_prompt: str
    user_prompt: str


class PromptBuilder:
    """Renders a question + retrieved chunks into a :class:`BuiltPrompt`.

    Templates are read and validated once at construction. The builder holds no
    retrieval, LLM, or policy logic — it only formats.
    """

    def __init__(self, prompts_dir: Path, qa_template: str, system_template: str) -> None:
        """Load and validate the prompt templates.

        Args:
            prompts_dir: Directory containing the template files.
            qa_template: Filename of the QA template (needs ``{context}`` and
                ``{question}`` placeholders).
            system_template: Filename of the system-prompt template.

        Raises:
            PromptTemplateError: If a template cannot be read, the QA template is
                missing a placeholder, or the system prompt is empty.
        """
        self._qa_template = self._load_template(prompts_dir / qa_template)
        self._system_prompt = self._load_template(prompts_dir / system_template)
        self._validate()

    def build(self, question: str, chunks: Sequence[RetrievedChunk]) -> BuiltPrompt:
        """Build the system + user prompt for a question and its context.

        The question is trimmed of surrounding whitespace before substitution.
        Chunks are used in the exact order given (the retrieval pipeline is the
        single owner of ranking — the builder never re-sorts).

        Args:
            question: The user's natural-language question.
            chunks: The hydrated retrieved chunks, already ranked (may be empty).

        Returns:
            A :class:`BuiltPrompt` with the system and user prompts.

        Raises:
            ValueError: If ``question`` is empty or whitespace-only.
        """
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Cannot build a prompt for an empty question.")

        context = self._format_context(chunks)
        user_prompt = self._qa_template.replace(_CONTEXT_PLACEHOLDER, context).replace(
            _QUESTION_PLACEHOLDER, normalized_question
        )
        return BuiltPrompt(system_prompt=self._system_prompt, user_prompt=user_prompt)

    # TODO(M2-10): reserved for prompt-length guardrails. Currently unused by
    # production code (only measures context size); no truncation yet.
    @staticmethod
    def _context_length(context: str) -> int:
        """Return the character length of a rendered context block.

        Preparation for prompt-length guardrails in M2-10 — this does not
        truncate or modify anything and does not affect current behaviour.

        Args:
            context: The rendered context string.

        Returns:
            The number of characters in ``context``.
        """
        return len(context)

    def _validate(self) -> None:
        """Fail fast if the cached templates are unusable."""
        missing = [
            placeholder
            for placeholder in (_CONTEXT_PLACEHOLDER, _QUESTION_PLACEHOLDER)
            if placeholder not in self._qa_template
        ]
        if missing:
            msg = f"QA template is missing required placeholders: {', '.join(missing)}"
            raise PromptTemplateError(msg)
        if not self._system_prompt.strip():
            raise PromptTemplateError("System prompt template is empty.")

    def _format_context(self, chunks: Sequence[RetrievedChunk]) -> str:
        """Render all chunks into the context block, or the empty marker."""
        if not chunks:
            return _EMPTY_CONTEXT
        return "\n\n".join(self._format_chunk(chunk) for chunk in chunks)

    @staticmethod
    def _format_chunk(chunk: RetrievedChunk) -> str:
        """Render a single retrieved chunk into a labelled context block."""
        page = _format_page(chunk.chunk.start_page, chunk.chunk.end_page)
        return (
            f"{_CHUNK_SEPARATOR}\n"
            f"Document: {chunk.filename}\n"
            f"Page: {page}\n"
            f"Content:\n"
            f"{chunk.chunk.content}\n"
            f"{_CHUNK_SEPARATOR}"
        )

    @staticmethod
    def _load_template(path: Path) -> str:
        """Read a template file as UTF-8.

        Args:
            path: Path to the template file.

        Returns:
            The template contents.

        Raises:
            PromptTemplateError: If the file cannot be read.
        """
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Could not read prompt template: {path}"
            raise PromptTemplateError(msg) from exc
