"""Unit tests for the query answering pipeline (M2-11).

All tests are offline — every collaborator is mocked.

Coverage:
- QueryResponse dataclass structure
- Successful query (full pipeline flow)
- Empty retrieval results (no chunks found)
- Guardrail refusal (weak evidence)
- Guardrail refusal (no retrieval results)
- Component call order verification (strict ordering)
- Empty/whitespace question handling
- Citation attachment on pass
- Citation exclusion on refusal
- Confidence score propagation
- Error propagation (RetrievalError, LLMProviderError, DatabaseQueryError)
- Hydration edge cases (missing chunks, missing documents, multi-document)
- Pipeline does not call generator/prompt on empty retrieval
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from atlasiq.backend.core.exceptions import (
    DatabaseQueryError,
    LLMProviderError,
    RetrievalError,
)
from atlasiq.backend.domain.chunk import ChunkRecord
from atlasiq.backend.domain.document import DocumentRecord, DocumentStatus
from atlasiq.retrieval.citations import Citation
from atlasiq.retrieval.guardrails import GuardrailDecision
from atlasiq.retrieval.models import ScoredChunkRef
from atlasiq.retrieval.prompt_builder import BuiltPrompt
from atlasiq.retrieval.qa_pipeline import QueryPipeline, QueryResponse

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_hybrid_retriever() -> MagicMock:
    """Mock hybrid retriever."""
    retriever = MagicMock()
    retriever.retrieve.return_value = [
        ScoredChunkRef(
            chunk_id="chunk-1",
            document_id="doc-1",
            chunk_index=0,
            score=0.9,
        ),
    ]
    return retriever


@pytest.fixture()
def mock_document_repo() -> MagicMock:
    """Mock document repository."""
    repo = MagicMock()
    repo.get_chunks_by_ids = AsyncMock(
        return_value=[
            ChunkRecord(
                id="chunk-1",
                document_id="doc-1",
                chunk_index=0,
                content="Chunk content.",
                start_page=5,
            ),
        ]
    )
    repo.get_document_by_id = AsyncMock(
        return_value=DocumentRecord(
            id="doc-1",
            filename="document.pdf",
            file_hash="hash123",
            file_type=".pdf",
            file_size_bytes=1024,
            status=DocumentStatus.COMPLETED,
        )
    )
    return repo


@pytest.fixture()
def mock_prompt_builder() -> MagicMock:
    """Mock prompt builder."""
    builder = MagicMock()
    builder.build.return_value = BuiltPrompt(
        system_prompt="System prompt.",
        user_prompt="User prompt.",
    )
    return builder


@pytest.fixture()
def mock_answer_generator() -> MagicMock:
    """Mock answer generator."""
    generator = MagicMock()
    generator.generate.return_value = "Generated answer."
    return generator


@pytest.fixture()
def mock_citation_builder() -> MagicMock:
    """Mock citation builder."""
    builder = MagicMock()
    builder.build.return_value = [
        Citation(document_name="document.pdf", page="5", quote="Chunk content.")
    ]
    return builder


@pytest.fixture()
def mock_guardrails() -> MagicMock:
    """Mock guardrails (default: pass decision)."""
    guardrails = MagicMock()
    guardrails.check.return_value = GuardrailDecision(
        passed=True,
        answer="Generated answer.",
        citations=[
            Citation(document_name="document.pdf", page="5", quote="Chunk content.")
        ],
        confidence_score=0.9,
        refusal_reason=None,
    )
    return guardrails


@pytest.fixture()
def pipeline(
    mock_hybrid_retriever: MagicMock,
    mock_document_repo: MagicMock,
    mock_prompt_builder: MagicMock,
    mock_answer_generator: MagicMock,
    mock_citation_builder: MagicMock,
    mock_guardrails: MagicMock,
) -> QueryPipeline:
    """Query pipeline with all collaborators mocked."""
    return QueryPipeline(
        hybrid_retriever=mock_hybrid_retriever,
        document_repo=mock_document_repo,
        prompt_builder=mock_prompt_builder,
        answer_generator=mock_answer_generator,
        citation_builder=mock_citation_builder,
        guardrails=mock_guardrails,
    )


# ── QueryResponse Dataclass ──────────────────────────────────────────────────


class TestQueryResponseDataclass:
    """Tests for the :class:`QueryResponse` value object."""

    def test_fields(self) -> None:
        """QueryResponse has all required fields."""
        response = QueryResponse(
            answer="Answer text.",
            citations=[Citation("doc.pdf", "1", "Quote.")],
            confidence_score=0.85,
            refusal_reason=None,
        )
        assert response.answer == "Answer text."
        assert len(response.citations) == 1
        assert response.confidence_score == 0.85
        assert response.refusal_reason is None

    def test_frozen_immutability(self) -> None:
        """QueryResponse is frozen (fields cannot be mutated)."""
        response = QueryResponse(
            answer="Answer", citations=[], confidence_score=0.9
        )
        with pytest.raises(AttributeError):
            response.answer = "New answer"  # type: ignore[misc]

    def test_refusal_reason_optional(self) -> None:
        """refusal_reason is optional (defaults to None)."""
        response = QueryResponse(
            answer="Answer", citations=[], confidence_score=0.8
        )
        assert response.refusal_reason is None


# ── Successful Query ─────────────────────────────────────────────────────────


class TestSuccessfulQuery:
    """Tests for successful query (full pipeline flow)."""

    @pytest.mark.asyncio()
    async def test_returns_generated_answer(self, pipeline: QueryPipeline) -> None:
        """Successful query returns the generated answer."""
        response = await pipeline.answer("What is AtlasIQ?")

        assert response.answer == "Generated answer."
        assert response.refusal_reason is None

    @pytest.mark.asyncio()
    async def test_includes_citations(self, pipeline: QueryPipeline) -> None:
        """Citations are included in successful response."""
        response = await pipeline.answer("What is AtlasIQ?")

        assert len(response.citations) == 1
        assert response.citations[0].document_name == "document.pdf"

    @pytest.mark.asyncio()
    async def test_includes_confidence_score(self, pipeline: QueryPipeline) -> None:
        """Confidence score is included in response."""
        response = await pipeline.answer("What is AtlasIQ?")

        assert response.confidence_score == 0.9

    @pytest.mark.asyncio()
    async def test_component_call_order(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
        mock_document_repo: MagicMock,
        mock_prompt_builder: MagicMock,
        mock_answer_generator: MagicMock,
        mock_citation_builder: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Components are called in the correct order."""
        await pipeline.answer("What is AtlasIQ?")

        # Verify retriever called
        mock_hybrid_retriever.retrieve.assert_called_once_with("What is AtlasIQ?")

        # Verify repository calls for hydration
        mock_document_repo.get_chunks_by_ids.assert_called_once_with(["chunk-1"])
        mock_document_repo.get_document_by_id.assert_called_once_with("doc-1")

        # Verify prompt builder called with question and hydrated chunks
        mock_prompt_builder.build.assert_called_once()
        call_args = mock_prompt_builder.build.call_args
        assert call_args[0][0] == "What is AtlasIQ?"
        assert len(call_args[0][1]) == 1  # Retrieved chunks

        # Verify generator called with built prompt
        mock_answer_generator.generate.assert_called_once()

        # Verify citation builder called with chunks
        mock_citation_builder.build.assert_called_once()

        # Verify guardrails called last
        mock_guardrails.check.assert_called_once()


