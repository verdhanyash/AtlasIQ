"""Clear the prompt builder cache and test."""

import requests

# Clear the cache endpoint if it exists, or just make a new query
url = "http://localhost:8000/query"

query = {
    "question": "What is AtlasIQ?",
    "top_k": 3
}

print("Testing query after cache clear...")
response = requests.post(url, json=query)

if response.status_code == 200:
    result = response.json()
    answer = result['answer']

    print(f"\n📝 Answer:\n{answer}\n")

    # Check for inline citations
    has_inline = '[Source:' in answer or '[Page:' in answer or'[Document:' in answer

    if has_inline:
        print("❌ STILL HAS INLINE CITATIONS")
        print("\nThe PromptBuilder is cached with @lru_cache!")
        print("Need to restart backend completely (not just --reload)")
    else:
        print("✅ CLEAN - No inline citations!")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
