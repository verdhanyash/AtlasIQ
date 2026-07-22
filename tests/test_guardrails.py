"""Unit tests for the guardrails module (M2-10).

All tests are offline — no external dependencies.

Coverage:
- GuardrailDecision dataclass structure
- Initialisation with valid/invalid threshold
- Strong evidence → pass-through
- Weak evidence (below threshold) → refusal
- Empty retrieval → out-of-corpus refusal
- Confidence score computation
- Refusal message matches system prompt contract
- Citations included on pass, excluded on refusal
"""

from __future__ import annotations

import pytest

from atlasiq.backend.domain.chunk import ChunkRecord
from atlasiq.retrieval.citations import Citation
from atlasiq.retrieval.guardrails import GuardrailDecision, Guardrails
from atlasiq.retrieval.models import RetrievedChunk

# ── Fixtures ─────────────────────────────────────────────────────────────────


def _make_chunk(score: float, content: str = "Content.") -> RetrievedChunk:
    """Helper to construct a RetrievedChunk for testing."""
    chunk_record = ChunkRecord(
        id="chunk-1",
        document_id="doc-1",
        chunk_index=0,
        content=content,
    )
    return RetrievedChunk(chunk=chunk_record, filename="doc.pdf", score=score)


def _make_citation() -> Citation:
    """Helper to construct a Citation for testing."""
    return Citation(
        document_name="doc.pdf",
        page="1",
        quote="Evidence text.",
        chunk_index=0,
        score=0.8,
    )


# ── GuardrailDecision Dataclass ──────────────────────────────────────────────


class TestGuardrailDecisionDataclass:
    """Tests for the :class:`GuardrailDecision` value object."""

    def test_fields(self) -> None:
        """GuardrailDecision has all required fields."""
        citation = _make_citation()
        decision = GuardrailDecision(
            passed=True,
            answer="Generated answer.",
            citations=[citation],
            confidence_score=0.85,
            refusal_reason=None,
        )
        assert decision.passed is True
        assert decision.answer == "Generated answer."
        assert len(decision.citations) == 1
        assert decision.confidence_score == 0.85
        assert decision.refusal_reason is None

    def test_frozen_immutability(self) -> None:
        """GuardrailDecision is frozen (fields cannot be mutated)."""
        decision = GuardrailDecision(
            passed=True,
            answer="Answer",
            citations=[],
            confidence_score=0.9,
        )
        with pytest.raises(AttributeError):
            decision.passed = False  # type: ignore[misc]

    def test_refusal_reason_optional(self) -> None:
        """refusal_reason is optional (defaults to None)."""
        decision = GuardrailDecision(
            passed=True, answer="Answer", citations=[], confidence_score=0.8
        )
        assert decision.refusal_reason is None


# ── Initialisation ───────────────────────────────────────────────────────────


class TestInitialisation:
    """Tests for :class:`Guardrails` initialisation."""

    def test_init_stores_threshold(self) -> None:
        """Threshold is stored and accessible."""
        guardrails = Guardrails(min_confidence_score=0.5)
        assert guardrails._min_confidence_score == 0.5

    def test_init_zero_threshold(self) -> None:
        """Zero threshold is valid (allows all results through)."""
        guardrails = Guardrails(min_confidence_score=0.0)
        assert guardrails._min_confidence_score == 0.0

    def test_init_negative_threshold_raises(self) -> None:
        """Negative threshold raises ValueError."""
        with pytest.raises(ValueError, match="min_confidence_score must be >= 0"):
            Guardrails(min_confidence_score=-0.1)


# ── Strong Evidence (Pass) ───────────────────────────────────────────────────


class TestStrongEvidence:
    """Tests for guardrail pass when evidence is strong."""

    def test_pass_returns_generated_answer(self) -> None:
        """Strong evidence → pass with generated answer."""
        guardrails = Guardrails(min_confidence_score=0.5)
        chunks = [_make_chunk(score=0.8)]
        citations = [_make_citation()]

        decision = guardrails.check("Generated answer.", chunks, citations)

        assert decision.passed is True
        assert decision.answer == "Generated answer."
        assert decision.refusal_reason is None

    def test_pass_includes_citations(self) -> None:
        """Citations are included when guardrail passes."""
        guardrails = Guardrails(min_confidence_score=0.5)
        chunks = [_make_chunk(score=0.9)]
        citations = [_make_citation()]

        decision = guardrails.check("Answer.", chunks, citations)

        assert len(decision.citations) == 1
        assert decision.citations[0].document_name == "doc.pdf"

    def test_pass_at_exact_threshold(self) -> None:
        """Score exactly at threshold passes."""
        guardrails = Guardrails(min_confidence_score=0.7)
        chunks = [_make_chunk(score=0.7)]

        decision = guardrails.check("Answer.", chunks, [])

        assert decision.passed is True

    def test_confidence_derived_from_heuristics(self) -> None:
        """Confidence score is computed from heuristics (document diversity, coverage)."""
        guardrails = Guardrails(min_confidence_score=0.01)
        # Single document, multiple chunks → high confidence
        chunks = [
            _make_chunk(score=0.016),  # RRF scores
            _make_chunk(score=0.015),
            _make_chunk(score=0.014),
            _make_chunk(score=0.013),
            _make_chunk(score=0.012),
        ]
        # Ensure all chunks have the same filename for single-doc scenario
        for chunk in chunks:
            chunk = RetrievedChunk(
                chunk=chunk.chunk,
                filename="doc.pdf",  # Single document
                score=chunk.score,
            )

        decision = guardrails.check("Answer.", chunks, [])

        # With single doc + 5 chunks, confidence should be high (>0.70)
        assert decision.confidence_score > 0.70


