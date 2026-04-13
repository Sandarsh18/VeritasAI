import re
import os
from urllib.parse import urlparse
from typing import Dict, List, TypedDict
import asyncio
import time

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = None
    StateGraph = None

USE_GEMINI = os.getenv("USE_GEMINI", "false").strip().lower() == "true"

if USE_GEMINI:
    try:
        from gemini_client import gemini_complete
    except Exception:
        gemini_complete = None
else:
    gemini_complete = None

# Compatibility bridge: allow imports like `from agents.judge import run_judge`
# while keeping this file as the runtime module used by main.py.
__path__ = [os.path.join(os.path.dirname(__file__), "agents")]


class ClaimState(TypedDict, total=False):
    claim: str
    context: str
    sources: List[Dict]
    prosecutor_argument: str
    defender_argument: str
    verdict: str
    confidence: int
    citations: List[str]
    prosecutor_points: List[str]
    defender_points: List[str]
    prosecutor_strength: str
    defender_strength: str


def _source_lines(sources: List[Dict]) -> str:
    lines = []
    for item in sources or []:
        title = item.get("title", "")
        link = item.get("link", "")
        lines.append(f"- {title} ({link})")
    return "\n".join(lines)


def _domain(url: str) -> str:
    try:
        netloc = urlparse(url or "").netloc.lower()
        return netloc.replace("www.", "")
    except Exception:
        return ""


def _clean_snippet(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:180]


def _fallback_points(sources: List[Dict], side: str) -> List[str]:
    points: List[str] = []
    for item in sources[:3]:
        title = (item.get("title") or "Untitled source").strip()
        snippet = _clean_snippet(item.get("snippet", ""))
        link = item.get("link", "")
        source_domain = _domain(link) or (item.get("source") or "source")
        lead = "supports" if side == "defender" else "challenges"
        statement = (
            f"{source_domain} {lead} parts of the claim via '{title}'."
            if not snippet
            else f"{source_domain} {lead} parts of the claim: {snippet}"
        )
        if link:
            statement = f"{statement} (Source: {link})"
        points.append(statement)

    if not points:
        points.append("No high-quality sources were retrieved for this side.")
    return points


def _extract_points(raw_text: str) -> List[str]:
    text = (raw_text or "").strip()
    if not text:
        return []

    lines = []
    for chunk in re.split(r"\n+|•|- ", text):
        cleaned = chunk.strip(" \t-•")
        if cleaned:
            lines.append(cleaned)

    if not lines and text:
        lines = [text]
    return lines[:4]


def _sources_to_agent_evidence(sources: List[Dict]) -> List[Dict]:
    evidence: List[Dict] = []
    for row in sources or []:
        link = row.get("link", "")
        domain = (_domain(link) or row.get("source") or "unknown").lower()
        trusted_tokens = ["reuters.com", "bbc.com", "who.int", "thehindu.com", "ndtv.com"]
        credibility = 0.9 if any(token in domain for token in trusted_tokens) else 0.7
        evidence.append(
            {
                "title": row.get("title", ""),
                "source": row.get("source", _domain(link)),
                "source_url": link,
                "content": row.get("snippet", ""),
                "credibility_score": credibility,
            }
        )
    return evidence


async def call_llm_async(prompt: str) -> str:
    """Optional async wrapper for Gemini completion when enabled."""
    if not USE_GEMINI or not gemini_complete:
        return ""
    try:
        return await asyncio.to_thread(gemini_complete, prompt)
    except Exception:
        return ""


async def decompose_claim(claim: str) -> list:
    """Split a compound claim into up to 3 sub-claims using LLM."""
    prompt = f"""Split this claim into individual factual sub-claims (max 3).
Return ONLY a JSON array of strings. No explanation.
If it is a single claim, return a single-element array.
Claim: {claim}
Example output: [\"sub-claim 1\", \"sub-claim 2\"]"""
    try:
        response = await call_llm_async(prompt)
        import json, re
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return [c.strip() for c in result if c.strip()][:3]
    except Exception:
        pass
    return [claim]


