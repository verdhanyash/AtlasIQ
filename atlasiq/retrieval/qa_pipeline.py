"""Query answering pipeline orchestrator.

Wires the retrieval, prompting, generation, citation, and guardrail components
into a single end-to-end question-answering flow. This module contains
**orchestration only**: it decides call order and manages the response lifecycle,
but performs no retrieval, prompting, generation, citation building, or evidence
gating of its own. Every collaborator is constructor-injected, so the pipeline is
trivially testable with mocks.

The pipeline follows the architecture documented in EXECUTION_PLAN_M2.md:
embed → hybrid retrieve → hydrate → prompt → generate → cite → guardrails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from atlasiq.retrieval.models import RetrievedChunk

if TYPE_CHECKING:
    from atlasiq.backend.repositories.document_repository import DocumentRepository
    from atlasiq.retrieval.citations import Citation, CitationBuilder
    from atlasiq.retrieval.generator import AnswerGenerator
    from atlasiq.retrieval.guardrails import Guardrails
    from atlasiq.retrieval.prompt_builder import PromptBuilder
    from atlasiq.retrieval.protocols import Retriever

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QueryResponse:
    """The final structured response from a query.

    Attributes:
        answer: The final answer (generated or refusal message).
        citations: Citations included with the answer (empty on refusal).
        confidence_score: Confidence derived from retrieval (0.0-1.0).
        refusal_reason: Optional reason for refusal (present when refused).
    """

    answer: str
    citations: list[Citation]
    confidence_score: float
    refusal_reason: str | None = None


class QueryPipeline:
    """Orchestrates the end-to-end question answering pipeline.

    Collaborators are injected; the pipeline constructs none of them. It calls
    them in a fixed order (retrieval → prompting → generation → citation →
    guardrails) and assembles the final response, delegating all real work to
    the injected components.
    """

    def __init__(
        self,
        hybrid_retriever: Retriever,
        document_repo: DocumentRepository,
        prompt_builder: PromptBuilder,
        answer_generator: AnswerGenerator,
        citation_builder: CitationBuilder,
        guardrails: Guardrails,
    ) -> None:
        """Initialise the pipeline with its collaborators.

        Args:
            hybrid_retriever: Retrieves ranked chunk references (dense + BM25 fusion).
            document_repo: PostgreSQL repository for hydrating chunk content.
            prompt_builder: Builds grounded prompts from question + chunks.
            answer_generator: Generates answers via LLM.
            citation_builder: Builds structured citations from chunks.
            guardrails: Evidence gating and confidence scoring.
        """
        self._hybrid_retriever = hybrid_retriever
        self._document_repo = document_repo
        self._prompt_builder = prompt_builder
        self._answer_generator = answer_generator
        self._citation_builder = citation_builder
        self._guardrails = guardrails

        logger.info("QueryPipeline initialised")

    async def answer(self, question: str) -> QueryResponse:
        """Answer a natural-language question using the full RAG pipeline.

        Orchestration flow:
        1. Retrieve ranked chunk references (hybrid: dense + BM25)
        2. Hydrate chunks (fetch content + metadata from PostgreSQL)
        3. Build grounded prompt (question + context)
        4. Generate answer (LLM)
        5. Build citations (from retrieved chunks)
        6. Apply guardrails (evidence gating + confidence)
        7. Return final response

        Args:
            question: The user's natural-language question.

        Returns:
            A :class:`QueryResponse` with the final answer (generated or
            refusal), citations, confidence score, and optional refusal reason.

        Raises:
            ValueError: If the question is empty or whitespace-only.
        """
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Question cannot be empty.")

        logger.info("Starting query pipeline for question: %s", normalized_question)

        # Step 1: Retrieve ranked chunk references
        scored_refs = self._hybrid_retriever.retrieve(normalized_question)
        logger.debug("Retrieved %d chunk references", len(scored_refs))

        # Step 2: Hydrate chunks (fetch content + metadata from PostgreSQL)
        chunk_ids = [ref.chunk_id for ref in scored_refs]
        chunk_records = await self._document_repo.get_chunks_by_ids(chunk_ids)

        # Build a lookup map to preserve retrieval ranking and scores
        # Also fetch unique document ids to get filenames
        chunk_by_id = {record.id: record for record in chunk_records}
        unique_document_ids = {ref.document_id for ref in scored_refs}

        # Fetch document records to get filenames
        document_map = {}
        for doc_id in unique_document_ids:
            doc_record = await self._document_repo.get_document_by_id(doc_id)
            if doc_record:
                document_map[doc_id] = doc_record.filename

        # Build RetrievedChunk objects with proper filenames
        retrieved_chunks = []
        for ref in scored_refs:
            if ref.chunk_id in chunk_by_id:
                chunk_record = chunk_by_id[ref.chunk_id]
                filename = document_map.get(ref.document_id, f"unknown_{ref.document_id}")
                retrieved_chunks.append(
                    RetrievedChunk(
                        chunk=chunk_record,
                        filename=filename,
                        score=ref.score,
                    )
                )

        logger.debug("Hydrated %d chunks from %d documents", len(retrieved_chunks), len(document_map))

        # Step 3: Build grounded prompt
        built_prompt = self._prompt_builder.build(normalized_question, retrieved_chunks)
        logger.debug("Built prompt with %d chunks in context", len(retrieved_chunks))

        # Step 4: Generate answer via LLM
        generated_answer = self._answer_generator.generate(built_prompt)
        logger.debug("Generated answer (%d chars)", len(generated_answer))

        # Step 5: Build citations from retrieved chunks
        citations = self._citation_builder.build(retrieved_chunks)
        logger.debug("Built %d citations", len(citations))

        # Step 6: Apply guardrails (evidence gating + confidence)
        decision = self._guardrails.check(generated_answer, retrieved_chunks, citations)
        logger.info(
            "Guardrail decision: passed=%s, confidence=%.2f",
            decision.passed,
            decision.confidence_score,
        )

        # Step 7: Assemble final response
        response = QueryResponse(
            answer=decision.answer,
            citations=decision.citations,
            confidence_score=decision.confidence_score,
            refusal_reason=decision.refusal_reason,
        )

        logger.info("Query pipeline completed successfully")
        return response