# ── Weak Evidence (Refusal) ──────────────────────────────────────────────────


class TestWeakEvidence:
    """Tests for guardrail refusal when evidence is weak."""

    def test_refusal_below_threshold(self) -> None:
        """Top score below threshold → refusal."""
        guardrails = Guardrails(min_confidence_score=0.5)
        chunks = [_make_chunk(score=0.4)]
        citations = [_make_citation()]

        decision = guardrails.check("Generated answer.", chunks, citations)

        assert decision.passed is False
        assert decision.refusal_reason == "weak_evidence"

    def test_refusal_returns_standard_message(self) -> None:
        """Refusal returns the standardised 'I don't have enough information' message."""
        guardrails = Guardrails(min_confidence_score=0.6)
        chunks = [_make_chunk(score=0.5)]

        decision = guardrails.check("Generated answer.", chunks, [])

        expected_message = (
            "I don't have enough information to answer this question "
            "based on the available documents."
        )
        assert decision.answer == expected_message

    def test_refusal_discards_generated_answer(self) -> None:
        """Generated answer is discarded when guardrail refuses."""
        guardrails = Guardrails(min_confidence_score=0.8)
        chunks = [_make_chunk(score=0.7)]

        decision = guardrails.check("Wrong answer.", chunks, [])

        assert "Wrong answer" not in decision.answer
        assert "I don't have enough information" in decision.answer

    def test_refusal_excludes_citations(self) -> None:
        """Citations are excluded when guardrail refuses."""
        guardrails = Guardrails(min_confidence_score=0.9)
        chunks = [_make_chunk(score=0.5)]
        citations = [_make_citation()]

        decision = guardrails.check("Answer.", chunks, citations)

        assert decision.citations == []

    def test_refusal_includes_confidence_score(self) -> None:
        """Confidence score is still computed and included on refusal."""
        guardrails = Guardrails(min_confidence_score=0.02)  # Use RRF-appropriate threshold
        chunks = [_make_chunk(score=0.010)]  # RRF score below threshold

        decision = guardrails.check("Answer.", chunks, [])

        # Confidence is still computed via heuristics even on refusal
        assert 0.0 <= decision.confidence_score <= 1.0


# ── Empty Retrieval (Out-of-Corpus) ──────────────────────────────────────────


class TestEmptyRetrieval:
    """Tests for guardrail behaviour when no chunks are retrieved."""

    def test_empty_chunks_refuses(self) -> None:
        """Empty chunk list → refusal."""
        guardrails = Guardrails(min_confidence_score=0.5)

        decision = guardrails.check("Generated answer.", [], [])

        assert decision.passed is False
        assert decision.refusal_reason == "no_retrieval_results"

    def test_empty_chunks_returns_standard_message(self) -> None:
        """Empty retrieval returns the standardised refusal message."""
        guardrails = Guardrails(min_confidence_score=0.5)

        decision = guardrails.check("Answer.", [], [])

        expected_message = (
            "I don't have enough information to answer this question "
            "based on the available documents."
        )
        assert decision.answer == expected_message

    def test_empty_chunks_zero_confidence(self) -> None:
        """Empty retrieval results in zero confidence."""
        guardrails = Guardrails(min_confidence_score=0.5)

        decision = guardrails.check("Answer.", [], [])

        assert decision.confidence_score == 0.0

    def test_empty_chunks_excludes_citations(self) -> None:
        """Empty retrieval → no citations included."""
        guardrails = Guardrails(min_confidence_score=0.5)

        decision = guardrails.check("Answer.", [], [_make_citation()])

        assert decision.citations == []


# ── Confidence Computation ───────────────────────────────────────────────────