async def _prosecutor_node_async(state: ClaimState) -> ClaimState:
    """Async version of prosecutor node."""
    return _prosecutor_node(state)


async def _defender_node_async(state: ClaimState) -> ClaimState:
    """Async version of defender node."""
    return _defender_node(state)


def _prosecutor_node(state: ClaimState) -> ClaimState:
    fallback_points = _fallback_points(state.get("sources", []), side="prosecutor")
    strength = "none"
    try:
        from agents.prosecutor import run_prosecutor

        evidence = _sources_to_agent_evidence(state.get("sources", []))
        result = run_prosecutor(state.get("claim", ""), evidence)
        points = [p for p in (result.get("arguments") or []) if p]
        if not points:
            points = fallback_points
        strength = str(result.get("prosecution_strength", "none")).lower().strip()
    except Exception:
        points = fallback_points
        strength = "moderate" if len(points) >= 2 else "weak"

    if strength not in {"strong", "moderate", "weak", "none"}:
        strength = "moderate" if len(points) >= 3 else "weak" if len(points) >= 1 else "none"

    return {
        "prosecutor_argument": points[0],
        "prosecutor_points": points,
        "prosecutor_strength": strength,
    }


def _defender_node(state: ClaimState) -> ClaimState:
    fallback_points = _fallback_points(state.get("sources", []), side="defender")
    strength = "none"
    try:
        from agents.defender import run_defender

        evidence = _sources_to_agent_evidence(state.get("sources", []))
        result = run_defender(state.get("claim", ""), evidence)
        points = [p for p in (result.get("arguments") or []) if p]
        if not points:
            points = fallback_points
        strength = str(result.get("defense_strength", "none")).lower().strip()
    except Exception:
        points = fallback_points
        strength = "moderate" if len(points) >= 2 else "weak"

    if strength not in {"strong", "moderate", "weak", "none"}:
        strength = "moderate" if len(points) >= 3 else "weak" if len(points) >= 1 else "none"

    return {
        "defender_argument": points[0],
        "defender_points": points,
        "defender_strength": strength,
    }


def _judge_node(state: ClaimState) -> ClaimState:
    claim = state.get("claim", "")
    sources = state.get("sources", []) or []

    prosecutor_points = state.get("prosecutor_points") or _extract_points(
        state.get("prosecutor_argument", "")
    )
    defender_points = state.get("defender_points") or _extract_points(
        state.get("defender_argument", "")
    )

    prosecutor_payload = {
        "arguments": prosecutor_points,
        "prosecution_strength": state.get("prosecutor_strength", "none"),
    }
    defender_payload = {
        "arguments": defender_points,
        "defense_strength": state.get("defender_strength", "none"),
    }

    evidence = []
    for row in sources[:8]:
        evidence.append(
            {
                "title": row.get("title", ""),
                "source": row.get("source", _domain(row.get("link", ""))),
                "source_url": row.get("link", ""),
                "content": row.get("snippet", ""),
                "credibility_score": 0.9 if any(
                    token in (row.get("link", "").lower())
                    for token in ["reuters.com", "bbc.com", "who.int", "thehindu.com", "ndtv.com"]
                ) else 0.7,
            }
        )

    result = {}
    try:
        from agents.judge import run_judge

        result = run_judge(
            claim=claim,
            prosecutor=prosecutor_payload,
            defender=defender_payload,
            evidence=evidence,
        )
    except Exception as exc:
        print(f"[GraphJudge] run_judge import/call failed: {exc}")
        result = {
            "verdict": "UNVERIFIED",
            "confidence": 43,
            "reasoning": "Judge model unavailable, using conservative fallback verdict.",
            "key_evidence": [],
            "prosecutor_strength": prosecutor_payload.get("prosecution_strength", "none"),
            "defender_strength": defender_payload.get("defense_strength", "none"),
            "recommendation": "Check trusted sources for confirmation.",
        }

    verdict = str(result.get("verdict", "UNVERIFIED")).upper()
    if verdict not in {"TRUE", "FALSE", "MISLEADING", "UNVERIFIED"}:
        verdict = "UNVERIFIED"

    confidence = result.get("confidence", 43)
    try:
        confidence = int(confidence)
    except Exception:
        confidence = 43
    if confidence == 50:
        confidence = 58 if verdict == "MISLEADING" else 43
    confidence = max(36, min(97, confidence))

    citations = [
        item.get("link", "")
        for item in sources
        if item.get("link")
    ][:3]

    return {
        "verdict": verdict,
        "confidence": confidence,
        "citations": citations,
        "summary": result.get("reasoning", ""),
        "prosecutor_strength": result.get(
            "prosecutor_strength",
            prosecutor_payload.get("prosecution_strength", "none"),
        ),
        "defender_strength": result.get(
            "defender_strength",
            defender_payload.get("defense_strength", "none"),
        ),
    }


