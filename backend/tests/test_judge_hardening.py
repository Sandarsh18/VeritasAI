"""Task 8.5 — Judge logic hardening rules (logic-only, no network)."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main


def _rows(n, year_text=""):
    return [{"title": f"src {i} {year_text}", "snippet": year_text, "link": f"http://e/{i}"} for i in range(n)]


def test_rule1_true_without_support_becomes_misleading_or_unverified():
    out = main._harden_verdict(
        "TRUE", 70, supportive_rows=[], contradictory_rows=_rows(4),
        prosecutor_strength="strong", defender_strength="strong",
        year_info={"mismatch": False, "year_match_score": 1.0, "nearest_gap": 0},
    )
    assert out["verdict"] in {"MISLEADING", "UNVERIFIED"}
    assert "rule1_true_without_support" in out["flags"]


def test_rule2_strong_vs_strong_balanced_becomes_misleading():
    out = main._harden_verdict(
        "TRUE", 80, supportive_rows=_rows(3), contradictory_rows=_rows(3),
        prosecutor_strength="strong", defender_strength="strong",
        year_info={"mismatch": False, "year_match_score": 1.0, "nearest_gap": 0},
    )
    assert out["verdict"] == "MISLEADING"
    assert "rule2_strong_vs_strong" in out["flags"]


def test_rule2_overwhelming_one_side_keeps_verdict():
    # 5 supporting vs 1 contradicting => overwhelming, TRUE may stand.
    out = main._harden_verdict(
        "TRUE", 85, supportive_rows=_rows(5), contradictory_rows=_rows(1),
        prosecutor_strength="strong", defender_strength="strong",
        year_info={"mismatch": False, "year_match_score": 1.0, "nearest_gap": 0},
    )
    assert out["verdict"] == "TRUE"


def test_rule3_year_mismatch_downgrades_and_warns():
    yi = main._compute_year_match("Did NEET 2026 paper leak?", _rows(3, "NEET 2024 leak"))
    assert yi["mismatch"] is True
    assert yi["year_match_score"] < 1.0
    out = main._harden_verdict(
        "TRUE", 80, supportive_rows=_rows(2, "2024"), contradictory_rows=_rows(2, "2024"),
        prosecutor_strength="moderate", defender_strength="moderate",
        year_info=yi,
    )
    assert "rule3_year_mismatch" in out["flags"]
    assert "different time period" in out["reasoning_suffix"]
    assert out["confidence"] < 80


def test_rule2b_balanced_split_becomes_misleading():
    out = main._harden_verdict(
        "TRUE", 60, supportive_rows=_rows(3), contradictory_rows=_rows(3),
        prosecutor_strength="strong", defender_strength="moderate",
        year_info={"mismatch": False, "year_match_score": 1.0, "nearest_gap": 0},
    )
    assert out["verdict"] == "MISLEADING"
    assert "rule2b_balanced_split" in out["flags"]


def test_rule2b_does_not_fire_on_uneven_split():
    out = main._harden_verdict(
        "FALSE", 80, supportive_rows=_rows(1), contradictory_rows=_rows(5),
        prosecutor_strength="strong", defender_strength="weak",
        year_info={"mismatch": False, "year_match_score": 1.0, "nearest_gap": 0},
    )
    assert out["verdict"] == "FALSE"


def test_rule4_no_placeholder_50():
    out = main._harden_verdict(
        "UNVERIFIED", 50, supportive_rows=_rows(1), contradictory_rows=_rows(1),
        prosecutor_strength="weak", defender_strength="weak",
        year_info={"mismatch": False, "year_match_score": 1.0, "nearest_gap": 0},
    )
    assert out["confidence"] != 50
    assert "rule4_placeholder_50_remapped" in out["flags"]


def test_year_match_no_year_in_claim_is_full_score():
    yi = main._compute_year_match("Did humans land on the moon?", _rows(3, "Apollo 1969"))
    assert yi["year_match_score"] == 1.0
    assert yi["mismatch"] is False


def test_year_match_exact_match():
    yi = main._compute_year_match("Did NEET 2024 paper leak?", _rows(3, "NEET 2024 leak confirmed"))
    assert yi["mismatch"] is False
    assert yi["year_match_score"] == 1.0
