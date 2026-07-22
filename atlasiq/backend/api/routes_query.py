"""Query API routes for AtlasIQ.

Provides the primary query endpoint (``POST /query``). Routes delegate
orchestration to the injected :class:`QueryPipeline` — they contain no
business logic of their own.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from atlasiq.backend.core.dependencies import get_query_pipeline

if TYPE_CHECKING:
    from atlasiq.retrieval.qa_pipeline import QueryPipeline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


class QueryRequest(BaseModel):
    """Request model for the query endpoint."""

    question: str = Field(
        ...,
        description="The natural-language question to ask.",
        examples=["What is AtlasIQ?"],
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Ensure the question is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace-only")
        return v.strip()


class CitationModel(BaseModel):
    """Citation response model."""

    document_name: str = Field(..., description="The name of the source document.")
    page: str = Field(..., description="The page number or page range.")
    quote: str = Field(..., description="The quoted passage from the document.")
    chunk_index: int = Field(..., description="Zero-based chunk index within the document.")
    score: float = Field(..., description="Retrieval relevance score (RRF or final score).")


class QueryAPIResponse(BaseModel):
    """Response model for the query endpoint."""

    answer: str = Field(..., description="The generated answer or refusal message.")
    citations: list[CitationModel] = Field(
        ..., description="The list of supporting citations."
    )
    confidence: float = Field(
        ..., description="Normalised confidence score (0.0 to 1.0)."
    )
    sources: list[str] = Field(
        ..., description="List of unique source document names cited."
    )
    refusal_reason: str | None = Field(
        None, description="Optional reason for refusal if guardrails rejected the query."
    )


@router.post("/query", response_model=QueryAPIResponse)
async def query_question(
    request: QueryRequest,
    pipeline: QueryPipeline = Depends(get_query_pipeline),
) -> QueryAPIResponse:
    """Submit a natural-language query to get an answer."""
    logger.info("Received query request")
    logger.debug("Received query request (%d characters)", len(request.question))
    response = await pipeline.answer(request.question)

    unique_sources = list(dict.fromkeys(c.document_name for c in response.citations))

    return QueryAPIResponse(
        answer=response.answer,
        citations=[
            CitationModel(
                document_name=c.document_name,
                page=c.page,
                quote=c.quote,
                chunk_index=c.chunk_index,
                score=c.score,
            )
            for c in response.citations
        ],
        confidence=response.confidence_score,
        sources=unique_sources,
        refusal_reason=response.refusal_reason,
    )
