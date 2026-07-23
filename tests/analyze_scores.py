"""Analyze retrieval scores to understand why irrelevant docs appear."""
import requests

resp = requests.post(
    "http://localhost:8000/query",
    json={"question": "What is this audit engagement letter about?"}
)

if resp.status_code == 200:
    data = resp.json()
    
    print("=== CITATION ANALYSIS ===\n")
    
    for i, citation in enumerate(data['citations'], 1):
        print(f"{i}. {citation['document_name']}")
        print(f"   Page: {citation.get('page', 'N/A')}")
        print(f"   Chunk Index: {citation.get('chunk_index', 'N/A')}")
        print(f"   RRF Score: {citation.get('score', 'N/A')}")
        print(f"   Content preview: {citation.get('content', '')[:150]}...")
        print()
    
    print("\n=== ANALYSIS ===")
    print(f"Total citations: {len(data['citations'])}")
    
    # Check for cross-contamination
    audit_citations = [c for c in data['citations'] if 'Audit' in c['document_name']]
    other_citations = [c for c in data['citations'] if 'Audit' not in c['document_name']]
    
    print(f"Audit letter citations: {len(audit_citations)}")
    print(f"Other document citations: {len(other_citations)}")
    
    if other_citations:
        print("\n⚠️  PROBLEM IDENTIFIED:")
        print(f"   {len(other_citations)} citations from irrelevant documents")
        print("   These chunks scored high enough to pass the 0.011 threshold")
        print("   but are NOT relevant to the audit letter question.")
        
        # Show the irrelevant chunk content
        for c in other_citations:
            print(f"\n   Irrelevant chunk from {c['document_name']}:")
            print(f"   Score: {c.get('score', 'N/A')}")
            print(f"   Content: {c.get('content', '')[:200]}...")
else:
    print(f"Error: {resp.status_code} - {resp.text}")
