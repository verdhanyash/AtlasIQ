"""Answer guardrails — evidence gating and confidence scoring.

Determines whether the system has enough retrieval evidence to answer a
question confidently, and produces a refusal when evidence is weak or absent.

This is a **pure decision component**: it does not retrieve, prompt, or generate
— it gates on retrieval scores and returns a pass/refusal decision plus a
confidence score. The guardrails reuse the refusal message contract already
present in the system prompt (``"I don't have enough information to answer this
question based on the available documents."``).

Guardrails operate on a simple principle: if the top-scoring retrieval result
falls below a configured threshold, the evidence is considered too weak to
generate a trustworthy answer, and the system refuses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from atlasiq.retrieval.citations import Citation
    from atlasiq.retrieval.models import RetrievedChunk

logger = logging.getLogger(__name__)

# The refusal message that matches the system prompt's instruction
_REFUSAL_MESSAGE = (
    "I don't have enough information to answer this question "
    "based on the available documents."
)


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    """The result of a guardrail check.

    Attributes:
        passed: Whether the evidence met the confidence threshold.
        answer: The answer to return (either generated or refusal message).
        citations: Citations to include with the answer (empty on refusal).
        confidence_score: Confidence derived from retrieval scores (0.0-1.0).
        refusal_reason: Optional reason for refusal (present when passed=False).
    """

    passed: bool
    answer: str
    citations: list[Citation]
    confidence_score: float
    refusal_reason: str | None = None


class Guardrails:
    """Evidence-gating guardrails for query answering.

    Checks whether retrieved chunks meet a minimum confidence threshold and
    returns a pass/refusal decision. When evidence is weak (top score below
    threshold) or absent (no chunks), the system refuses to answer.

    The confidence score is computed from retrieval scores and attached to
    every response (pass or refusal).
    """

    def __init__(self, min_confidence_score: float) -> None:
        """Initialise guardrails with a confidence threshold.

        Args:
            min_confidence_score: Minimum score for the top retrieval result
                to pass the guardrail. If the top chunk scores below this,
                the system refuses to answer. Typically 0.0-1.0 range.

        Note:
            Retrieval scores are model-dependent and not absolute confidence
            values. The threshold should be tuned through evaluation on your
            specific corpus and embedding model rather than treated as a
            universal confidence measure.
        """
        if min_confidence_score < 0:
            msg = f"min_confidence_score must be >= 0, got {min_confidence_score}"
            raise ValueError(msg)

        self._min_confidence_score = min_confidence_score
        logger.info(
            "Guardrails initialised with min_confidence_score=%.2f",
            min_confidence_score,
        )

    def check(
        self,
        generated_answer: str,
        chunks: Sequence[RetrievedChunk],
        citations: list[Citation],
    ) -> GuardrailDecision:
        """Check whether the evidence supports answering the question.

        Args:
            generated_answer: The answer produced by the LLM (may be discarded
                if guardrails refuse).
            chunks: The retrieved chunks that were used to generate the answer.
            citations: The citations built from the chunks.

        Returns:
            A :class:`GuardrailDecision` indicating pass/refusal, the final
            answer (generated or refusal message), citations (present only on
            pass), and a confidence score.
        """
        if not chunks:
            # No retrieval results → out-of-corpus refusal
            logger.info("Guardrail refusal: no chunks retrieved (out-of-corpus)")
            return GuardrailDecision(
                passed=False,
                answer=_REFUSAL_MESSAGE,
                citations=[],
                confidence_score=0.0,
                refusal_reason="no_retrieval_results",
            )

        # Confidence is derived from the top retrieval score (highest relevance)
        top_score = max(chunk.score for chunk in chunks)
        confidence = self._compute_confidence(top_score)

        if top_score < self._min_confidence_score:
            # Top score below threshold → weak evidence refusal
            logger.info(
                "Guardrail refusal: top score %.3f < threshold %.3f (weak evidence)",
                top_score,
                self._min_confidence_score,
            )
            return GuardrailDecision(
                passed=False,
                answer=_REFUSAL_MESSAGE,
                citations=[],
                confidence_score=confidence,
                refusal_reason="weak_evidence",
            )

        # Evidence sufficient → pass with generated answer and citations
        logger.info(
            "Guardrail passed: top score %.3f >= threshold %.3f (confidence=%.2f)",
            top_score,
            self._min_confidence_score,
            confidence,
        )
        return GuardrailDecision(
            passed=True,
            answer=generated_answer,
            citations=citations,
            confidence_score=confidence,
            refusal_reason=None,
        )

    @staticmethod
    def _compute_confidence(top_score: float) -> float:
        """Compute a normalised confidence score from the top retrieval score.

        In V1, confidence is simply the top score clamped to [0.0, 1.0].
        Future versions may apply more sophisticated scoring (e.g., incorporating
        score distribution, citation count, or LLM uncertainty).

        Args:
            top_score: The highest retrieval score among the chunks.

        Returns:
            A normalised confidence score in [0.0, 1.0].
        """
        return max(0.0, min(1.0, top_score))
