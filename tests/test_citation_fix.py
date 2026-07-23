"""Test script to verify inline citations are removed from answers."""


import requests


def test_query():
    url = "http://localhost:8000/query"

    query = {
        "question": "How does the AtlasIQ ingestion pipeline work?",
        "top_k": 5
    }

    print("🔍 Testing query:", query["question"])
    print("-" * 80)

    response = requests.post(url, json=query)

    if response.status_code == 200:
        result = response.json()

        print("\n✅ Query successful!")
        print(f"\n📝 Answer:\n{result['answer']}\n")
        print(f"🎯 Confidence: {result['confidence']}%")
        print(f"\n📚 Citations ({len(result['citations'])}):")
        for i, citation in enumerate(result['citations'], 1):
            print(f"  {i}. {citation['filename']} (Page {citation['page_number']})")

        # Check if answer contains inline citations
        answer = result['answer']
        has_inline_citation = '[Source:' in answer or '[Page:' in answer

        print("\n" + "=" * 80)
        if has_inline_citation:
            print("❌ FAILED: Answer still contains inline citations")
            print("   The LLM is still adding [Source:...] in the answer text")
        else:
            print("✅ PASSED: Answer is clean without inline citations")
            print("   Citations are shown separately in the UI")
        print("=" * 80)

    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_query()
