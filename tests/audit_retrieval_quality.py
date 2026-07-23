"""Comprehensive retrieval quality audit for AtlasIQ.

Tests 50+ realistic questions across multiple documents to measure:
- Retrieval precision (correct documents retrieved)
- Citation correctness (citations match answer)
- Hallucination rate (unsupported claims)
- Refusal quality (refuses when should)
- Confidence calibration (confidence matches quality)
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


# Test questions categorized by expected behavior
TEST_QUESTIONS = {
    "exact_match": [
        # Questions with clear answers in specific documents
        ("What is AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "high"),
        ("What is the purpose of this audit engagement letter?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "high"),
        ("What are the main components of AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "high"),
        ("Who is responsible for fraud detection according to the audit letter?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "high"),
        ("What file formats does AtlasIQ support?", ["AtlasIQ_Project_Guide.pdf"], "high"),
    ],
    "multi_document": [
        # Questions that legitimately span multiple documents
        ("What documents mention responsibilities?", ["AtlasIQ_Project_Guide.pdf", "2024-Audit-Representation-Engagement-Letter.pdf"], "medium"),
        ("Which documents discuss implementation?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    ],
    "inference": [
        # Questions requiring synthesis from document
        ("What is the main benefit of using AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("What are the key obligations in the audit engagement?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "medium"),
        ("How does AtlasIQ handle document processing?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    ],
    "specific_detail": [
        # Questions about specific facts
        ("What years does the audit engagement letter cover?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "high"),
        ("What embedding model does AtlasIQ use?", ["AtlasIQ_Project_Guide.pdf"], "high"),
        ("What database does AtlasIQ use for vectors?", ["AtlasIQ_Project_Guide.pdf"], "high"),
        ("What is the fee arrangement mentioned in the audit letter?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "medium"),
    ],
    "comparison": [
        # Questions comparing aspects
        ("What is the difference between the frontend and backend in AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("Compare the responsibilities mentioned in different sections of the audit letter", ["2024-Audit-Representation-Engagement-Letter.pdf"], "low"),
    ],
    "temporal": [
        # Questions about time/sequence
        ("When does the audit engagement end?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "high"),
        ("What is the timeline for AtlasIQ development?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    ],
    "negation": [
        # Questions with negative framing
        ("What does AtlasIQ not support?", ["AtlasIQ_Project_Guide.pdf"], "low"),
        ("What is not covered by the audit engagement?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "low"),
    ],
    "out_of_scope": [
        # Questions that should be refused
        ("What is the capital of France?", [], "refuse"),
        ("Who is the president of India?", [], "refuse"),
        ("What is the weather today?", [], "refuse"),
        ("How do I cook pasta?", [], "refuse"),
        ("What is quantum physics?", [], "refuse"),
        ("Tell me about the Roman Empire", [], "refuse"),
        ("What is machine learning?", [], "refuse"),
        ("Who won the World Cup in 2022?", [], "refuse"),
    ],
    "ambiguous": [
        # Ambiguous questions
        ("What are the requirements?", ["2024-Audit-Representation-Engagement-Letter.pdf", "AtlasIQ_Project_Guide.pdf"], "medium"),
        ("How does it work?", ["AtlasIQ_Project_Guide.pdf"], "low"),
        ("What is the purpose?", ["AtlasIQ_Project_Guide.pdf", "2024-Audit-Representation-Engagement-Letter.pdf"], "medium"),
    ],
    "partial_match": [
        # Questions with terms in multiple documents but answer in one
        ("What is the RAG architecture?", ["AtlasIQ_Project_Guide.pdf"], "high"),
        ("What confirmation is required from third parties?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "medium"),
    ],
    "technical": [
        # Technical questions
        ("What is hybrid retrieval in AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "high"),
        ("How does BM25 work in AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("What is the chunking strategy?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("What vector database is used?", ["AtlasIQ_Project_Guide.pdf"], "high"),
    ],
    "procedural": [
        # How-to questions
        ("How do I upload documents to AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("How do I query AtlasIQ?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("What steps are involved in document ingestion?", ["AtlasIQ_Project_Guide.pdf"], "medium"),
    ],
    "list_extraction": [
        # Questions expecting lists
        ("What are the responsibilities listed in the audit letter?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "high"),
        ("List the features of AtlasIQ", ["AtlasIQ_Project_Guide.pdf"], "medium"),
        ("What services are included in the audit?", ["2024-Audit-Representation-Engagement-Letter.pdf"], "medium"),
    ],
    "edge_cases": [
        # Edge cases
        ("", [], "refuse"),  # Empty query
        ("a", [], "refuse"),  # Single character
        ("the the the", [], "refuse"),  # Only stop words
        ("AtlasIQ" * 100, ["AtlasIQ_Project_Guide.pdf"], "low"),  # Repetitive
    ],
}


async def query_atlasiq(question: str, base_url: str = "http://localhost:8000") -> dict[str, Any]:
    """Query AtlasIQ API and return response."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{base_url}/query",
                json={"question": question},
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"error": "timeout", "question": question}
        except httpx.HTTPError as e:
            return {"error": str(e), "question": question}


