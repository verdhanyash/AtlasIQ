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

        # Compute confidence from chunk distribution and quality
        confidence = self._compute_confidence(chunks)

        # CRITICAL CHECK: LLM Refusal Detection
        # If LLM explicitly refuses to answer, cap confidence at 20%
        # This prevents showing high confidence when the LLM knows the answer is weak
        refusal_phrases = [
            "don't have enough information",
            "cannot answer",
            "unable to answer",
            "don't know",
            "not enough information",
            "insufficient information",
            "available documents",
        ]
        
        answer_lower = generated_answer.lower()
        llm_refused = any(phrase in answer_lower for phrase in refusal_phrases)
        
        if llm_refused:
            logger.debug(
                "LLM refusal detected in answer → capping confidence at 20%%"
            )
            # LLM explicitly refused → very low confidence regardless of retrieval patterns
            confidence = min(confidence, 0.20)

        # For minimum threshold check, use top RRF score as proxy for retrieval quality
        # (separate from user-facing confidence which uses heuristics)
        top_rrf_score = max(chunk.score for chunk in chunks)

        if top_rrf_score < self._min_confidence_score:
            # Top RRF score below threshold → weak evidence refusal
            logger.info(
                "Guardrail refusal: top RRF score %.4f < threshold %.2f (weak evidence), computed confidence=%.2f",
                top_rrf_score,
                self._min_confidence_score,
                confidence,
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
            "Guardrail passed: top RRF score %.4f >= threshold %.2f, confidence=%.2f",
            top_rrf_score,
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
    def _compute_confidence(chunks: Sequence[RetrievedChunk]) -> float:
        """Compute a normalized confidence score from retrieved chunks.

        In V1, confidence is computed using heuristics based on:
        1. **Absolute retrieval quality** (are top scores strong enough?)
        2. Document diversity (fewer unique docs = more focused = higher confidence)
        3. Number of supporting chunks (more chunks from same doc = higher confidence)
        4. Score distribution (how concentrated are top scores)

        This approach avoids the pitfall of treating RRF scores (which represent
        relative ranking, not absolute confidence) as confidence measures. RRF
        scores range from ~0.016 (rank 1) to ~0.012 (rank 20) with rrf_k=60,
        making them unsuitable for direct use as confidence percentages.

        Args:
            chunks: The retrieved chunks (already filtered/ranked).

        Returns:
            A confidence score in [0.0, 1.0]:
            - 0.75-0.95: High confidence (focused retrieval from 1-2 docs)
            - 0.50-0.74: Medium confidence (moderate diversity)
            - 0.20-0.49: Low confidence (scattered retrieval)
            - 0.00-0.19: Very low confidence (weak evidence)
        """
        if not chunks:
            return 0.0

        # CRITICAL CHECK: Absolute retrieval quality
        # If top RRF scores are too low, the retrieval is weak regardless of patterns
        top_score = chunks[0].score if chunks else 0.0
        
        # Typical strong matches: RRF score > 0.025 (chunk appears high in both retrievers)
        # Weak matches: RRF score < 0.018 (chunk only in one retriever or low-ranked)
        # THRESHOLD: If top score < 0.020, cap confidence at 25% (weak retrieval)
        if top_score < 0.020:
            logger.debug(
                "Weak retrieval quality: top RRF score %.6f < 0.020 → capping confidence at 25%%",
                top_score
            )
            # Still compute relative patterns, but cap maximum confidence
            max_confidence_cap = 0.25
        else:
            max_confidence_cap = 1.0

        # Analyze top-5 chunks for confidence signals
        top_chunks = list(chunks[:5])
        unique_docs = set(chunk.filename for chunk in top_chunks)
        num_unique = len(unique_docs)
        num_chunks = len(top_chunks)

        # Signal 1: Document diversity (lower is better)
        # 1 unique doc → diversity_factor = 1.0
        # 2 unique docs → diversity_factor = 0.8
        # 3+ unique docs → diversity_factor = 0.6
        if num_unique == 1:
            diversity_factor = 1.0
        elif num_unique == 2:
            diversity_factor = 0.8
        else:
            diversity_factor = 0.6

        # Signal 2: Chunk count (more supporting chunks = more confident)
        # 5 chunks → coverage_factor = 1.0
        # 3 chunks → coverage_factor = 0.8
        # 1 chunk → coverage_factor = 0.6
        coverage_factor = min(1.0, 0.4 + (num_chunks * 0.12))

        # Signal 3: Score concentration (are top scores significantly higher?)
        # High RRF scores indicate chunks appeared in multiple retriever lists
        scores = [chunk.score for chunk in chunks[:min(10, len(chunks))]]
        top_score = scores[0]
        avg_score = sum(scores) / len(scores)

        # If top score is much higher than average, retrieval is confident
        # Typical RRF: top ~0.016, avg ~0.013 → ratio ~1.23
        # Strong retrieval: top ~0.030, avg ~0.016 → ratio ~1.88
        score_ratio = top_score / avg_score if avg_score > 0 else 1.0
        concentration_factor = min(1.0, (score_ratio - 1.0) / 1.0)  # Normalize around ratio=1-2

        # Combine factors with weights
        base_confidence = (
            diversity_factor * 0.5 +  # Document focus is most important
            coverage_factor * 0.3 +   # Supporting evidence matters
            concentration_factor * 0.2  # Score distribution is a weak signal
        )

        # Map to confidence bands
        if base_confidence >= 0.85:
            # High confidence: single document, many chunks, strong scores
            confidence = 0.75 + (base_confidence - 0.85) * 1.33  # Maps 0.85-1.0 → 0.75-0.95
        elif base_confidence >= 0.65:
            # Medium-high confidence
            confidence = 0.50 + (base_confidence - 0.65) * 1.25  # Maps 0.65-0.85 → 0.50-0.75
        elif base_confidence >= 0.45:
            # Medium-low confidence
            confidence = 0.25 + (base_confidence - 0.45) * 1.25  # Maps 0.45-0.65 → 0.25-0.50
        else:
            # Low confidence: scattered retrieval or weak evidence
            confidence = base_confidence * 0.55  # Maps 0.0-0.45 → 0.0-0.25

        # Apply absolute quality cap (prevents high confidence on weak retrieval)
        confidence = min(confidence, max_confidence_cap)

        return max(0.0, min(1.0, confidence))
