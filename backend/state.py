"""
state.py — VeritasAI Verification Pipeline State Model

Pydantic-based shared state for LangGraph nodes.
All pipeline stages read/write this state.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field


def merge_unique(left: Optional[List[Any]], right: Optional[List[Any]]) -> List[Any]:
    """LangGraph reducer: append list updates while preserving first-seen order."""
    merged: List[Any] = []
    seen = set()
    for item in list(left or []) + list(right or []):
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def take_latest(left: Optional[Any], right: Optional[Any]) -> Any:
    """LangGraph reducer: keep the newest non-empty scalar update."""
    return right if right not in (None, "") else left


class VerificationState(BaseModel):
    """Strongly typed shared state flowing through every LangGraph node."""

    # ── Core claim ──────────────────────────────────────
    claim: str = ""
    context: str = ""

    # ── Pipeline status ─────────────────────────────────
    pipeline_stage: Annotated[str, take_latest] = "waiting"
    stage: Annotated[str, take_latest] = "pending"
    completed_stages: Annotated[List[str], merge_unique] = Field(default_factory=list)
    errors: Annotated[List[str], merge_unique] = Field(default_factory=list)

    # ── Claim analysis ──────────────────────────────────
    analysis: Dict = Field(default_factory=dict)

    # ── Evidence retrieval ──────────────────────────────
    queries: List[str] = Field(default_factory=list)
    raw_results: List[Dict] = Field(default_factory=list)
    filtered_results: List[Dict] = Field(default_factory=list)
    evidence_sources: List[Dict] = Field(default_factory=list)
    evidence: List[Dict] = Field(default_factory=list)
    retrieval_meta: Dict = Field(default_factory=dict)

    # ── Agent analysis ──────────────────────────────────
    prosecutor: Dict = Field(default_factory=dict)
    defender: Dict = Field(default_factory=dict)
    prosecutor_argument: str = ""
    defender_argument: str = ""
    # Points may be strings from older agents or structured dicts for rich cards.
    prosecutor_points: List[Any] = Field(default_factory=list)
    defender_points: List[Any] = Field(default_factory=list)
    prosecutor_strength: str = "none"
    defender_strength: str = "none"
    prosecutor_analysis: Any = Field(default_factory=dict)
    defender_analysis: Any = Field(default_factory=dict)

    # ── Judge / Verdict ─────────────────────────────────
    judge: Dict = Field(default_factory=dict)
    verdict: str = "UNVERIFIED"
    confidence: float = 0.0
    reasoning: Any = ""
    reasoning_points: List[str] = Field(default_factory=list)
    reasoning_text: str = ""
    summary: str = ""
    citations: List[str] = Field(default_factory=list)
    disagreement_score: float = 0.0
    support_count: int = 0
    contradict_count: int = 0
    contentiousness: str = "Low"

    # ── PDF ─────────────────────────────────────────────
    pdf_path: Optional[str] = None

    # ── Timing ──────────────────────────────────────────
    timing_claim_analysis_ms: float = 0.0
    timing_retrieval_ms: float = 0.0
    timing_filter_ms: float = 0.0
    timing_prosecutor_ms: float = 0.0
    timing_defender_ms: float = 0.0
    timing_judge_ms: float = 0.0

    class Config:
        extra = "allow"  # Accept extra fields from nodes without error