# ── Empty Retrieval ──────────────────────────────────────────────────────────


class TestEmptyRetrieval:
    """Tests for queries with no retrieval results."""

    @pytest.mark.asyncio()
    async def test_no_chunks_retrieved(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Pipeline handles empty retrieval results."""
        # Configure retriever to return no results
        mock_hybrid_retriever.retrieve.return_value = []

        # Configure guardrails to refuse on empty retrieval
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=False,
            answer="I don't have enough information to answer this question based on the available documents.",
            citations=[],
            confidence_score=0.0,
            refusal_reason="no_retrieval_results",
        )

        response = await pipeline.answer("Unknown topic?")

        assert response.refusal_reason == "no_retrieval_results"
        assert response.confidence_score == 0.0
        assert response.citations == []

    @pytest.mark.asyncio()
    async def test_guardrails_receives_empty_chunks(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Guardrails receives empty chunk list when nothing retrieved."""
        mock_hybrid_retriever.retrieve.return_value = []
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=False,
            answer="Refusal message.",
            citations=[],
            confidence_score=0.0,
            refusal_reason="no_retrieval_results",
        )

        await pipeline.answer("Unknown?")

        # Verify guardrails called with empty chunks
        call_args = mock_guardrails.check.call_args
        assert len(call_args[0][1]) == 0  # Empty chunks list


# ── Guardrail Refusal ────────────────────────────────────────────────────────


