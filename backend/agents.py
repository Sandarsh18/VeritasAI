import asyncio
import logging
import os
import re
import sys
from typing import Dict, List, TypedDict

try:
    from langgraph.graph import StateGraph
except Exception:
    StateGraph = None

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "agents")
if AGENTS_DIR not in sys.path:
    sys.path.append(AGENTS_DIR)

from claim_analyzer import analyze_claim
from defender import run_defender
from judge import run_judge
from prosecutor import run_prosecutor
from rag.retriever import retrieve_evidence

# Compatibility bridge: allow imports like `from agents.judge import run_judge`
# while keeping this file as the runtime module used by main.py.
__path__ = [AGENTS_DIR]

LOGGER = logging.getLogger("veritas.graph")


class ClaimState(TypedDict, total=False):
    claim: str
    context: str
    analysis: Dict
    evidence: List[Dict]
    retrieval_meta: Dict
    prosecutor: Dict
    defender: Dict
    judge: Dict
    prosecutor_argument: str
    defender_argument: str
    prosecutor_points: List[str]
    defender_points: List[str]
    prosecutor_strength: str
    defender_strength: str
    verdict: str
    confidence: int
    reasoning: str
    summary: str
    citations: List[str]
    disagreement_score: float


def _clean_points(points: List[str]) -> List[str]:
    cleaned = []
    for point in points or []:
        value = str(point or "").strip()
        if value:
            cleaned.append(value)
    return cleaned


def _normalize_sources(sources: List[Dict]) -> List[Dict]:
    normalized = []
    for row in sources or []:
        url = row.get("url") or row.get("source_url") or row.get("link") or ""
        normalized.append(
            {
                "title": row.get("title", ""),
                "source": row.get("source", "Unknown"),
                "content": row.get("content") or row.get("snippet") or "",
                "url": url,
                "source_url": url,
                "published_date": row.get("published_date") or row.get("date") or "",
                "credibility_score": float(row.get("credibility_score", 0.5) or 0.5),
                "evidence_source": row.get("evidence_source", "api"),
            }
        )
    return normalized


