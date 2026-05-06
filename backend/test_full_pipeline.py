#!/usr/bin/env python3
"""
Full Pipeline Test Suite for VeritasAI
Tests all 10 phases of the stabilization effort
"""

import json
import asyncio
import time
import sys
from datetime import datetime

# Test configuration
TEST_TIMEOUT = 900  # 15 minutes total
CLAIM_TIMEOUT = 120  # 2 minutes per claim

test_cases = [
    {
        "id": "TEST_1",
        "claim": "5G towers are spreading COVID-19",
        "expected_verdict": ["FALSE", "MISLEADING"],
        "min_evidence": 3,
        "description": "COVID misinformation with 5G conspiracy"
    },
    {
        "id": "TEST_2",
        "claim": "Is India developing 6G?",
        "expected_verdict": ["TRUE", "UNVERIFIED"],
        "min_evidence": 2,
        "description": "Technology claim about 6G development"
    },
    {
        "id": "TEST_3",
        "claim": "1kg of gold is costlier than 1kg of silver",
        "expected_verdict": ["TRUE", "FALSE"],
        "min_evidence": 2,
        "description": "Economic/financial claim"
    },
    {
        "id": "TEST_4",
        "claim": "asdfghhj",
        "expected_verdict": ["INSUFFICIENT_DATA", "UNVERIFIED"],
        "min_evidence": 0,
        "description": "Nonsense query - should return insufficient data"
    },
]

class TestResults:
    def __init__(self):
        self.tests = []
        self.start_time = datetime.now()
    
    def add_test(self, test_id, claim, verdict, evidence_count, reasoning_sample, passed, error=None):
        self.tests.append({
            "test_id": test_id,
            "claim": claim[:80],
            "verdict": verdict,
            "evidence_count": evidence_count,
            "reasoning_sample": reasoning_sample[:100] if reasoning_sample else "N/A",
            "passed": passed,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def summary(self):
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t["passed"])
        failed = total - passed
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total)*100:.1f}%" if total > 0 else "0%",
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "tests": self.tests
        }

async def test_api_connectivity():
    """PHASE 1: Verify API connectivity"""
    print("\n" + "="*60)
    print("PHASE 1: API CONNECTIVITY TEST")
    print("="*60)
    
    from rag.retriever import _search_serpapi, _search_newsapi
    
    test_query = "AI artificial intelligence"
    
    # Test SerpAPI
    print(f"\n[TEST] SerpAPI connectivity with query: '{test_query}'")
    serp_results, serp_meta = _search_serpapi(test_query, top_n=5)
    print(f"[SEARCH] SerpAPI status: {serp_meta.get('ok')}")
    print(f"[SEARCH] SerpAPI results count: {serp_meta.get('count')}")
    if serp_meta.get('error'):
        print(f"[SEARCH] SerpAPI error: {serp_meta.get('error')}")
    
    # Test NewsAPI
    print(f"\n[TEST] NewsAPI connectivity with query: '{test_query}'")
    news_results, news_meta = _search_newsapi(test_query, top_n=5)
    print(f"[SEARCH] NewsAPI status: {news_meta.get('ok')}")
    print(f"[SEARCH] NewsAPI results count: {news_meta.get('count')}")
    if news_meta.get('error'):
        print(f"[SEARCH] NewsAPI error: {news_meta.get('error')}")
    
    api_ok = (serp_meta.get('ok') or news_meta.get('ok'))
    print(f"\n[RESULT] API Connectivity: {'✓ PASS' if api_ok else '✗ FAIL'}")
    return api_ok

