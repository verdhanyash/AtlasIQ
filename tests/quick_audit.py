"""Quick audit test - subset of questions for faster validation."""
import asyncio
import httpx


async def test_query(question: str, expected_doc: str = None) -> dict:
    """Test a single query."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "http://localhost:8000/query",
                json={"question": question},
            )
            response.raise_for_status()
            result = response.json()
            
            # Check if refused
            answer = result.get("answer", "")
            refused = any(phrase in answer.lower() for phrase in [
                "don't have enough information",
                "cannot answer",
                "unable to answer",
            ])
            
            # Get sources
            sources = result.get("sources", [])
            citations = result.get("citations", [])
            confidence = result.get("confidence", 0.0)
            
            # Simple pass/fail
            if expected_doc:
                passed = any(expected_doc in src for src in sources)
                status = "✅ PASS" if passed else "❌ FAIL"
            elif expected_doc is None:  # Should refuse
                passed = refused and confidence < 0.30
                status = "✅ CORRECT REFUSAL" if passed else "❌ FALSE POSITIVE"
            else:
                passed = True
                status = "✅ ANSWERED"
            
            print(f"\n{status}: {question[:60]}")
            print(f"  Confidence: {confidence:.0%}")
            print(f"  Sources: {sources}")
            print(f"  Citations: {len(citations)}")
            if citations and len(citations) > 0:
                first_cit = citations[0]
                chunk_idx = first_cit.get('chunk_index', 'N/A')
                score = first_cit.get('score', 0.0)
                print(f"  Sample Citation: chunk={chunk_idx}, score={score:.3f}")
            
            return {"question": question, "passed": passed, "result": result}
            
        except Exception as e:
            print(f"\n❌ ERROR: {question[:60]}")
            print(f"  {str(e)}")
            return {"question": question, "passed": False, "error": str(e)}


async def main():
    """Run quick audit."""
    print("=" * 80)
    print("QUICK AUDIT - Sample Questions")
    print("=" * 80)
    
    tests = [
        # Should answer correctly
        ("What is AtlasIQ?", "AtlasIQ_Project_Guide.pdf"),
        ("What is this audit letter about?", "2024-Audit"),
        ("What database does AtlasIQ use?", "AtlasIQ_Project_Guide.pdf"),
        
        # Should refuse
        ("What is the capital of France?", None),
        ("Who is the president of India?", None),
        ("What is the weather today?", None),
    ]
    
    results = []
    for question, expected in tests:
        result = await test_query(question, expected)
        results.append(result)
        await asyncio.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"\n{'✅ ALL TESTS PASSED' if passed == total else '❌ SOME TESTS FAILED'}")


if __name__ == "__main__":
    asyncio.run(main())
