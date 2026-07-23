"""Test script to verify inline citations are removed from answers."""

import requests


def run_test():
    url = "http://localhost:8000/query"

    query = {
        "question": "How does the AtlasIQ ingestion pipeline work?",
        "top_k": 5
    }

    print("🔍 Testing query:", query["question"])
    print("-" * 80)

    try:
        response = requests.post(url, json=query)

        if response.status_code == 200:
            result = response.json()

            print("\n✅ Query successful!")
            print(f"\n📝 Answer:\n{result['answer']}\n")
            print(f"🎯 Confidence: {result.get('confidence', result.get('confidence_score', 0))}%")
            print(f"\n📚 Citations ({len(result.get('citations', []))}):")
            for i, citation in enumerate(result.get('citations', []), 1):
                doc_name = citation.get('document_name') or citation.get('filename', 'Unknown')
                page_num = citation.get('page') or citation.get('page_number', 'N/A')
                print(f"  {i}. {doc_name} (Page {page_num})")

            # Check if answer contains inline citations
            answer = result['answer']
            has_inline_citation = '[Source:' in answer or '[Page:' in answer

            print("\n" + "=" * 80)
            if has_inline_citation:
                print("❌ FAILED: Answer still contains inline citations")
            else:
                print("✅ PASSED: Answer is clean without inline citations")
            print("=" * 80)
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print("Skipping live test:", e)


if __name__ == "__main__":
    run_test()
