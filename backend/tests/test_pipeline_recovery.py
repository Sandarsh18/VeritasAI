"""
test_pipeline_recovery.py — Veritas AI Pipeline Recovery Tests

These 6 tests verify that the full pipeline is:
  1. Stable (no crashes)
  2. Evidence-grounded (no hallucinations)
  3. API-connected (real search results)
  4. Graph-enhanced (Neo4j used when available)
  5. Fully testable (deterministic outputs for edge cases)

Usage:
  cd backend && python -m pytest tests/test_pipeline_recovery.py -v
"""

import asyncio
import os
import sys

import pytest

# Allow imports from backend root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import run_claim_graph, ClaimState


def _run(coro):
    """Helper to run async from sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test 1: Factual claim with verifiable evidence
# ---------------------------------------------------------------------------
class TestFactualClaim:
    """A real-world factual claim should return evidence and a verdict."""

    def test_returns_evidence(self):
        result: ClaimState = _run(run_claim_graph("India won the 2011 Cricket World Cup"))
        evidence = result.get("evidence", [])
        assert len(evidence) > 0, f"Expected evidence, got {len(evidence)}"

    def test_verdict_is_valid(self):
        result: ClaimState = _run(run_claim_graph("India won the 2011 Cricket World Cup"))
        verdict = result.get("verdict", "")
        assert verdict in {"TRUE", "FALSE", "MISLEADING", "UNVERIFIED", "INSUFFICIENT_DATA"}, \
            f"Invalid verdict: {verdict}"

    def test_confidence_in_range(self):
        result: ClaimState = _run(run_claim_graph("India won the 2011 Cricket World Cup"))
        confidence = result.get("confidence", -1)
        assert 0 <= confidence <= 100, f"Confidence out of range: {confidence}"

    def test_reasoning_not_empty(self):
        result: ClaimState = _run(run_claim_graph("India won the 2011 Cricket World Cup"))
        reasoning = result.get("reasoning", "")
        assert len(reasoning) > 10, f"Reasoning too short: {reasoning!r}"


# ---------------------------------------------------------------------------
# Test 2: Misinformation claim (should find debunking evidence)
# ---------------------------------------------------------------------------
class TestMisinformationClaim:
    """A known misinformation claim should trigger misinfo query expansion."""

    def test_returns_evidence(self):
        result: ClaimState = _run(run_claim_graph("5G towers are spreading COVID-19"))
        evidence = result.get("evidence", [])
        assert len(evidence) > 0, f"Expected debunking evidence, got {len(evidence)}"

    def test_verdict_not_true(self):
        result: ClaimState = _run(run_claim_graph("5G towers are spreading COVID-19"))
        verdict = result.get("verdict", "")
        # A known misinformation claim should NOT be marked TRUE
        assert verdict != "TRUE", f"Misinformation should not be TRUE, got: {verdict}"


# ---------------------------------------------------------------------------
# Test 3: Gibberish claim (should return INSUFFICIENT_DATA)
# ---------------------------------------------------------------------------
class TestGibberishClaim:
    """A gibberish claim should produce INSUFFICIENT_DATA with no hallucinations."""

    def test_insufficient_data_verdict(self):
        result: ClaimState = _run(run_claim_graph("xyzzy florp blargh 12345 qwerty"))
        verdict = result.get("verdict", "")
        assert verdict == "INSUFFICIENT_DATA", f"Gibberish should be INSUFFICIENT_DATA, got: {verdict}"

    def test_no_hallucinated_evidence(self):
        result: ClaimState = _run(run_claim_graph("xyzzy florp blargh 12345 qwerty"))
        evidence = result.get("evidence", [])
        # Should have 0 evidence for gibberish
        assert len(evidence) == 0, f"Gibberish should have 0 evidence, got {len(evidence)}"


# ---------------------------------------------------------------------------
# Test 4: Opinion claim (should be caught by analyzer)
# ---------------------------------------------------------------------------
class TestOpinionClaim:
    """An opinion should be detected and handled gracefully."""

    def test_handled_gracefully(self):
        result: ClaimState = _run(run_claim_graph("Pizza is the best food in the world"))
        verdict = result.get("verdict", "")
        # Opinions should be UNVERIFIED or INSUFFICIENT_DATA
        assert verdict in {"UNVERIFIED", "INSUFFICIENT_DATA"}, \
            f"Opinion should be UNVERIFIED/INSUFFICIENT_DATA, got: {verdict}"


# ---------------------------------------------------------------------------
# Test 5: No-evidence enforcement (agents should not hallucinate)
# ---------------------------------------------------------------------------
class TestNoEvidenceEnforcement:
    """When evidence=[], agents must return canned responses, not LLM output."""

    def test_prosecutor_canned_response(self):
        """Prosecutor should return canned response with no evidence."""
        from agents import _prosecutor_node
        state: ClaimState = {"claim": "Test claim", "evidence": []}
        result = _prosecutor_node(state)
        strength = result.get("prosecutor_strength", "")
        assert strength == "none", f"Expected prosecutor strength 'none', got: {strength}"
        points = result.get("prosecutor_points", [])
        assert "No contradictory evidence found." in points

    def test_defender_canned_response(self):
        """Defender should return canned response with no evidence."""
        from agents import _defender_node
        state: ClaimState = {"claim": "Test claim", "evidence": []}
        result = _defender_node(state)
        strength = result.get("defender_strength", "")
        assert strength == "none", f"Expected defender strength 'none', got: {strength}"
        points = result.get("defender_points", [])
        assert "No supporting evidence found." in points


# ---------------------------------------------------------------------------
# Test 6: Neo4j graph store (graceful degradation)
# ---------------------------------------------------------------------------
class TestNeo4jGraceful:
    """Neo4j operations should not crash even if Neo4j is unavailable."""

    def test_store_claim_no_crash(self):
        from graph import GraphStore
        store = GraphStore()
        # Don't call connect() — driver will be None
        try:
            store.store_claim(
                claim="Test claim for Neo4j",
                results=[{"link": "https://example.com", "title": "Test", "source": "Test"}],
                verdict={"verdict": "TRUE", "confidence": 80},
            )
        except Exception as e:
            pytest.fail(f"store_claim should not crash without Neo4j: {e}")

    def test_get_source_reputation_no_crash(self):
        from graph import GraphStore
        store = GraphStore()
        rep = store.get_source_reputation("https://reuters.com/test")
        assert rep == 0.5, f"Default reputation should be 0.5, got: {rep}"

    def test_get_related_claims_no_crash(self):
        from graph import GraphStore
        store = GraphStore()
        related = store.get_related_claims("Test claim")
        assert related == [], f"Should return empty list without Neo4j, got: {related}"