class TestGuardrailRefusal:
    """Tests for guardrail refusal scenarios."""

    @pytest.mark.asyncio()
    async def test_weak_evidence_refusal(
        self,
        pipeline: QueryPipeline,
        mock_guardrails: MagicMock,
    ) -> None:
        """Guardrail refuses when evidence is weak."""
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=False,
            answer="I don't have enough information to answer this question based on the available documents.",
            citations=[],
            confidence_score=0.3,
            refusal_reason="weak_evidence",
        )

        response = await pipeline.answer("Vague question?")

        assert response.refusal_reason == "weak_evidence"
        assert "I don't have enough information" in response.answer
        assert response.citations == []

    @pytest.mark.asyncio()
    async def test_refusal_discards_generated_answer(
        self,
        pipeline: QueryPipeline,
        mock_answer_generator: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Generated answer is discarded when guardrail refuses."""
        mock_answer_generator.generate.return_value = "Wrong answer."
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=False,
            answer="Refusal message.",
            citations=[],
            confidence_score=0.2,
            refusal_reason="weak_evidence",
        )

        response = await pipeline.answer("Question?")

        assert "Wrong answer" not in response.answer
        assert response.answer == "Refusal message."

    @pytest.mark.asyncio()
    async def test_refusal_excludes_citations(
        self,
        pipeline: QueryPipeline,
        mock_guardrails: MagicMock,
    ) -> None:
        """Citations are excluded when guardrail refuses."""
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=False,
            answer="Refusal message.",
            citations=[],
            confidence_score=0.4,
            refusal_reason="weak_evidence",
        )

        response = await pipeline.answer("Question?")

        assert response.citations == []


# ── Input Validation ─────────────────────────────────────────────────────────


class TestInputValidation:
    """Tests for question input validation."""

    @pytest.mark.asyncio()
    async def test_empty_question_raises(self, pipeline: QueryPipeline) -> None:
        """Empty question raises ValueError."""
        with pytest.raises(ValueError, match="Question cannot be empty"):
            await pipeline.answer("")

    @pytest.mark.asyncio()
    async def test_whitespace_only_question_raises(
        self, pipeline: QueryPipeline
    ) -> None:
        """Whitespace-only question raises ValueError."""
        with pytest.raises(ValueError, match="Question cannot be empty"):
            await pipeline.answer("   \n  ")

    @pytest.mark.asyncio()
    async def test_question_normalized(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
    ) -> None:
        """Question is stripped of leading/trailing whitespace."""
        await pipeline.answer("  What is AtlasIQ?  \n")

        # Verify retriever received normalized question
        mock_hybrid_retriever.retrieve.assert_called_once_with("What is AtlasIQ?")


# ── Hydration ────────────────────────────────────────────────────────────────


class TestHydration:
    """Tests for chunk hydration from PostgreSQL."""

    @pytest.mark.asyncio()
    async def test_fetches_chunks_by_ids(
        self,
        pipeline: QueryPipeline,
        mock_document_repo: MagicMock,
    ) -> None:
        """Chunks are fetched by their IDs."""
        await pipeline.answer("Question?")

        mock_document_repo.get_chunks_by_ids.assert_called_once_with(["chunk-1"])

    @pytest.mark.asyncio()
    async def test_fetches_document_metadata(
        self,
        pipeline: QueryPipeline,
        mock_document_repo: MagicMock,
    ) -> None:
        """Document metadata (filename) is fetched for citations."""
        await pipeline.answer("Question?")

        mock_document_repo.get_document_by_id.assert_called_once_with("doc-1")

    @pytest.mark.asyncio()
    async def test_preserves_retrieval_scores(
        self,
        pipeline: QueryPipeline,
        mock_prompt_builder: MagicMock,
    ) -> None:
        """Retrieval scores are preserved through hydration."""
        await pipeline.answer("Question?")

        # Verify chunks passed to prompt builder have correct scores
        call_args = mock_prompt_builder.build.call_args
        retrieved_chunks = call_args[0][1]
        assert len(retrieved_chunks) == 1
        assert retrieved_chunks[0].score == 0.9

    @pytest.mark.asyncio()
    async def test_handles_missing_document(
        self,
        pipeline: QueryPipeline,
        mock_document_repo: MagicMock,
        mock_prompt_builder: MagicMock,
    ) -> None:
        """Missing document results in fallback filename."""
        mock_document_repo.get_document_by_id = AsyncMock(return_value=None)

        await pipeline.answer("Question?")

        # Verify fallback filename used
        call_args = mock_prompt_builder.build.call_args
        retrieved_chunks = call_args[0][1]
        assert "unknown_" in retrieved_chunks[0].filename


# ── Realistic Scenarios ──────────────────────────────────────────────────────


class TestRealisticScenarios:
    """End-to-end scenarios resembling real queries."""

    @pytest.mark.asyncio()
    async def test_successful_query_with_multiple_chunks(
        self,
        mock_hybrid_retriever: MagicMock,
        mock_document_repo: MagicMock,
        mock_prompt_builder: MagicMock,
        mock_answer_generator: MagicMock,
        mock_citation_builder: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Successful query with multiple chunks from different documents."""
        # Configure retriever with multiple results
        mock_hybrid_retriever.retrieve.return_value = [
            ScoredChunkRef("chunk-1", "doc-1", 0, 0.95),
            ScoredChunkRef("chunk-2", "doc-2", 0, 0.82),
        ]

        # Configure repo responses
        mock_document_repo.get_chunks_by_ids = AsyncMock(
            return_value=[
                ChunkRecord("chunk-1", "doc-1", 0, "First chunk.", start_page=5),
                ChunkRecord("chunk-2", "doc-2", 0, "Second chunk.", start_page=12),
            ]
        )

        async def get_doc(doc_id: str) -> DocumentRecord:
            docs = {
                "doc-1": DocumentRecord(
                    "doc-1", "report.pdf", "h1", ".pdf", 1024, DocumentStatus.COMPLETED
                ),
                "doc-2": DocumentRecord(
                    "doc-2", "guide.pdf", "h2", ".pdf", 2048, DocumentStatus.COMPLETED
                ),
            }
            return docs[doc_id]

        mock_document_repo.get_document_by_id = AsyncMock(side_effect=get_doc)

        # Configure citation builder
        mock_citation_builder.build.return_value = [
            Citation("report.pdf", "5", "First chunk."),
            Citation("guide.pdf", "12", "Second chunk."),
        ]

        # Configure guardrails to pass
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=True,
            answer="Based on the documents...",
            citations=[
                Citation("report.pdf", "5", "First chunk."),
                Citation("guide.pdf", "12", "Second chunk."),
            ],
            confidence_score=0.95,
            refusal_reason=None,
        )

        pipeline = QueryPipeline(
            mock_hybrid_retriever,
            mock_document_repo,
            mock_prompt_builder,
            mock_answer_generator,
            mock_citation_builder,
            mock_guardrails,
        )

        response = await pipeline.answer("Complex question?")

        assert response.answer == "Based on the documents..."
        assert len(response.citations) == 2
        assert response.confidence_score == 0.95
        assert response.refusal_reason is None


