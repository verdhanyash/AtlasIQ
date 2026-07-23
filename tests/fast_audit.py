"""Fast retrieval audit - 20 critical questions with parallel execution."""
import asyncio
import json
from datetime import datetime
import httpx


# Critical test questions (reduced from 50+ to 20)
CRITICAL_TESTS = [
    # Exact match (should work perfectly)
    ("What is AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "high"),
    ("What is this audit engagement letter about?", ["2024-Audit"], "high"),
    ("What database does AtlasIQ use for vectors?", ["AtlasIQ_Project_Guide.pdf"], "high"),
    
    # Specific details
    ("What embedding model does AtlasIQ use?", ["AtlasIQ_Project_Guide.pdf"], "high"),
    ("What years does the audit engagement letter cover?", ["2024-Audit"], "high"),
    
    # Multi-document (challenging)
    ("What documents mention responsibilities?", ["AtlasIQ_Project_Guide.pdf", "2024-Audit"], "medium"),
    
    # Inference
    ("What is the main benefit of using AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    ("How does AtlasIQ handle document processing?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    
    # Technical
    ("What is hybrid retrieval in AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "high"),
    ("How does BM25 work in AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    
    # Out of scope (should refuse)
    ("What is the capital of France?", [], "refuse"),
    ("Who is the president of India?", [], "refuse"),
    ("What is the weather today?", [], "refuse"),
    ("How do I cook pasta?", [], "refuse"),
    ("What is quantum physics?", [], "refuse"),
    
    # Edge cases
    ("", [], "refuse"),  # Empty
    ("a", [], "refuse"),  # Single char
    
    # Ambiguous
    ("What are the requirements?", ["2024-Audit", "AtlasIQ_Project_Guide.pdf"], "medium"),
    ("How does it work?", ["AtlasIQ_Project_Guide.pdf"], "low"),
    
    # Negation (challenging)
    ("What does AtlasIQ not support?", ["AtlasIQ_Project_Guide.pdf"], "low"),
]


async def query_atlasiq(question: str, session: httpx.AsyncClient) -> dict:
    """Query AtlasIQ API."""
    try:
        response = await session.post(
            "http://localhost:8000/query",
            json={"question": question},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "question": question}


def evaluate(question: str, response: dict, expected_docs: list[str], expected_conf: str) -> dict:
    """Evaluate response."""
    if "error" in response:
        return {
            "question": question,
            "status": "ERROR",
            "error": response["error"],
            "passed": False,
        }
    
    answer = response.get("answer", "")
    citations = response.get("citations", [])
    confidence = response.get("confidence", 0.0)
    sources = response.get("sources", [])
    
    # Check refusal
    refused = any(p in answer.lower() for p in [
        "don't have enough information",
        "cannot answer",
        "unable to answer",
        "not enough information",
    ])
    
    should_refuse = expected_conf == "refuse"
    
    # Evaluate based on expectation
    if should_refuse:
        if refused:
            return {
                "question": question,
                "status": "CORRECT_REFUSAL",
                "confidence": confidence,
                "passed": confidence < 0.30,
            }
        else:
            return {
                "question": question,
                "status": "FALSE_POSITIVE",
                "confidence": confidence,
                "passed": False,
            }
    
    if refused and not should_refuse:
        return {
            "question": question,
            "status": "FALSE_NEGATIVE",
            "confidence": confidence,
            "passed": False,
        }
    
    # Calculate precision
    if not expected_docs:
        retrieval_precision = 1.0 if not sources else 0.0
    else:
        correct = sum(1 for s in sources if any(exp in s for exp in expected_docs))
        retrieval_precision = correct / len(sources) if sources else 0.0
    
    citation_correctness = 1.0
    if citations and expected_docs:
        correct = sum(1 for c in citations if any(exp in c.get("document_name", "") for exp in expected_docs))
        citation_correctness = correct / len(citations)
    
    # Check confidence calibration
    if expected_conf == "high":
        confidence_match = confidence >= 0.70
    elif expected_conf == "medium":
        confidence_match = 0.40 <= confidence <= 0.85
    elif expected_conf == "low":
        confidence_match = confidence <= 0.60
    else:
        confidence_match = True
    
    passed = (
        retrieval_precision >= 0.8 and
        citation_correctness >= 0.8 and
        confidence_match
    )
    
    # Check citation metadata
    has_metadata = False
    if citations:
        first = citations[0]
        has_metadata = (
            "chunk_index" in first and 
            "score" in first and
            first.get("chunk_index") is not None and
            first.get("score", 0.0) > 0
        )
    
    return {
        "question": question,
        "status": "ANSWERED",
        "retrieval_precision": round(retrieval_precision, 2),
        "citation_correctness": round(citation_correctness, 2),
        "confidence": round(confidence, 2),
        "expected_confidence": expected_conf,
        "confidence_match": confidence_match,
        "has_metadata": has_metadata,
        "num_citations": len(citations),
        "sources": sources,
        "passed": passed,
    }


async def run_fast_audit():
    """Run fast audit with parallel requests."""
    print("=" * 80)
    print("FAST RETRIEVAL AUDIT - 20 Critical Questions")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Running {len(CRITICAL_TESTS)} queries in parallel batches...")
    print()
    
    # Process in batches of 5 to avoid overwhelming the server
    batch_size = 5
    all_results = []
    
    async with httpx.AsyncClient() as session:
        for i in range(0, len(CRITICAL_TESTS), batch_size):
            batch = CRITICAL_TESTS[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(CRITICAL_TESTS) + batch_size - 1) // batch_size
            
            print(f"[Batch {batch_num}/{total_batches}] Processing {len(batch)} queries...")
            
            # Run batch in parallel
            tasks = [query_atlasiq(q, session) for q, _, _ in batch]
            responses = await asyncio.gather(*tasks)
            
            # Evaluate each
            for (question, expected_docs, expected_conf), response in zip(batch, responses):
                result = evaluate(question, response, expected_docs, expected_conf)
                all_results.append(result)
                
                # Print result
                status_icon = "[PASS]" if result["passed"] else "[FAIL]"
                q_short = question[:50] + "..." if len(question) > 50 else question
                print(f"  {status_icon} {q_short}")
                if result["status"] == "ANSWERED":
                    print(f"         Ret: {result['retrieval_precision']:.0%} | "
                          f"Cit: {result['citation_correctness']:.0%} | "
                          f"Conf: {result['confidence']:.0%} | "
                          f"Meta: {'YES' if result.get('has_metadata') else 'NO'}")
                elif result["status"] == "CORRECT_REFUSAL":
                    print(f"         Correctly refused (conf: {result['confidence']:.0%})")
                elif result["status"] in ["FALSE_POSITIVE", "FALSE_NEGATIVE"]:
                    print(f"         {result['status']} (conf: {result['confidence']:.0%})")
            
            print()
    
    # Summary
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    
    answered = [r for r in all_results if r["status"] == "ANSWERED"]
    refusals = [r for r in all_results if r["status"] in ["CORRECT_REFUSAL", "FALSE_NEGATIVE"]]
    correct_refusals = [r for r in all_results if r["status"] == "CORRECT_REFUSAL"]
    false_positives = [r for r in all_results if r["status"] == "FALSE_POSITIVE"]
    false_negatives = [r for r in all_results if r["status"] == "FALSE_NEGATIVE"]
    
    print(f"\nOVERALL: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"  - Answered correctly: {len([r for r in answered if r['passed']])}/{len(answered)}")
    print(f"  - Refused correctly: {len(correct_refusals)}/{len(refusals)}")
    print(f"  - False positives: {len(false_positives)}")
    print(f"  - False negatives: {len(false_negatives)}")
    
    if answered:
        avg_ret = sum(r["retrieval_precision"] for r in answered) / len(answered)
        avg_cit = sum(r["citation_correctness"] for r in answered) / len(answered)
        avg_conf = sum(r["confidence"] for r in answered) / len(answered)
        with_metadata = sum(1 for r in answered if r.get("has_metadata", False))
        
        print(f"\nANSWERED QUERIES:")
        print(f"  - Avg Retrieval Precision: {avg_ret:.1%}")
        print(f"  - Avg Citation Correctness: {avg_cit:.1%}")
        print(f"  - Avg Confidence: {avg_conf:.1%}")
        print(f"  - Citations with metadata: {with_metadata}/{len(answered)}")
    
    # Key issues
    print(f"\nKEY FINDINGS:")
    issues = []
    
    if answered:
        avg_ret = sum(r["retrieval_precision"] for r in answered) / len(answered)
        if avg_ret < 0.80:
            issues.append(f"  [!] Low retrieval precision ({avg_ret:.1%})")
        
        avg_cit = sum(r["citation_correctness"] for r in answered) / len(answered)
        if avg_cit < 0.80:
            issues.append(f"  [!] Low citation correctness ({avg_cit:.1%})")
        
        with_metadata = sum(1 for r in answered if r.get("has_metadata", False))
        if with_metadata < len(answered):
            issues.append(f"  [!] Missing citation metadata in {len(answered) - with_metadata} responses")
    
    if len(false_positives) > 0:
        issues.append(f"  [!] {len(false_positives)} false positives (answering out-of-scope)")
    
    if len(false_negatives) > 0:
        issues.append(f"  [!] {len(false_negatives)} false negatives (refusing valid queries)")
    
    if not issues:
        print("  [OK] No critical issues detected!")
    else:
        for issue in issues:
            print(issue)
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total,
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives),
        },
        "results": all_results,
    }
    
    with open("fast_audit_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: fast_audit_results.json")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Final verdict
    if passed / total >= 0.85:
        print("\n[VERDICT] System performing WELL")
    elif passed / total >= 0.70:
        print("\n[VERDICT] System performing ADEQUATELY - minor improvements needed")
    else:
        print("\n[VERDICT] System needs IMPROVEMENT")


if __name__ == "__main__":
    asyncio.run(run_fast_audit())