def _calculate_disagreement(state: ClaimState) -> Dict[str, float]:
    """
    Calculates a disagreement score based on the arguments of the prosecutor and defender.
    Score is 0-1, where 1 is high disagreement.
    """
    prosecutor_points = state.get("prosecutor_points", [])
    defender_points = state.get("defender_points", [])
    
    p_len = len(prosecutor_points)
    d_len = len(defender_points)
    
    if p_len == 0 and d_len == 0:
        return {"disagreement_score": 0.0}
        
    # Normalize lengths to be between 0 and 1 (assuming max 4 points)
    p_norm = p_len / 4.0
    d_norm = d_len / 4.0
    
    # Disagreement is high if both are strong, low if one is weak.
    # Using a formula that rewards two high scores.
    # (p_norm * d_norm) gives a good sense of mutual engagement.
    # The additional term boosts the score if they are balanced.
    disagreement = (p_norm * d_norm) + (1.0 - abs(p_norm - d_norm)) / 4.0
    
    return {"disagreement_score": min(1.0, disagreement)}


def calculate_disagreement_score(prosecutor_args: list, defender_args: list) -> float:
    """Score 0.0-1.0 reflecting how contested a claim is."""
    p = min(len(prosecutor_args) if prosecutor_args else 0, 5)
    d = min(len(defender_args) if defender_args else 0, 5)
    if p + d == 0:
        return 0.0
    balance = 1.0 - abs(p - d) / (p + d)
    volume = (p + d) / 10.0
    return round(min(balance * volume, 1.0), 2)


async def _run_parallel(state: ClaimState) -> ClaimState:
    """Runs prosecutor and defender in parallel, then the judge."""
    start_time = time.monotonic()

    prosecutor_task = _prosecutor_node_async(state)
    defender_task = _defender_node_async(state)

    results = await asyncio.gather(prosecutor_task, defender_task)

    merged_state: ClaimState = dict(state)
    for result in results:
        merged_state.update(result)

    judge_result = _judge_node(merged_state)
    merged_state.update(judge_result)
    
    disagreement_result = _calculate_disagreement(merged_state)
    merged_state.update(disagreement_result)

    end_time = time.monotonic()
    print(f"Async agent execution time: {end_time - start_time:.2f} seconds")

    return merged_state


def _run_sequential(state: ClaimState) -> ClaimState:
    merged: ClaimState = dict(state)
    merged.update(_prosecutor_node(merged))
    merged.update(_defender_node(merged))
    merged.update(_judge_node(merged))
    disagreement_result = _calculate_disagreement(merged)
    merged.update(disagreement_result)
    return merged


async def run_claim_graph(claim: str, context: str, sources: List[Dict]) -> ClaimState:
    state: ClaimState = {
        "claim": claim,
        "context": context,
        "sources": sources,
    }

    # Always use parallel execution for this enhancement
    return await _run_parallel(state)
