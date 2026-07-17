"""Tests for the prompt builder.

Fully offline (DL-014): templates are written to ``tmp_path``; chunks are
constructed directly. Verifies field names, per-chunk formatting, placeholder
substitution, empty-context handling, eager validation (fail fast), brace
robustness, and template caching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from atlasiq.backend.core.exceptions import PromptTemplateError
from atlasiq.backend.domain import ChunkRecord
from atlasiq.retrieval.models import RetrievedChunk
from atlasiq.retrieval.prompt_builder import BuiltPrompt, PromptBuilder

if TYPE_CHECKING:
    from pathlib import Path

_QA = "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
_SYSTEM = "You are AtlasIQ. Answer only from the context."

# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_templates(tmp_path: Path, qa: str = _QA, system: str = _SYSTEM) -> Path:
    (tmp_path / "qa.txt").write_text(qa, encoding="utf-8")
    (tmp_path / "system.txt").write_text(system, encoding="utf-8")
    return tmp_path


def _builder(tmp_path: Path) -> PromptBuilder:
    return PromptBuilder(tmp_path, "qa.txt", "system.txt")


def _chunk(
    content: str,
    filename: str = "doc.pdf",
    start_page: int | None = None,
    end_page: int | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=ChunkRecord(
            id="c-0",
            document_id="d-1",
            chunk_index=0,
            content=content,
            start_page=start_page,
            end_page=end_page,
        ),
        filename=filename,
        score=1.0,
    )


# ── BuiltPrompt field names ──────────────────────────────────────────────────


def test_builtprompt_field_names(tmp_path: Path) -> None:
    result = _builder(_write_templates(tmp_path)).build("Q?", [_chunk("text")])

    assert isinstance(result, BuiltPrompt)
    assert result.system_prompt == _SYSTEM
    assert "Q?" in result.user_prompt


# ── _format_chunk formatting ─────────────────────────────────────────────────


class TestFormatChunk:
    def test_single_page(self) -> None:
        block = PromptBuilder._format_chunk(_chunk("body", start_page=12, end_page=12))
        assert "Page: 12" in block

    def test_page_range(self) -> None:
        block = PromptBuilder._format_chunk(_chunk("body", start_page=12, end_page=14))
        assert "Page: 12-14" in block

    def test_missing_page(self) -> None:
        block = PromptBuilder._format_chunk(_chunk("body"))
        assert "Page: N/A" in block

    def test_block_structure(self) -> None:
        block = PromptBuilder._format_chunk(
            _chunk("Employees get insurance.", filename="Handbook.pdf", start_page=3)
        )
        assert "Document: Handbook.pdf" in block
        assert "Page: 3" in block
        assert "Content:" in block
        assert "Employees get insurance." in block
        assert block.count("=" * 32) == 2  # opening and closing separators


# ── Context substitution ─────────────────────────────────────────────────────


class TestContext:
    def test_content_substituted(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build("Q?", [_chunk("UNIQUE_TEXT")])
        assert "UNIQUE_TEXT" in result.user_prompt

    def test_question_substituted(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build("What is X?", [_chunk("body")])
        assert "What is X?" in result.user_prompt

    def test_multiple_chunks_joined(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build(
            "Q?", [_chunk("FIRST_CHUNK"), _chunk("SECOND_CHUNK")]
        )
        assert "FIRST_CHUNK" in result.user_prompt
        assert "SECOND_CHUNK" in result.user_prompt
        # joined by a blank line between the two blocks
        assert "\n\n" in result.user_prompt

    def test_empty_context_marker(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build("Q?", [])
        assert "(No retrieved context.)" in result.user_prompt


# ── Eager validation (fail fast) ─────────────────────────────────────────────


class TestValidation:
    def test_missing_template_file(self, tmp_path: Path) -> None:
        (tmp_path / "system.txt").write_text(_SYSTEM, encoding="utf-8")
        # qa.txt does not exist
        with pytest.raises(PromptTemplateError, match="Could not read"):
            PromptBuilder(tmp_path, "qa.txt", "system.txt")

    def test_missing_context_placeholder(self, tmp_path: Path) -> None:
        _write_templates(tmp_path, qa="Only {question} here")
        with pytest.raises(PromptTemplateError, match="placeholders"):
            _builder(tmp_path)

    def test_missing_question_placeholder(self, tmp_path: Path) -> None:
        _write_templates(tmp_path, qa="Only {context} here")
        with pytest.raises(PromptTemplateError, match="placeholders"):
            _builder(tmp_path)

    def test_empty_system_prompt(self, tmp_path: Path) -> None:
        _write_templates(tmp_path, system="   \n\t  ")
        with pytest.raises(PromptTemplateError, match="System prompt"):
            _builder(tmp_path)


# ── Brace robustness (str.replace, not str.format) ───────────────────────────


class TestBraceRobustness:
    def test_literal_braces_in_content(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build(
            "Q?", [_chunk("config = {key: value} and {unclosed")]
        )
        assert "{key: value}" in result.user_prompt
        assert "{unclosed" in result.user_prompt

    def test_literal_braces_in_question(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build(
            "What does {x} mean in {namespace}?", [_chunk("body")]
        )
        assert "{x}" in result.user_prompt
        assert "{namespace}" in result.user_prompt


# ── Question normalization ───────────────────────────────────────────────────


class TestQuestionNormalization:
    def test_leading_trailing_whitespace_trimmed(self, tmp_path: Path) -> None:
        result = _builder(_write_templates(tmp_path)).build(
            "   What is X?  \n", [_chunk("body")]
        )
        assert "Question: What is X?" in result.user_prompt
        # the surrounding whitespace is gone
        assert "   What is X?" not in result.user_prompt

    def test_blank_question_raises(self, tmp_path: Path) -> None:
        builder = _builder(_write_templates(tmp_path))
        with pytest.raises(ValueError, match="empty question"):
            builder.build("   \n\t ", [_chunk("body")])

    def test_empty_string_question_raises(self, tmp_path: Path) -> None:
        builder = _builder(_write_templates(tmp_path))
        with pytest.raises(ValueError, match="empty question"):
            builder.build("", [_chunk("body")])


# ── Chunk order preservation ─────────────────────────────────────────────────


def test_preserves_input_chunk_order(tmp_path: Path) -> None:
    # Deliberately unsorted-by-score to prove the builder does NOT re-sort.
    chunks = [
        _chunk("ALPHA_CHUNK"),
        _chunk("BETA_CHUNK"),
        _chunk("GAMMA_CHUNK"),
    ]
    result = _builder(_write_templates(tmp_path)).build("Q?", chunks)

    pos_alpha = result.user_prompt.index("ALPHA_CHUNK")
    pos_beta = result.user_prompt.index("BETA_CHUNK")
    pos_gamma = result.user_prompt.index("GAMMA_CHUNK")
    assert pos_alpha < pos_beta < pos_gamma


# ── Unicode / UTF-8 handling ─────────────────────────────────────────────────


def test_unicode_content_preserved(tmp_path: Path) -> None:
    unicode_text = "कर्मचारी बीमा · 従業員保険 · benefits 🎉"
    result = _builder(_write_templates(tmp_path)).build("Q?", [_chunk(unicode_text)])
    assert unicode_text in result.user_prompt


def test_unicode_question_preserved(tmp_path: Path) -> None:
    result = _builder(_write_templates(tmp_path)).build(
        "बीमा क्या है? 🤔", [_chunk("body")]
    )
    assert "बीमा क्या है? 🤔" in result.user_prompt


# ── Context length helper ────────────────────────────────────────────────────


def test_context_length_helper() -> None:
    assert PromptBuilder._context_length("") == 0
    assert PromptBuilder._context_length("hello") == 5
    assert PromptBuilder._context_length("नमस्ते") == len("नमस्ते")


# ── Template caching (read once) ─────────────────────────────────────────────


def test_templates_cached_at_construction(tmp_path: Path) -> None:
    builder = _builder(_write_templates(tmp_path, qa="V1 {context} {question}"))

    # Overwrite the file on disk AFTER construction.
    (tmp_path / "qa.txt").write_text("V2 {context} {question}", encoding="utf-8")

    result = builder.build("Q?", [_chunk("body")])

    # The cached (original) template is used, not the modified file.
    assert result.user_prompt.startswith("V1 ")
    assert "V2" not in result.user_prompt
