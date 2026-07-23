"""Capture diagnostic logs for retrieval pipeline analysis."""
import requests
import time

print("Waiting for backend to be ready...")
time.sleep(2)

print("\n" + "="*80)
print("DIAGNOSTIC TEST: Audit Letter Query")
print("="*80)
print("\nQuery: 'What is this audit engagement letter about?'")
print("\nSending request...\n")

response = requests.post(
    "http://localhost:8000/query",
    json={"question": "What is this audit engagement letter about?"}
)

if response.status_code == 200:
    data = response.json()
    
    print("\n" + "="*80)
    print("RESPONSE SUMMARY")
    print("="*80)
    print(f"\nAnswer: {data['answer'][:200]}...")
    print(f"\nConfidence: {data['confidence']:.2%}")
    print(f"\nCitations ({len(data['citations'])} total):")
    for i, citation in enumerate(data['citations'], 1):
        print(f"  {i}. {citation['document_name']}")
    
    # Check for issue
    sources = [c['document_name'] for c in data['citations']]
    if 'AtlasIQ_Project_Guide.pdf' in sources:
        print("\n" + "="*80)
        print("⚠️  ISSUE CONFIRMED")
        print("="*80)
        print("AtlasIQ_Project_Guide.pdf is cited (should not be for audit letter query)")
        print("\nCheck backend.log for detailed diagnostic output:")
        print("  - DenseRetriever scores")
        print("  - BM25Retriever scores")
        print("  - RRF fusion scores")
        print("  - Hydrated chunks")
        print("  - Citation builder input")
    else:
        print("\n✅ Issue resolved - only audit letter cited!")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)

print("\n" + "="*80)
print("Check the backend process output for detailed diagnostic logs")
print("="*80)