# ── Error Propagation ────────────────────────────────────────────────────────


class TestErrorPropagation:
    """Pipeline lets domain errors propagate without swallowing them."""

    @pytest.mark.asyncio()
    async def test_retrieval_error_propagates(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
    ) -> None:
        """RetrievalError from the hybrid retriever propagates unchanged."""
        mock_hybrid_retriever.retrieve.side_effect = RetrievalError(
            "Qdrant connection failed"
        )

        with pytest.raises(RetrievalError, match="Qdrant connection failed"):
            await pipeline.answer("Question?")

    @pytest.mark.asyncio()
    async def test_llm_error_propagates(
        self,
        pipeline: QueryPipeline,
        mock_answer_generator: MagicMock,
    ) -> None:
        """LLMProviderError from the generator propagates unchanged."""
        mock_answer_generator.generate.side_effect = LLMProviderError(
            "LLM timeout"
        )

        with pytest.raises(LLMProviderError, match="LLM timeout"):
            await pipeline.answer("Question?")

    @pytest.mark.asyncio()
    async def test_database_error_from_hydration_propagates(
        self,
        pipeline: QueryPipeline,
        mock_document_repo: MagicMock,
    ) -> None:
        """DatabaseQueryError during chunk hydration propagates unchanged."""
        mock_document_repo.get_chunks_by_ids = AsyncMock(
            side_effect=DatabaseQueryError("PostgreSQL read failed")
        )

        with pytest.raises(DatabaseQueryError, match="PostgreSQL read failed"):
            await pipeline.answer("Question?")

    @pytest.mark.asyncio()
    async def test_database_error_from_document_fetch_propagates(
        self,
        pipeline: QueryPipeline,
        mock_document_repo: MagicMock,
    ) -> None:
        """DatabaseQueryError during document metadata fetch propagates."""
        mock_document_repo.get_document_by_id = AsyncMock(
            side_effect=DatabaseQueryError("Document lookup failed")
        )

        with pytest.raises(DatabaseQueryError, match="Document lookup failed"):
            await pipeline.answer("Question?")

    @pytest.mark.asyncio()
    async def test_retrieval_error_prevents_generation(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
        mock_answer_generator: MagicMock,
    ) -> None:
        """A retrieval failure prevents any LLM call (fail early)."""
        mock_hybrid_retriever.retrieve.side_effect = RetrievalError("Failed")

        with pytest.raises(RetrievalError):
            await pipeline.answer("Question?")

        mock_answer_generator.generate.assert_not_called()

    @pytest.mark.asyncio()
    async def test_hydration_error_prevents_generation(
        self,
        pipeline: QueryPipeline,
        mock_document_repo: MagicMock,
        mock_answer_generator: MagicMock,
    ) -> None:
        """A hydration failure prevents any LLM call (fail early)."""
        mock_document_repo.get_chunks_by_ids = AsyncMock(
            side_effect=DatabaseQueryError("Hydration failed")
        )

        with pytest.raises(DatabaseQueryError):
            await pipeline.answer("Question?")

        mock_answer_generator.generate.assert_not_called()


