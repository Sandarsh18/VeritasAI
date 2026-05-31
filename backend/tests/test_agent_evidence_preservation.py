"""Agents must never return empty arguments when evidence is present.

Covers the Evidence Preservation Rule + minimal opposing/supporting analysis
(Property 5: evidence-to-agents; Property 6: judge inputs)."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
for p in (str(BACKEND_DIR), str(BACKEND_DIR / "agents")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agents.prosecutor import run_prosecutor
from agents.defender import run_defender


# Evidence that clearly SUPPORTS the claim (no contradiction) -> historically
# starved the prosecutor.
SUPPORTING_EVIDENCE = [
    {
        "title": "Bengaluru is the capital of Karnataka",
        "source": "gov.in",
        "content": "Bengaluru is the official capital city of the Indian state of Karnataka.",
        "url": "https://example.gov.in/a",
        "credibility_score": 0.9,
    },
    {
        "title": "Karnataka administrative capital",
        "source": "britannica.com",
        "content": "The capital of Karnataka is Bengaluru, also known as Bangalore.",
        "url": "https://example.com/b",
        "credibility_score": 0.85,
    },
    {
        "title": "About Karnataka",
        "source": "byjus.com",
        "content": "Bengaluru serves as the capital of Karnataka.",
        "url": "https://example.com/c",
        "credibility_score": 0.7,
    },
]


def test_prosecutor_not_empty_on_one_sided_support():
    result = run_prosecutor("Is Bangalore the capital of Karnataka?", SUPPORTING_EVIDENCE)
    assert len(result["arguments"]) >= 1, "Prosecutor must produce a minimal opposing analysis"
    assert result["prosecution_strength"] in {"strong", "moderate", "weak", "none"}
    # arguments must carry source attribution
    for arg in result["arguments"]:
        assert isinstance(arg, dict)
        assert arg.get("source")


def test_defender_not_empty_on_one_sided_support():
    result = run_defender("Is Bangalore the capital of Karnataka?", SUPPORTING_EVIDENCE)
    assert len(result["arguments"]) >= 1
    assert result["defense_strength"] in {"strong", "moderate", "weak", "none"}


def test_agents_still_empty_when_no_evidence():
    assert run_prosecutor("x", [])["arguments"] == []
    assert run_defender("x", [])["arguments"] == []