class TestConfidenceComputation:
    """Tests for confidence score calculation."""

    def test_single_document_high_confidence(self) -> None:
        """Single document with multiple chunks → high confidence."""
        guardrails = Guardrails(min_confidence_score=0.01)
        chunks = [
            RetrievedChunk(
                chunk=ChunkRecord(id=f"c{i}", document_id="doc-1", chunk_index=i, content="Content"),
                filename="doc.pdf",
                score=0.016 - i * 0.001,
            )
            for i in range(5)
        ]

        decision = guardrails.check("Answer.", chunks, [])

        # Single doc → high diversity factor → high confidence
        assert decision.confidence_score >= 0.70

    def test_multiple_documents_lower_confidence(self) -> None:
        """Multiple documents → lower confidence due to scattered retrieval."""
        guardrails = Guardrails(min_confidence_score=0.01)
        chunks = [
            RetrievedChunk(
                chunk=ChunkRecord(id=f"c{i}", document_id=f"doc-{i}", chunk_index=0, content="Content"),
                filename=f"doc{i}.pdf",
                score=0.016 - i * 0.001,
            )
            for i in range(5)
        ]

        decision = guardrails.check("Answer.", chunks, [])

        # Multiple docs → low diversity factor → lower confidence
        assert decision.confidence_score < 0.70

    def test_confidence_within_valid_range(self) -> None:
        """Confidence is always in [0.0, 1.0]."""
        guardrails = Guardrails(min_confidence_score=0.01)
        chunks = [_make_chunk(score=0.016)]

        decision = guardrails.check("Answer.", chunks, [])

        assert 0.0 <= decision.confidence_score <= 1.0


# ── Multiple Chunks ──────────────────────────────────────────────────────────


class TestMultipleChunks:
    """Tests for behaviour with multiple retrieved chunks."""

    def test_uses_top_rrf_score_for_threshold(self) -> None:
        """Guardrail uses the highest RRF score for threshold comparison."""
        guardrails = Guardrails(min_confidence_score=0.015)
        chunks = [
            _make_chunk(score=0.012),
            _make_chunk(score=0.018),  # top RRF score above threshold
            _make_chunk(score=0.014),
        ]

        decision = guardrails.check("Answer.", chunks, [])

        assert decision.passed is True

    def test_weak_top_rrf_score_refuses(self) -> None:
        """Even with multiple chunks, weak top RRF score → refusal."""
        guardrails = Guardrails(min_confidence_score=0.015)
        chunks = [
            _make_chunk(score=0.013),  # top score below threshold
            _make_chunk(score=0.012),
            _make_chunk(score=0.011),
        ]

        decision = guardrails.check("Answer.", chunks, [])

        assert decision.passed is False
        assert decision.refusal_reason == "weak_evidence"


# ── Realistic Scenarios ──────────────────────────────────────────────────────


class TestRealisticScenarios:
    """End-to-end scenarios resembling real query pipeline output."""

    def test_high_quality_retrieval_passes(self) -> None:
        """High-scoring retrieval with citations → pass."""
        guardrails = Guardrails(min_confidence_score=0.01)
        chunks = [
            RetrievedChunk(
                chunk=ChunkRecord(id="c1", document_id="doc-1", chunk_index=0, content="Very relevant."),
                filename="doc1.pdf",
                score=0.018,  # RRF score
            ),
            RetrievedChunk(
                chunk=ChunkRecord(id="c2", document_id="doc-1", chunk_index=1, content="Also relevant."),
                filename="doc1.pdf",
                score=0.016,  # RRF score
            ),
        ]
        citations = [
            Citation("doc1.pdf", "5", "Very relevant.", 0, 0.018),
            Citation("doc1.pdf", "12", "Also relevant.", 1, 0.016),
        ]

        decision = guardrails.check("Based on the documents...", chunks, citations)

        assert decision.passed is True
        assert decision.answer == "Based on the documents..."
        assert len(decision.citations) == 2
        # Single document with 2 chunks → medium-high confidence
        assert decision.confidence_score >= 0.50

    def test_low_quality_retrieval_refuses(self) -> None:
        """Low RRF score → refusal despite generated answer."""
        guardrails = Guardrails(min_confidence_score=0.015)
        chunks = [_make_chunk(score=0.010, content="Barely relevant.")]  # RRF score

        decision = guardrails.check("Maybe the answer is...", chunks, [])

        assert decision.passed is False
        assert "I don't have enough information" in decision.answer
        assert decision.citations == []
        assert decision.refusal_reason == "weak_evidence"

    def test_zero_threshold_allows_everything(self) -> None:
        """Zero threshold → even very low RRF scores pass."""
        guardrails = Guardrails(min_confidence_score=0.0)
        chunks = [_make_chunk(score=0.001)]  # Very low RRF score

        decision = guardrails.check("Answer.", chunks, [])

        assert decision.passed is True