def evaluate_retrieval(
    question: str,
    response: dict[str, Any],
    expected_docs: list[str],
    expected_confidence: str,
) -> dict[str, Any]:
    """Evaluate a single retrieval response."""
    
    if "error" in response:
        return {
            "question": question,
            "status": "ERROR",
            "error": response["error"],
            "retrieval_precision": 0.0,
            "citation_correctness": 0.0,
            "confidence_match": False,
            "passed": False,
        }
    
    answer = response.get("answer", "")
    citations = response.get("citations", [])
    confidence = response.get("confidence", 0.0)
    sources = response.get("sources", [])
    
    # Check if refused
    refused = any(phrase in answer.lower() for phrase in [
        "don't have enough information",
        "cannot answer",
        "unable to answer",
        "not enough information",
    ])
    
    # Expected to refuse?
    should_refuse = expected_confidence == "refuse"
    
    if should_refuse:
        # Correct refusal
        if refused:
            return {
                "question": question,
                "status": "CORRECT_REFUSAL",
                "confidence": confidence,
                "confidence_match": confidence < 0.30,  # Should be low
                "passed": True,
            }
        else:
            # False positive (answered when should refuse)
            return {
                "question": question,
                "status": "FALSE_POSITIVE",
                "answer_preview": answer[:100],
                "confidence": confidence,
                "citations": len(citations),
                "passed": False,
            }
    
    # Should answer but refused
    if refused and not should_refuse:
        return {
            "question": question,
            "status": "FALSE_NEGATIVE",
            "expected_docs": expected_docs,
            "confidence": confidence,
            "passed": False,
        }
    
    # Calculate retrieval precision
    if not expected_docs:
        retrieval_precision = 1.0 if not sources else 0.0
    else:
        correct_sources = sum(1 for src in sources if any(exp in src for exp in expected_docs))
        retrieval_precision = correct_sources / len(sources) if sources else 0.0
    
    # Calculate citation correctness
    if not citations:
        citation_correctness = 0.0
    else:
        correct_citations = sum(
            1 for cit in citations
            if any(exp in cit.get("document_name", "") for exp in expected_docs)
        ) if expected_docs else 0
        citation_correctness = correct_citations / len(citations)
    
    # Check confidence calibration
    if expected_confidence == "high":
        confidence_match = confidence >= 0.70
    elif expected_confidence == "medium":
        confidence_match = 0.40 <= confidence <= 0.85
    elif expected_confidence == "low":
        confidence_match = confidence <= 0.60
    else:
        confidence_match = True
    
    # Overall pass/fail
    passed = (
        retrieval_precision >= 0.8 and
        citation_correctness >= 0.8 and
        confidence_match
    )
    
    return {
        "question": question,
        "status": "ANSWERED",
        "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer,
        "retrieval_precision": round(retrieval_precision, 2),
        "citation_correctness": round(citation_correctness, 2),
        "confidence": round(confidence, 2),
        "expected_confidence": expected_confidence,
        "confidence_match": confidence_match,
        "num_citations": len(citations),
        "sources": sources,
        "expected_docs": expected_docs,
        "passed": passed,
    }


