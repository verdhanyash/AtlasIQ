"""Test query with hybrid_min_score filtering enabled."""
import requests
import json
import time

print("Waiting for backend to reload...")
time.sleep(2)

print("\n=== TESTING FILTERED RETRIEVAL ===\n")

# Test the audit letter query
response = requests.post(
    "http://localhost:8000/query",
    json={"question": "What is this audit engagement letter about?"}
)

if response.status_code == 200:
    data = response.json()
    
    print(f"Answer: {data['answer'][:150]}...")
    print(f"\nConfidence: {data['confidence']:.2%}")
    print(f"Citations: {len(data['citations'])}")
    
    print("\nCitation Sources:")
    for i, citation in enumerate(data['citations'], 1):
        print(f"  {i}. {citation['document_name']}")
        if 'score' in citation:
            print(f"     RRF Score: {citation['score']:.4f}")
    
    # Check if AtlasIQ_Project_Guide.pdf is still appearing
    sources = [c['document_name'] for c in data['citations']]
    if 'AtlasIQ_Project_Guide.pdf' in sources:
        print("\n⚠️  ISSUE: AtlasIQ_Project_Guide.pdf still appearing in citations!")
        print("    This suggests the filter threshold may need to be increased.")
    else:
        print("\n✅ SUCCESS: Only audit letter citations (irrelevant docs filtered out)")
    
    # Show retrieval details if available
    if 'retrieval_details' in data and data['retrieval_details']:
        print("\nRetrieval Details:")
        details = data['retrieval_details']
        if 'stats' in details:
            print(f"  Total candidates: {details['stats'].get('total_candidates', 'N/A')}")
            print(f"  Final retrieved: {details['stats'].get('final_retrieved', 'N/A')}")
            print(f"  Filtered out: {details['stats'].get('filtered_out', 'N/A')}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