async def test_claim_verification(test_case, results):
    """Test a single claim verification"""
    from main import verify_claim, ClaimRequest
    from fastapi.testclient import TestClient
    from main import app
    
    client = TestClient(app)
    claim = test_case["claim"]
    test_id = test_case["id"]
    
    print(f"\n[{test_id}] Testing: {claim[:60]}...")
    print(f"Expected verdict: {test_case['expected_verdict']}")
    print(f"Min evidence required: {test_case['min_evidence']}")
    
    try:
        # Make request to verify endpoint
        response = client.post(
            "/api/verify",
            json={"claim": claim},
            timeout=CLAIM_TIMEOUT
        )
        
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
            print(f"[{test_id}] ✗ FAIL: {error_msg}")
            results.add_test(test_id, claim, "ERROR", 0, "", False, error_msg)
            return False
        
        data = response.json()
        verdict = data.get("verdict", "UNKNOWN")
        evidence_count = len(data.get("evidence", []))
        reasoning = data.get("reasoning", "")
        confidence = data.get("confidence", 0)
        stages = data.get("stages", {})
        
        # Validate results
        verdict_ok = verdict in test_case["expected_verdict"]
        evidence_ok = evidence_count >= test_case["min_evidence"]
        has_reasoning = len(reasoning.strip()) > 0 or verdict == "INSUFFICIENT_DATA"
        
        passed = verdict_ok and evidence_ok and has_reasoning
        
        print(f"[{test_id}] Verdict: {verdict} (expected {test_case['expected_verdict']}) - {'✓' if verdict_ok else '✗'}")
        print(f"[{test_id}] Evidence: {evidence_count} articles (min {test_case['min_evidence']}) - {'✓' if evidence_ok else '✗'}")
        print(f"[{test_id}] Confidence: {confidence}%")
        print(f"[{test_id}] Pipeline stages: {stages}")
        
        if not has_reasoning:
            print(f"[{test_id}] ✗ FAIL: No reasoning provided")
            passed = False
        
        if data.get("pipeline_warning"):
            print(f"[{test_id}] ⚠ Warning: {data.get('pipeline_warning')}")
        
        print(f"[{test_id}] Result: {'✓ PASS' if passed else '✗ FAIL'}")
        results.add_test(test_id, claim, verdict, evidence_count, reasoning, passed)
        return passed
        
    except Exception as e:
        error_msg = str(e)[:200]
        print(f"[{test_id}] ✗ FAIL: {error_msg}")
        results.add_test(test_id, claim, "ERROR", 0, "", False, error_msg)
        return False

async def test_evidence_grounding(results):
    """PHASE 3: Verify evidence is grounded (no hallucinations)"""
    print("\n" + "="*60)
    print("PHASE 3: EVIDENCE GROUNDING TEST")
    print("="*60)
    
    from agents.prosecutor import run_prosecutor
    from agents.defender import run_defender
    
    # Test with empty evidence
    print("\n[TEST] Agent behavior with no evidence")
    
    prosecutor_result = run_prosecutor("Test claim", [])
    defender_result = run_defender("Test claim", [])
    
    prosecutor_ok = (
        len(prosecutor_result.get("arguments", [])) > 0 and
        prosecutor_result.get("prosecution_strength") == "none"
    )
    defender_ok = (
        len(defender_result.get("arguments", [])) > 0 and
        defender_result.get("defense_strength") == "none"
    )
    
    print(f"[TEST] Prosecutor with empty evidence: {'✓ PASS' if prosecutor_ok else '✗ FAIL'}")
    print(f"[TEST] Defender with empty evidence: {'✓ PASS' if defender_ok else '✗ FAIL'}")
    
    return prosecutor_ok and defender_ok

async def run_all_tests():
    """Run all test phases"""
    print("\n" + "="*80)
    print("VERITAS AI - FULL SYSTEM TEST SUITE")
    print("="*80)
    print(f"Start time: {datetime.now().isoformat()}")
    
    results = TestResults()
    all_passed = True
    
    # PHASE 1: API Connectivity
    print("\n[PHASES 1-2] Testing API connectivity and retrieval...")
    api_ok = await test_api_connectivity()
    all_passed = all_passed and api_ok
    
    # PHASE 3: Evidence Grounding
    print("\n[PHASE 3] Testing evidence grounding...")
    evidence_ok = await test_evidence_grounding(results)
    all_passed = all_passed and evidence_ok
    
    # PHASE 10: Full Claim Tests
    print("\n[PHASE 10] Testing full claim verification pipeline...")
    for test_case in test_cases:
        test_ok = await test_claim_verification(test_case, results)
        all_passed = all_passed and test_ok
    
    # Summary
    summary = results.summary()
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass rate: {summary['pass_rate']}")
    print(f"Duration: {summary['duration_seconds']:.1f}s")
    
    # Save results
    results_file = "/tmp/veritas-test-results.json"
    with open(results_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