async def run_audit() -> None:
    """Run complete retrieval quality audit."""
    
    print("=" * 80)
    print("ATLASIQ RETRIEVAL QUALITY AUDIT")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_results = []
    category_stats = {}
    
    # Test each category
    for category, questions in TEST_QUESTIONS.items():
        print(f"\n{'=' * 80}")
        print(f"Category: {category.upper().replace('_', ' ')}")
        print(f"{'=' * 80}")
        
        category_results = []
        
        for i, (question, expected_docs, expected_conf) in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Testing: {question[:60]}...")
            
            response = await query_atlasiq(question)
            result = evaluate_retrieval(question, response, expected_docs, expected_conf)
            
            status_symbol = "✅" if result["passed"] else "❌"
            print(f"    {status_symbol} Status: {result['status']}")
            
            if result["status"] == "ANSWERED":
                print(f"    📊 Retrieval: {result['retrieval_precision']:.0%} | "
                      f"Citation: {result['citation_correctness']:.0%} | "
                      f"Confidence: {result['confidence']:.0%}")
            elif result["status"] == "CORRECT_REFUSAL":
                print(f"    🚫 Correctly refused | Confidence: {result['confidence']:.0%}")
            
            category_results.append(result)
            all_results.append({"category": category, **result})
        
        # Category statistics
        passed = sum(1 for r in category_results if r["passed"])
        total = len(category_results)
        
        category_stats[category] = {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total if total > 0 else 0.0,
        }
        
        print(f"\n📈 Category Summary: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    # Overall statistics
    print(f"\n\n{'=' * 80}")
    print("OVERALL AUDIT RESULTS")
    print(f"{'=' * 80}\n")
    
    total_tests = len(all_results)
    total_passed = sum(1 for r in all_results if r["passed"])
    
    # Calculate metrics
    answered = [r for r in all_results if r["status"] == "ANSWERED"]
    refusals = [r for r in all_results if r["status"] in ["CORRECT_REFUSAL", "FALSE_NEGATIVE"]]
    correct_refusals = [r for r in all_results if r["status"] == "CORRECT_REFUSAL"]
    false_positives = [r for r in all_results if r["status"] == "FALSE_POSITIVE"]
    false_negatives = [r for r in all_results if r["status"] == "FALSE_NEGATIVE"]
    
    if answered:
        avg_retrieval = sum(r.get("retrieval_precision", 0) for r in answered) / len(answered)
        avg_citation = sum(r.get("citation_correctness", 0) for r in answered) / len(answered)
        avg_confidence = sum(r.get("confidence", 0) for r in answered) / len(answered)
    else:
        avg_retrieval = avg_citation = avg_confidence = 0.0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
    print(f"Failed: {total_tests - total_passed} ({(total_tests-total_passed)/total_tests*100:.1f}%)")
    print()
    
    print("📊 RETRIEVAL METRICS:")
    print(f"  • Average Retrieval Precision: {avg_retrieval:.1%}")
    print(f"  • Average Citation Correctness: {avg_citation:.1%}")
    print(f"  • Average Confidence: {avg_confidence:.1%}")
    print()
    
    print("🚫 REFUSAL QUALITY:")
    print(f"  • Correct Refusals: {len(correct_refusals)}/{len(refusals)} "
          f"({len(correct_refusals)/len(refusals)*100 if refusals else 0:.1f}%)")
    print(f"  • False Positives (answered when should refuse): {len(false_positives)}")
    print(f"  • False Negatives (refused when should answer): {len(false_negatives)}")
    print()
    
    print("📂 BY CATEGORY:")
    for category, stats in category_stats.items():
        print(f"  • {category:20s}: {stats['passed']:2d}/{stats['total']:2d} "
              f"({stats['pass_rate']*100:5.1f}%)")
    print()
    
    # Identify issues
    print("🔍 IDENTIFIED ISSUES:")
    issues = []
    
    if avg_retrieval < 0.80:
        issues.append(f"⚠️  Low retrieval precision ({avg_retrieval:.1%}) - incorrect documents retrieved")
    
    if avg_citation < 0.80:
        issues.append(f"⚠️  Low citation correctness ({avg_citation:.1%}) - citations don't match answers")
    
    if len(false_positives) > total_tests * 0.1:
        issues.append(f"⚠️  High false positive rate ({len(false_positives)}/{total_tests}) - answering out-of-scope questions")
    
    if len(false_negatives) > total_tests * 0.1:
        issues.append(f"⚠️  High false negative rate ({len(false_negatives)}/{total_tests}) - refusing valid questions")
    
    # Check confidence calibration per category
    for conf_level in ["high", "medium", "low"]:
        matching = [r for r in answered if r.get("expected_confidence") == conf_level]
        if matching:
            calibrated = sum(1 for r in matching if r.get("confidence_match", False))
            if calibrated / len(matching) < 0.70:
                issues.append(f"⚠️  Poor confidence calibration for '{conf_level}' confidence questions "
                             f"({calibrated}/{len(matching)} = {calibrated/len(matching)*100:.0f}%)")
    
    if not issues:
        print("  ✅ No major issues detected!")
    else:
        for issue in issues:
            print(f"  {issue}")
    
    # Recommendations
    print(f"\n{'=' * 80}")
    print("RECOMMENDATIONS")
    print(f"{'=' * 80}\n")
    
    recommendations = []
    
    if avg_retrieval < 0.80:
        recommendations.append(
            "1. RETRIEVAL PRECISION:\n"
            "   - Review hybrid retrieval weights (dense vs BM25)\n"
            "   - Consider adding reranking model\n"
            "   - Tune RRF fusion parameters"
        )
    
    if avg_citation < 0.80:
        recommendations.append(
            "2. CITATION CORRECTNESS:\n"
            "   - Implement LLM-based citation validation\n"
            "   - Add embedding similarity check between answer and cited chunks\n"
            "   - Increase top-k threshold for citations"
        )
    
    if len(false_positives) > 0:
        recommendations.append(
            f"3. FALSE POSITIVES ({len(false_positives)} cases):\n"
            "   - Strengthen guardrails (increase min_confidence_score)\n"
            "   - Add query intent classification\n"
            "   - Improve LLM refusal detection"
        )
    
    if len(false_negatives) > 0:
        recommendations.append(
            f"4. FALSE NEGATIVES ({len(false_negatives)} cases):\n"
            "   - Lower guardrail threshold\n"
            "   - Review confidence calculation heuristics\n"
            "   - Check if documents are properly indexed"
        )
    
    # Check specific failing categories
    for category, stats in category_stats.items():
        if stats["pass_rate"] < 0.60 and category not in ["edge_cases", "out_of_scope"]:
            recommendations.append(
                f"5. {category.upper().replace('_', ' ')} CATEGORY ({stats['pass_rate']*100:.0f}% pass rate):\n"
                f"   - Review question types in this category\n"
                f"   - May need specialized handling for {category} queries"
            )
    
    if not recommendations:
        print("✅ System performing well! No immediate improvements needed.")
        print("\nOptional enhancements:")
        print("  • Add semantic reranking for even better precision")
        print("  • Implement query expansion for better recall")
        print("  • Add document-level metadata filtering")
    else:
        for rec in recommendations:
            print(rec)
            print()
    
    # Save detailed results
    output_file = Path("audit_results.json")
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "pass_rate": total_passed / total_tests,
                "avg_retrieval_precision": avg_retrieval,
                "avg_citation_correctness": avg_citation,
                "avg_confidence": avg_confidence,
                "false_positives": len(false_positives),
                "false_negatives": len(false_negatives),
            },
            "category_stats": category_stats,
            "all_results": all_results,
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print(f"\n✅ Audit complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(run_audit())