def _citation_urls(evidence: List[Dict]) -> List[str]:
    urls: List[str] = []
    seen = set()
    for row in evidence or []:
        url = (row.get("url") or row.get("source_url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls[:3]


def _analyzer_node(state: ClaimState) -> ClaimState:
    claim = (state.get("claim") or "").strip()
    analysis = analyze_claim(claim)
    LOGGER.info("[Graph] Analyzer claim_type=%s domain=%s", analysis.get("claim_type"), analysis.get("domain"))
    return {"analysis": analysis}


def _retriever_node(state: ClaimState) -> ClaimState:
    claim = state.get("claim", "")
    analysis = state.get("analysis", {})

    if state.get("evidence"):
        LOGGER.info("[Graph] Retriever using preloaded evidence count=%s", len(state.get("evidence", [])))
        return {"evidence": state.get("evidence", []), "retrieval_meta": {"preloaded": True}}

    keywords = analysis.get("key_keywords") or []
    domain = analysis.get("domain") or "general"

    evidence, meta = retrieve_evidence(
        claim=claim,
        keywords=keywords,
        domain=domain,
        top_k=5,
        max_retries=1,
    )

    if not evidence:
        # Mandatory retry when first pass fails.
        evidence, retry_meta = retrieve_evidence(
            claim=claim,
            keywords=keywords,
            domain=domain,
            top_k=5,
            max_retries=2,
        )
        meta = {
            "primary": meta,
            "retry": retry_meta,
        }

    LOGGER.info("[Graph] Retriever evidence_count=%s", len(evidence))
    return {
        "evidence": evidence,
        "retrieval_meta": meta,
    }


def _prosecutor_node(state: ClaimState) -> ClaimState:
    claim = state.get("claim", "")
    evidence = state.get("evidence", [])
    result = run_prosecutor(claim, evidence)
    points = _clean_points(result.get("arguments", []))

    if not points:
        points = ["No specific contradicting evidence found in retrieved sources."]

    strength = str(result.get("prosecution_strength", "none") or "none").lower()
    if strength not in {"strong", "moderate", "weak", "none"}:
        strength = "weak" if points else "none"

    return {
        "prosecutor": {
            **result,
            "arguments": points,
            "prosecution_strength": strength,
        },
        "prosecutor_argument": points[0],
        "prosecutor_points": points,
        "prosecutor_strength": strength,
    }


def _defender_node(state: ClaimState) -> ClaimState:
    claim = state.get("claim", "")
    evidence = state.get("evidence", [])
    result = run_defender(claim, evidence)
    points = _clean_points(result.get("arguments", []))

    if not points:
        points = ["No specific supporting evidence found in retrieved sources."]

    strength = str(result.get("defense_strength", "none") or "none").lower()
    if strength not in {"strong", "moderate", "weak", "none"}:
        strength = "weak" if points else "none"

    return {
        "defender": {
            **result,
            "arguments": points,
            "defense_strength": strength,
        },
        "defender_argument": points[0],
        "defender_points": points,
        "defender_strength": strength,
    }


def _judge_node(state: ClaimState) -> ClaimState:
    claim = state.get("claim", "")
    prosecutor = state.get("prosecutor") or {
        "arguments": state.get("prosecutor_points", []),
        "prosecution_strength": state.get("prosecutor_strength", "none"),
    }
    defender = state.get("defender") or {
        "arguments": state.get("defender_points", []),
        "defense_strength": state.get("defender_strength", "none"),
    }
    evidence = state.get("evidence", [])

    result = run_judge(claim, prosecutor, defender, evidence)
    verdict = str(result.get("verdict", "UNVERIFIED")).upper()

    try:
        confidence = int(float(result.get("confidence", 43)))
    except Exception:
        confidence = 43

    confidence = max(36, min(95, 63 if confidence == 50 else confidence))
    reasoning = str(result.get("reasoning", "")).strip() or "Insufficient evidence for a definitive verdict."

    return {
        "judge": result,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "summary": reasoning,
        "citations": _citation_urls(evidence),
    }


def _build_langgraph():
    if StateGraph is None:
        LOGGER.warning("[Graph] LangGraph unavailable, using sequential fallback")
        return None

    graph = StateGraph(ClaimState)
    graph.add_node("claim_analyzer_node", _analyzer_node)
    graph.add_node("retriever_node", _retriever_node)
    graph.add_node("prosecutor_node", _prosecutor_node)
    graph.add_node("defender_node", _defender_node)
    graph.add_node("judge_node", _judge_node)

    graph.set_entry_point("claim_analyzer_node")
    graph.add_edge("claim_analyzer_node", "retriever_node")
    graph.add_edge("retriever_node", "prosecutor_node")
    graph.add_edge("retriever_node", "defender_node")
    graph.add_edge("prosecutor_node", "judge_node")
    graph.add_edge("defender_node", "judge_node")
    graph.set_finish_point("judge_node")

    return graph.compile()


_GRAPH = _build_langgraph()


def _run_sequential(state: ClaimState) -> ClaimState:
    merged: ClaimState = dict(state)
    merged.update(_analyzer_node(merged))
    merged.update(_retriever_node(merged))
    merged.update(_prosecutor_node(merged))
    merged.update(_defender_node(merged))
    merged.update(_judge_node(merged))
    return merged


def calculate_disagreement_score(prosecutor_args: list, defender_args: list) -> float:
    """Score 0.0-1.0 reflecting how contested a claim is."""
    p = min(len(prosecutor_args) if prosecutor_args else 0, 5)
    d = min(len(defender_args) if defender_args else 0, 5)
    if p + d == 0:
        return 0.0
    balance = 1.0 - abs(p - d) / (p + d)
    volume = (p + d) / 10.0
    return round(min(balance * volume, 1.0), 2)


async def decompose_claim(claim: str) -> list:
    """Lightweight decomposition used by main.py compatibility path."""
    text = (claim or "").strip()
    if not text:
        return []

    parts = [
        p.strip(" ,.;")
        for p in re.split(r"\band\b|\bbut\b|\bwhile\b", text, flags=re.IGNORECASE)
        if p.strip(" ,.;")
    ]
    return parts[:3] if parts else [text]


async def run_claim_graph(claim: str, context: str = "", sources: List[Dict] | None = None) -> ClaimState:
    state: ClaimState = {
        "claim": claim,
        "context": context,
    }

    if sources:
        state["evidence"] = _normalize_sources(sources)

    if _GRAPH is not None:
        result: ClaimState = await asyncio.to_thread(_GRAPH.invoke, state)
    else:
        result = _run_sequential(state)

    prosecutor_args = (result.get("prosecutor") or {}).get("arguments") or result.get("prosecutor_points", [])
    defender_args = (result.get("defender") or {}).get("arguments") or result.get("defender_points", [])
    result["disagreement_score"] = calculate_disagreement_score(prosecutor_args, defender_args)

    if not result.get("citations"):
        result["citations"] = _citation_urls(result.get("evidence", []))

    return result