# ── Strict Call Ordering ─────────────────────────────────────────────────────


class TestStrictCallOrdering:
    """Verifies the exact call sequence documented in EXECUTION_PLAN_M2.md."""

    @pytest.mark.asyncio()
    async def test_retrieve_before_hydrate(
        self,
        mock_hybrid_retriever: MagicMock,
        mock_document_repo: MagicMock,
        mock_prompt_builder: MagicMock,
        mock_answer_generator: MagicMock,
        mock_citation_builder: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Components are called in documented order: retrieve → hydrate → prompt → generate → cite → guard."""
        order: list[str] = []

        def _record_retrieve(*_a: object, **_k: object) -> list[ScoredChunkRef]:
            order.append("retrieve")
            return [ScoredChunkRef("c1", "d1", 0, 0.9)]

        async def _record_get_chunks(*_a: object, **_k: object) -> list[ChunkRecord]:
            order.append("hydrate_chunks")
            return [ChunkRecord("c1", "d1", 0, "Text.", start_page=1)]

        async def _record_get_doc(*_a: object, **_k: object) -> DocumentRecord:
            order.append("hydrate_doc")
            return DocumentRecord("d1", "f.pdf", "h", ".pdf", 100, DocumentStatus.COMPLETED)

        def _record_prompt(*_a: object, **_k: object) -> BuiltPrompt:
            order.append("prompt")
            return BuiltPrompt("sys", "usr")

        def _record_generate(*_a: object, **_k: object) -> str:
            order.append("generate")
            return "Answer"

        def _record_cite(*_a: object, **_k: object) -> list[Citation]:
            order.append("cite")
            return [Citation("f.pdf", "1", "Text.")]

        def _record_guard(*_a: object, **_k: object) -> GuardrailDecision:
            order.append("guard")
            return GuardrailDecision(True, "Answer", [Citation("f.pdf", "1", "Text.")], 0.9)

        mock_hybrid_retriever.retrieve.side_effect = _record_retrieve
        mock_document_repo.get_chunks_by_ids = AsyncMock(side_effect=_record_get_chunks)
        mock_document_repo.get_document_by_id = AsyncMock(side_effect=_record_get_doc)
        mock_prompt_builder.build.side_effect = _record_prompt
        mock_answer_generator.generate.side_effect = _record_generate
        mock_citation_builder.build.side_effect = _record_cite
        mock_guardrails.check.side_effect = _record_guard

        pipeline = QueryPipeline(
            mock_hybrid_retriever,
            mock_document_repo,
            mock_prompt_builder,
            mock_answer_generator,
            mock_citation_builder,
            mock_guardrails,
        )

        await pipeline.answer("Q?")

        # Verify strict ordering
        assert order.index("retrieve") < order.index("hydrate_chunks")
        assert order.index("hydrate_chunks") < order.index("prompt")
        assert order.index("prompt") < order.index("generate")
        assert order.index("generate") < order.index("cite")
        assert order.index("cite") < order.index("guard")


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.asyncio()
    async def test_empty_retrieval_still_calls_guardrails(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Even with zero chunks, guardrails are called to produce a refusal."""
        mock_hybrid_retriever.retrieve.return_value = []
        mock_guardrails.check.return_value = GuardrailDecision(
            passed=False,
            answer="Refusal.",
            citations=[],
            confidence_score=0.0,
            refusal_reason="no_retrieval_results",
        )

        response = await pipeline.answer("Q?")

        mock_guardrails.check.assert_called_once()
        assert response.refusal_reason == "no_retrieval_results"

    @pytest.mark.asyncio()
    async def test_chunk_missing_from_db_is_silently_dropped(
        self,
        pipeline: QueryPipeline,
        mock_hybrid_retriever: MagicMock,
        mock_document_repo: MagicMock,
        mock_prompt_builder: MagicMock,
    ) -> None:
        """Chunk ids returned by retriever but absent from DB are dropped."""
        # Retriever returns two refs, but DB only has one
        mock_hybrid_retriever.retrieve.return_value = [
            ScoredChunkRef("c1", "d1", 0, 0.9),
            ScoredChunkRef("c2", "d1", 1, 0.7),
        ]
        mock_document_repo.get_chunks_by_ids = AsyncMock(
            return_value=[
                ChunkRecord("c1", "d1", 0, "First chunk.", start_page=1),
                # c2 is missing — DB didn't find it
            ]
        )

        await pipeline.answer("Q?")

        # Only 1 retrieved chunk passed to prompt builder (c2 dropped)
        call_args = mock_prompt_builder.build.call_args
        chunks = call_args[0][1]
        assert len(chunks) == 1
        assert chunks[0].chunk.id == "c1"

    @pytest.mark.asyncio()
    async def test_multiple_chunks_same_document(
        self,
        mock_hybrid_retriever: MagicMock,
        mock_document_repo: MagicMock,
        mock_prompt_builder: MagicMock,
        mock_answer_generator: MagicMock,
        mock_citation_builder: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Multiple chunks from the same document fetch the doc only once."""
        # Two chunks from the same document
        mock_hybrid_retriever.retrieve.return_value = [
            ScoredChunkRef("c1", "d1", 0, 0.9),
            ScoredChunkRef("c2", "d1", 1, 0.7),
        ]
        mock_document_repo.get_chunks_by_ids = AsyncMock(
            return_value=[
                ChunkRecord("c1", "d1", 0, "Chunk A", start_page=1),
                ChunkRecord("c2", "d1", 1, "Chunk B", start_page=2),
            ]
        )
        mock_document_repo.get_document_by_id = AsyncMock(
            return_value=DocumentRecord(
                "d1", "report.pdf", "h", ".pdf", 1024, DocumentStatus.COMPLETED
            )
        )
        mock_guardrails.check.return_value = GuardrailDecision(
            True, "Answer", [], 0.9
        )

        pipeline = QueryPipeline(
            mock_hybrid_retriever,
            mock_document_repo,
            mock_prompt_builder,
            mock_answer_generator,
            mock_citation_builder,
            mock_guardrails,
        )

        await pipeline.answer("Q?")

        # Document fetched only once despite two chunks from it
        mock_document_repo.get_document_by_id.assert_called_once_with("d1")

        # Both chunks passed to prompt builder
        call_args = mock_prompt_builder.build.call_args
        chunks = call_args[0][1]
        assert len(chunks) == 2

    @pytest.mark.asyncio()
    async def test_response_is_frozen(self, pipeline: QueryPipeline) -> None:
        """QueryResponse returned from the pipeline is immutable."""
        response = await pipeline.answer("Q?")

        with pytest.raises(AttributeError):
            response.answer = "tampered"  # type: ignore[misc]

    @pytest.mark.asyncio()
    async def test_guardrail_arguments_match_generated_values(
        self,
        pipeline: QueryPipeline,
        mock_answer_generator: MagicMock,
        mock_citation_builder: MagicMock,
        mock_guardrails: MagicMock,
    ) -> None:
        """Guardrails receive the exact answer and citations produced by the generator and citation builder."""
        mock_answer_generator.generate.return_value = "Specific answer text"
        specific_citations = [Citation("f.pdf", "1", "Quote")]
        mock_citation_builder.build.return_value = specific_citations

        await pipeline.answer("Q?")

        guard_args = mock_guardrails.check.call_args
        assert guard_args[0][0] == "Specific answer text"
        assert guard_args[0][2] is specific_citations
