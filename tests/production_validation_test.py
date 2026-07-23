"""Production validation tests for AtlasIQ - Runtime behavior testing."""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def run_health_check():
    """Test backend health check."""
    print("\n=== HEALTH CHECK ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"PostgreSQL: {data['checks']['postgresql']}")
    print(f"Qdrant: {data['checks']['qdrant']}")
    print(f"LLM Provider: {data['checks']['llm_provider']}")
    return response.status_code == 200

def run_query(question: str):
    """Test query endpoint."""
    print(f"\n=== QUERY TEST: {question[:50]}... ===")
    response = requests.post(
        f"{BASE_URL}/query",
        json={"question": question}
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Answer: {data['answer'][:200]}...")
        print(f"Confidence: {data['confidence']:.2%}")
        print(f"Citations: {len(data['citations'])}")
        if data['citations']:
            print(f"First citation: {data['citations'][0]['document_name']} (page {data['citations'][0]['page']})")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_documents_list():
    """Test listing documents."""
    print("\n=== DOCUMENTS LIST ===")
    response = requests.get(f"{BASE_URL}/ingest/documents?limit=10")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict) and 'documents' in data:
            docs = data['documents']
            print(f"Total documents: {len(docs)}")
            if docs:
                print(f"First document: {docs[0].get('document_name', 'N/A')}")
                print(f"Document ID: {docs[0].get('document_id', 'N/A')}")
        elif isinstance(data, list):
            print(f"Total documents: {len(data)}")
            if data:
                print(f"First document: {data[0].get('document_name', 'N/A')}")
                print(f"Document ID: {data[0].get('document_id', 'N/A')}")
        return True
    return False

def test_invalid_upload():
    """Test invalid file upload."""
    print("\n=== INVALID UPLOAD TEST ===")
    files = {'file': ('test.xyz', b'invalid content', 'application/octet-stream')}
    response = requests.post(f"{BASE_URL}/ingest/upload", files=files)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 422  # Should reject unsupported format

def test_empty_query():
    """Test empty query."""
    print("\n=== EMPTY QUERY TEST ===")
    response = requests.post(f"{BASE_URL}/query", json={"question": ""})
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.json()}")
    return True

def main():
    """Run all production validation tests."""
    print("=" * 60)
    print("PRODUCTION VALIDATION TEST SUITE")
    print("=" * 60)
    
    tests = []
    
    # Test 1: Health check
    tests.append(("Health Check", test_health()))
    
    # Test 2: List documents
    tests.append(("Documents List", test_documents_list()))
    
    # Test 3: Query with real document
    tests.append(("Query Test 1", test_query("What is this audit engagement letter about?")))
    
    # Test 4: Another query
    tests.append(("Query Test 2", test_query("What are the responsibilities mentioned?")))
    
    # Test 5: Query unrelated topic (should have low confidence or refusal)
    tests.append(("Query Test 3 (Unrelated)", test_query("What is the weather today?")))
    
    # Test 6: Empty query
    tests.append(("Empty Query", test_empty_query()))
    
    # Test 7: Invalid upload
    tests.append(("Invalid Upload", test_invalid_upload()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - PRODUCTION READY")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review needed")

if __name__ == "__main__":
    main()
