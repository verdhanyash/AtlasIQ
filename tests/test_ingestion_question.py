"""Test the ingestion pipeline question."""

import requests

url = "http://localhost:8000/query"

query = {
    "question": "How does the AtlasIQ ingestion pipeline work?",
    "top_k": 5
}

print("🔍 Testing:", query["question"])
print("=" * 80)

response = requests.post(url, json=query)

if response.status_code == 200:
    result = response.json()

    print(f"\n📝 Answer:\n{result['answer']}\n")
    print("=" * 80)
    print(f"🎯 Confidence: {result['confidence']}%")
    print(f"\n📚 Citations ({len(result['citations'])}):")
    for i, citation in enumerate(result['citations'], 1):
        doc_name = citation.get('document_name', citation.get('filename', 'Unknown'))
        page = citation.get('page', citation.get('page_number', 'N/A'))
        print(f"  {i}. {doc_name} (Page {page})")

    # Check if answer is clean
    has_inline = '[Source:' in result['answer'] or '[Page:' in result['answer'] or '[Document:' in result['answer']

    print("\n" + "=" * 80)
    if has_inline:
        print("❌ FAILED: Answer contains inline citations")
    else:
        print("✅ PASSED: Clean answer without inline citations!")
        print("   Citations are displayed separately below the answer.")
    print("=" * 80)

else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
