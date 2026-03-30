import re
from urllib.parse import urlparse
from typing import Dict, List, TypedDict

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = None
    StateGraph = None

from gemini_client import gemini_complete_json


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


def _prosecutor_node(state: ClaimState) -> ClaimState:
    prompt = f'''Given the claim and evidence, argue why the claim is false. Use citations.

Claim: {state.get("claim", "")}

Evidence Context:
{state.get("context", "")}

Sources:
{_source_lines(state.get("sources", []))}

Return strict JSON:
{{
  "prosecutor_argument": "short paragraph with citations like [1], [2]"
}}'''
    fallback_points = _fallback_points(state.get("sources", []), side="prosecutor")
    try:
        result = gemini_complete_json(prompt)
        argument = result.get("prosecutor_argument", "")
        points = _extract_points(argument) or fallback_points
    except Exception:
        points = fallback_points

    return {
        "prosecutor_argument": points[0],
        "prosecutor_points": points,
        "prosecutor_strength": "moderate" if len(points) >= 2 else "weak",
    }


def _defender_node(state: ClaimState) -> ClaimState:
    prompt = f'''Given the claim and evidence, argue why the claim might be true. Use citations.

Claim: {state.get("claim", "")}

Evidence Context:
{state.get("context", "")}

Sources:
{_source_lines(state.get("sources", []))}

Return strict JSON:
{{
  "defender_argument": "short paragraph with citations like [1], [2]"
}}'''
    fallback_points = _fallback_points(state.get("sources", []), side="defender")
    try:
        result = gemini_complete_json(prompt)
        argument = result.get("defender_argument", "")
        points = _extract_points(argument) or fallback_points
    except Exception:
        points = fallback_points

    return {
        "defender_argument": points[0],
        "defender_points": points,
        "defender_strength": "moderate" if len(points) >= 2 else "weak",
    }


def _judge_node(state: ClaimState) -> ClaimState:
    prompt = f'''Evaluate both sides and provide final verdict (True/False/Misleading), confidence score, and list of cited sources.

Claim: {state.get("claim", "")}

Prosecutor:
{state.get("prosecutor_argument", "")}

Defender:
{state.get("defender_argument", "")}

Evidence Context:
{state.get("context", "")}

Sources:
{_source_lines(state.get("sources", []))}

Rules:
- Never return without citations.
- Use only provided sources.
- Confidence must be an integer 0-100.

Return strict JSON:
{{
  "verdict": "TRUE|FALSE|MISLEADING",
  "confidence": 0,
  "citations": ["url1", "url2"],
  "summary": "one-paragraph rationale with citations"
}}'''

    try:
        result = gemini_complete_json(prompt)
    except Exception:
        result = {}

    verdict = str(result.get("verdict", "MISLEADING")).upper()
    if verdict not in {"TRUE", "FALSE", "MISLEADING"}:
        verdict = "MISLEADING"

    confidence = result.get("confidence", 50)
    try:
        confidence = int(confidence)
    except Exception:
        confidence = 50
    confidence = max(0, min(100, confidence))

    citations = result.get("citations") or []
    citations = [str(c) for c in citations if str(c).strip()]
    if not citations:
        citations = [item.get("link", "") for item in (state.get("sources") or []) if item.get("link")][:3]

    return {
        "verdict": verdict,
        "confidence": confidence,
        "citations": citations,
    }


def _run_sequential(state: ClaimState) -> ClaimState:
    merged: ClaimState = dict(state)
    merged.update(_prosecutor_node(merged))
    merged.update(_defender_node(merged))
    merged.update(_judge_node(merged))
    return merged


def run_claim_graph(claim: str, context: str, sources: List[Dict]) -> ClaimState:
    state: ClaimState = {
        "claim": claim,
        "context": context,
        "sources": sources,
    }

    if StateGraph is None or END is None:
        return _run_sequential(state)

    try:
        graph = StateGraph(ClaimState)
        graph.add_node("prosecutor", _prosecutor_node)
        graph.add_node("defender", _defender_node)
        graph.add_node("judge", _judge_node)

        graph.set_entry_point("prosecutor")
        graph.add_edge("prosecutor", "defender")
        graph.add_edge("defender", "judge")
        graph.add_edge("judge", END)

        compiled = graph.compile()
        return compiled.invoke(state)
    except Exception:
        return _run_sequential(state)
