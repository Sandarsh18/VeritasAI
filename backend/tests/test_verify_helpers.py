from main import _judge_review_flags, _validate_verify_payload


def test_judge_review_flags_marks_invalid_verdict_and_confidence():
    flags = _judge_review_flags("MAYBE", 120, "")

    assert bool(flags)
    assert "judge_verdict_invalid" in flags
    assert "judge_confidence_invalid" in flags
    assert "judge_reasoning_missing" in flags


def test_judge_review_flags_empty_for_valid_values():
    flags = _judge_review_flags("TRUE", 77, "Evidence-backed reasoning")

    assert flags == []


def test_validate_verify_payload_rejects_malformed_payload():
    malformed = {
        "claim": "Test claim",
        "verdict": "TRUE",
        "confidence": 88,
        "reasoning": "Missing required fields should fail model validation.",
    }

    validated = _validate_verify_payload(malformed, context="test-malformed")
    assert validated is None


def test_validate_verify_payload_accepts_structured_fields():
    payload = {
        "claim": "Test claim",
        "claim_type": "factual_claim",
        "domain": "technology",
        "sub_claims": ["Test claim"],
        "stages": {"claim": True, "retrieval": True, "agents": True, "verdict": True},
        "verdict": "UNVERIFIED",
        "confidence": 42,
        "disagreement_score": 0.0,
        "reasoning": "Insufficient relevant evidence found to verify this claim.",
        "explanation": "Insufficient relevant evidence found to verify this claim.",
        "reasoning_points": [],
        "verdict_insights": {},
        "final_verdict": {
            "label": "UNVERIFIED",
            "confidence": 42,
            "reasoning": "Insufficient relevant evidence found to verify this claim.",
            "support_count": 0,
            "contradict_count": 0,
        },
        "prosecutor_argument": "N/A",
        "defender_argument": "N/A",
        "prosecutor": {"arguments": []},
        "defender": {"arguments": []},
        "agent_outputs": {"prosecutor": [], "defender": []},
        "prosecutor_evidence": [],
        "defender_evidence": [],
        "citations": [],
        "sources": [],
        "evidence": [],
        "retrieved_docs": [],
        "retrieval_meta": {},
        "pipeline_warning": "",
        "cached": False,
        "cache_hit": False,
        "processing_time_seconds": 0.1,
        "pipeline_metrics": {},
        "cache_schema_version": 5,
        "needs_review": False,
        "review_flags": [],
        "error_flag": False,
    }

    validated = _validate_verify_payload(payload, context="test-structured")
    assert validated is not None
