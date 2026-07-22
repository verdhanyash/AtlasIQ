# Citation Format Fix Summary

## Problem
The LLM was including inline citations in the answer text like:
```
[Source: AtlasIQ_Project_Guide.pdf, Page: 2]
```

This made the answer text cluttered and hard to read.

## Root Cause
**Two prompt templates** were instructing the LLM to add citations:

1. **`prompts/system_prompt.txt`** - Had: "Always cite your sources by referencing the document name and page number"
2. **`prompts/qa_prompt.txt`** - Had explicit citation formatting instructions:
   - "Cite the source document and page number for each claim"
   - "Format citations as [Source: document_name, Page: page_number]"

## Solution Applied

### Updated `prompts/system_prompt.txt`
```
CRITICAL INSTRUCTION - READ CAREFULLY:
You MUST NOT include ANY form of citations, source references, or attributions in your answer text.
Do NOT write things like "[Source: ...]", "[Document: ...]", "[Page: ...]", or any similar references.
The system will automatically add citations below your answer.
Your answer must be clean prose without any bracketed references.
```

### Updated `prompts/qa_prompt.txt`
```
Instructions:
- Answer using ONLY the information in the context above.
- If the context does not contain enough information, say "I don't have enough information to answer this question based on the available documents."
- Do NOT include any citations, source references, or page numbers in your answer. Write only the answer itself in clean prose.
- The system will automatically handle citations separately.
- Be concise and direct.
```

## Result
✅ **Answers are now clean without inline citations**

### Example Query: "How does the AtlasIQ ingestion pipeline work?"

**Clean Answer (no inline citations):**
> The AtlasIQ ingestion pipeline consists of six stages: a validator that rejects bad type/size data, a metadata + change detector using SHA-256 hash to decide if the document is new, modified, or unchanged, a parser utilizing Docling to convert PDF/DOCX documents into clean text (without OCR), a chunker which recursively splits the text into overlapping, size-bounded chunks, an embedder that uses nomic-embed-text-v1.5 to generate 768-dimensional vector representations of each chunk, and a store that saves the chunk text in PostgreSQL and vectors in Qdrant using a shared deterministic chunk ID for joining.

**Citations (shown separately below answer):**
- AtlasIQ_Project_Guide.pdf (Page N/A)

## Important Notes

1. **Prompt caching**: The `PromptBuilder` is cached with `@lru_cache(maxsize=1)` in `atlasiq/backend/core/dependencies.py`. This means prompt changes require a **full backend restart** (not just `--reload`).

2. **Both services running**:
   - Backend: http://localhost:8000 ✅
   - Frontend: http://localhost:8502 ✅

3. **Citation cards**: The UI displays citation information separately below the answer, so the answer text itself should be clean prose.

## Files Modified
- `prompts/system_prompt.txt`
- `prompts/qa_prompt.txt`

## Testing
Run `python test_ingestion_question.py` to verify the fix is working.
