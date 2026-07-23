"""Direct diagnostic test - traces retrieval pipeline step by step."""
import asyncio
import logging
from atlasiq.backend.core.config import Settings
from atlasiq.backend.core.dependencies import (
    get_dense_retriever,
    get_bm25_retriever,
    get_hybrid_retriever,
    get_document_repository,
)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s [%(name)s] %(message)s'
)

async def diagnose():
    """Run diagnostic analysis of retrieval for audit letter query."""
    question = "What is this audit engagement letter about?"
    
    print("\n" + "="*80)
    print("RETRIEVAL PIPELINE DIAGNOSTIC")
    print("="*80)
    print(f"\nQuery: '{question}'")
    print("\n" + "-"*80)
    
    settings = Settings()
    
    # Step 1: Dense Retriever
    print("\nSTEP 1: DENSE RETRIEVER")
    print("-"*80)
    dense = get_dense_retriever()  # Not async
    dense_results = dense.retrieve(question)
    print(f"Dense retriever returned {len(dense_results)} chunks")
    
    print("\nTop 10 Dense Results:")
    for i, ref in enumerate(dense_results[:10], 1):
        print(f"  {i}. chunk_id={ref.chunk_id[:8]}..., doc_id={ref.document_id[:8]}..., "
              f"chunk_idx={ref.chunk_index}, score={ref.score:.6f}")
    
    # Step 2: BM25 Retriever
    print("\n" + "-"*80)
    print("STEP 2: BM25 RETRIEVER")
    print("-"*80)
    bm25 = await get_bm25_retriever()  # This is async
    bm25_results = bm25.retrieve(question)
    print(f"BM25 retriever returned {len(bm25_results)} chunks")
    
    print("\nTop 10 BM25 Results:")
    for i, ref in enumerate(bm25_results[:10], 1):
        print(f"  {i}. chunk_id={ref.chunk_id[:8]}..., doc_id={ref.document_id[:8]}..., "
              f"chunk_idx={ref.chunk_index}, score={ref.score:.6f}")
    
    # Step 3: Hybrid (RRF) Fusion
    print("\n" + "-"*80)
    print("STEP 3: HYBRID (RRF) FUSION")
    print("-"*80)
    hybrid = await get_hybrid_retriever()  # This is async
    hybrid_results = hybrid.retrieve(question)
    print(f"Hybrid retriever returned {len(hybrid_results)} chunks after RRF fusion")
    
    print("\nTop 10 Hybrid (RRF) Results:")
    for i, ref in enumerate(hybrid_results[:10], 1):
        print(f"  {i}. chunk_id={ref.chunk_id[:8]}..., doc_id={ref.document_id[:8]}..., "
              f"chunk_idx={ref.chunk_index}, rrf_score={ref.score:.6f}")
    
    # Step 4: Hydrate chunks to see document names
    print("\n" + "-"*80)
    print("STEP 4: HYDRATE CHUNKS (Get Document Names)")
    print("-"*80)
    repo = get_document_repository()
    
    chunk_ids = [ref.chunk_id for ref in hybrid_results[:10]]
    chunk_records = await repo.get_chunks_by_ids(chunk_ids)
    chunk_by_id = {record.id: record for record in chunk_records}
    
    unique_document_ids = {ref.document_id for ref in hybrid_results[:10]}
    document_map = {}
    for doc_id in unique_document_ids:
        doc_record = await repo.get_document_by_id(doc_id)
        if doc_record:
            document_map[doc_id] = doc_record.filename
    
    print("\nTop 10 Hydrated Chunks:")
    for i, ref in enumerate(hybrid_results[:10], 1):
        if ref.chunk_id in chunk_by_id:
            chunk = chunk_by_id[ref.chunk_id]
            filename = document_map.get(ref.document_id, "unknown")
            content_preview = chunk.content[:100].replace('\n', ' ')
            print(f"\n  {i}. FILE: {filename}")
            print(f"     RRF Score: {ref.score:.6f}")
            print(f"     Chunk Index: {chunk.chunk_index}")
            print(f"     Content: {content_preview}...")
    
    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    # Count documents in top 10
    doc_counts = {}
    for i, ref in enumerate(hybrid_results[:10], 1):
        filename = document_map.get(ref.document_id, "unknown")
        doc_counts[filename] = doc_counts.get(filename, 0) + 1
    
    print("\nDocument Distribution in Top 10:")
    for filename, count in sorted(doc_counts.items(), key=lambda x: -x[1]):
        print(f"  {filename}: {count} chunks")
    
    # Check for AtlasIQ guide
    if "AtlasIQ_Project_Guide.pdf" in doc_counts:
        print("\n⚠️  PROBLEM IDENTIFIED:")
        print(f"   AtlasIQ_Project_Guide.pdf has {doc_counts['AtlasIQ_Project_Guide.pdf']} chunks in top 10")
        print("   This should NOT match an audit letter query")
        
        # Find where it ranks
        for i, ref in enumerate(hybrid_results[:10], 1):
            filename = document_map.get(ref.document_id, "unknown")
            if filename == "AtlasIQ_Project_Guide.pdf":
                print(f"\n   RANK #{i}: AtlasIQ guide chunk")
                print(f"   RRF Score: {ref.score:.6f}")
                if ref.chunk_id in chunk_by_id:
                    chunk = chunk_by_id[ref.chunk_id]
                    print(f"   Content: {chunk.content[:200]}...")
    else:
        print("\n✅ No AtlasIQ guide in top 10 - issue may be resolved!")
    
    await repo.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
