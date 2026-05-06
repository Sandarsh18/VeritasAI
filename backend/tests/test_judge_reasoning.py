import agents.judge as judge_module


def test_judge_reasoning_is_not_empty_and_references_evidence(monkeypatch):
    evidence = [
        {
            "title": "ITU 6G research report",
            "source": "ITU",
            "content": "The report outlines 6G research milestones.",
            "credibility_score": 0.9,
        }
    ]

    monkeypatch.setattr(judge_module, "call_with_fallback", lambda *args, **kwargs: "{ }")
    monkeypatch.setattr(
        judge_module,
        "extract_json",
        lambda raw: {"verdict": "TRUE", "confidence": 82},
    )

    result = judge_module.run_judge(
        "Is India developing 6G?",
        {"arguments": ["Some evidence"], "prosecution_strength": "weak"},
        {"arguments": ["More evidence"], "defense_strength": "moderate"},
        evidence,
    )

    reasoning = result.get("reasoning", "")
    assert reasoning
    assert "ITU" in reasoning or "6G" in reasoning
