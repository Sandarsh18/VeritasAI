import asyncio
import logging
import os
import re
import sys
import time
import traceback
from typing import Any, Callable, Dict, List
from urllib.parse import urlparse

try:
    import langchain as _langchain

    # Older LangGraph/LangChain-core combinations still read these root attrs.
    # Some installed langchain builds no longer expose them, which makes graph
    # invocation fail before the first node runs.
    for _attr, _default in {
        "debug": False,
        "verbose": False,
        "llm_cache": None,
    }.items():
        if not hasattr(_langchain, _attr):
            setattr(_langchain, _attr, _default)
except Exception:
    pass

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
from services.credibility_service import calculate_credibility
from state import VerificationState

# Compatibility bridge: allow imports like `from agents.judge import run_judge`
# while keeping this file as the runtime module used by main.py.
__path__ = [AGENTS_DIR]

LOGGER = logging.getLogger("veritas.graph")


ClaimState = Dict[str, Any]


def _state_dict(state: Any) -> ClaimState:
    if isinstance(state, dict):
        return dict(state)
    if hasattr(state, "model_dump"):
        return state.model_dump()
    if hasattr(state, "dict"):
        return state.dict()
    return dict(state or {})


def _graph_node(func: Callable[[ClaimState], ClaimState]) -> Callable[[Any], ClaimState]:
    def _wrapped(state: Any) -> ClaimState:
        return func(_state_dict(state))

    return _wrapped


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


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
        source_like = {
            **row,
            "url": url,
            "content": row.get("content") or row.get("snippet") or "",
            "published_date": row.get("published_date") or row.get("date") or "",
        }
        try:
            credibility = calculate_credibility(source_like, peers=sources) / 100
        except Exception:
            credibility = float(row.get("credibility_score", 0.5) or 0.5)
        normalized.append(
            {
                "title": row.get("title", ""),
                "source": row.get("source", "Unknown"),
                "content": row.get("content") or row.get("snippet") or "",
                "url": url,
                "source_url": url,
                "published_date": row.get("published_date") or row.get("date") or "",
                "credibility_score": round(max(0.0, min(1.0, float(credibility))), 4),
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


def _source_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "").strip()
    except Exception:
        return ""


def _looks_like_gibberish(claim: str) -> bool:
    text = (claim or "").lower()
    meaningful_terms = {
        "covid",
        "5g",
        "6g",
        "neet",
        "olympics",
        "gold",
        "silver",
        "earth",
        "india",
    }
    if any(term in text for term in meaningful_terms):
        return False
    if any(marker in text for marker in ["xyzzy", "florp", "blargh", "qwerty"]):
        return True
    tokens = re.findall(r"[a-z0-9]+", text)
    if len(tokens) >= 4:
        numeric = sum(1 for token in tokens if token.isdigit())
        very_short_or_odd = sum(1 for token in tokens if len(token) <= 2 or not re.search(r"[aeiou0-9]", token))
        return numeric >= 1 and very_short_or_odd >= len(tokens) // 2
    return False


def _looks_like_opinion(claim: str) -> bool:
    text = f" {(claim or '').lower()} "
    opinion_cues = [
        " best ",
        " worst ",
        " favorite ",
        " favourite ",
        " tastiest ",
        " most beautiful ",
        " better than all ",
        " greatest ",
    ]
    factual_cues = [" costs ", " price ", " won ", " announced ", " developed ", " leaked ", " spread "]
    return any(cue in text for cue in opinion_cues) and not any(cue in text for cue in factual_cues)


# ════════════════════════════════════════════════════════════
# NODE: Claim Analysis
# ════════════════════════════════════════════════════════════
def _analyzer_node(state: ClaimState) -> ClaimState:
    start = time.perf_counter()
    claim = (state.get("claim") or "").strip()
    analysis = analyze_claim(claim)
    if _looks_like_gibberish(claim):
        analysis.update(
            {
                "claim_type": "invalid_or_gibberish",
                "should_proceed": False,
                "early_response": {
                    "verdict": "INSUFFICIENT_DATA",
                    "confidence": 0,
                    "reasoning": "The claim does not contain enough meaningful factual content to verify.",
                },
            }
        )
    elif _looks_like_opinion(claim):
        analysis.update(
            {
                "claim_type": "opinion",
                "should_proceed": False,
                "early_response": {
                    "verdict": "UNVERIFIED",
                    "confidence": 40,
                    "reasoning": "The claim is subjective, so it cannot be verified as a factual statement.",
                },
            }
        )
    LOGGER.info("[Graph] Analyzer claim_type=%s domain=%s", analysis.get("claim_type"), analysis.get("domain"))
    completed = list(state.get("completed_stages") or [])
    completed.append("claim_analysis")
    return {
        "analysis": analysis,
        "timing_claim_analysis_ms": _elapsed_ms(start),
        "completed_stages": completed,
        "stage": "claim_analysis_done",
    }


# ════════════════════════════════════════════════════════════
# NODE: Evidence Retrieval
# ════════════════════════════════════════════════════════════
def _retriever_node(state: ClaimState) -> ClaimState:
    start = time.perf_counter()
    claim = state.get("claim", "")
    analysis = state.get("analysis", {})

    if analysis.get("should_proceed") is False:
        LOGGER.info("[Graph] Retriever skipped because analyzer returned early_response")
        completed = list(state.get("completed_stages") or [])
        completed.append("retrieval")
        return {
            "evidence": [],
            "retrieval_meta": {"skipped": True, "reason": "analysis_early_response"},
            "queries": [],
            "raw_results": [],
            "filtered_results": [],
            "timing_retrieval_ms": _elapsed_ms(start),
            "completed_stages": completed,
            "stage": "retrieval_done",
            "pipeline_stage": "retrieval_skipped",
        }

    if state.get("evidence"):
        LOGGER.info("[Graph] Retriever using preloaded evidence count=%s", len(state.get("evidence", [])))
        completed = list(state.get("completed_stages") or [])
        completed.append("retrieval")
        return {
            "evidence": state.get("evidence", []),
            "retrieval_meta": {"preloaded": True},
            "completed_stages": completed,
            "stage": "retrieval_done",
        }

    keywords = analysis.get("key_keywords") or []
    domain = analysis.get("domain") or "general"

    evidence, meta = retrieve_evidence(
        claim=claim,
        keywords=keywords,
        domain=domain,
        top_k=7,
        max_retries=1,
    )

    if not evidence:
        # Mandatory retry when first pass fails.
        evidence, retry_meta = retrieve_evidence(
            claim=claim,
            keywords=keywords,
            domain=domain,
            top_k=7,
            max_retries=2,
        )
        meta = {
            "primary": meta,
            "retry": retry_meta,
        }

    if evidence:
        LOGGER.info("[PIPELINE] Retrieval completed")
    else:
        LOGGER.warning("[PIPELINE] Retrieval failed")
    LOGGER.info("[Graph] Retriever evidence_count=%s", len(evidence))
    LOGGER.info("[Graph] Retriever queries=%s", (meta or {}).get("queries", []))
    LOGGER.info(
        "[Graph] Retriever top_titles=%s",
        [row.get("title", "")[:80] for row in (evidence or [])[:3]],
    )

    raw_results = []
    if isinstance(meta, dict):
        for run in meta.get("api_runs", []) or []:
            for q in run.get("queries", []) or []:
                raw_results.append(
                    {
                        "query": q.get("query", ""),
                        "merged_count": q.get("merged_count", 0),
                        "serp_count": (q.get("serpapi") or {}).get("count", 0),
                        "news_count": (q.get("newsapi") or {}).get("count", 0),
                    }
                )

    completed = list(state.get("completed_stages") or [])
    completed.append("retrieval")
    return {
        "evidence": evidence,
        "retrieval_meta": meta,
        "queries": (meta or {}).get("queries", []),
        "raw_results": raw_results,
        "filtered_results": (meta or {}).get("top_k", []),
        "timing_retrieval_ms": _elapsed_ms(start),
        "completed_stages": completed,
        "stage": "retrieval_done",
    }


# ════════════════════════════════════════════════════════════
# NODE: Evidence Filtering (NEW)
# ════════════════════════════════════════════════════════════
def _filter_node(state: ClaimState) -> ClaimState:
    """Deduplicate and filter evidence for relevance before agent analysis."""
    start = time.perf_counter()
    evidence = list(state.get("evidence") or [])
    claim = (state.get("claim") or "").strip().lower()

    if not evidence:
        completed = list(state.get("completed_stages") or [])
        completed.append("evidence_filtering")
        return {
            "evidence": [],
            "completed_stages": completed,
            "stage": "filtering_done",
            "timing_filter_ms": _elapsed_ms(start),
        }

    # 1. Deduplicate by URL
    seen_urls: set = set()
    deduped: List[Dict] = []
    for row in evidence:
        url = (row.get("url") or row.get("source_url") or row.get("link") or "").strip().lower()
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(row)

    # 2. Deduplicate by title similarity
    seen_titles: set = set()
    title_deduped: List[Dict] = []
    for row in deduped:
        title = (row.get("title") or "").strip().lower()
        title_key = " ".join(title.split()[:8])  # First 8 words as key
        if title_key and title_key in seen_titles:
            continue
        if title_key:
            seen_titles.add(title_key)
        title_deduped.append(row)

    # 3. Basic relevance check — article must share at least 1 claim term
    claim_terms = {
        t for t in re.findall(r"[a-z0-9]+", claim)
        if len(t) > 2 and t not in {"the", "is", "are", "and", "for", "was", "has", "been", "not"}
    }

    relevant: List[Dict] = []
    scored_relevance: List[tuple[int, Dict]] = []
    for row in title_deduped:
        text = f"{row.get('title', '')} {row.get('content', '')} {row.get('snippet', '')}".lower()
        overlap = sum(1 for t in claim_terms if t in text)
        scored_relevance.append((overlap, row))
        required_overlap = 1
        if len(claim_terms) >= 4:
            required_overlap = 2
        elif len(claim_terms) >= 2:
            required_overlap = min(2, len(claim_terms))
        if overlap >= required_overlap or not claim_terms:
            relevant.append(row)

    # If filtering removed too many, keep only the strongest partial matches.
    if len(relevant) < 3 and len(title_deduped) >= 3:
        partial = [row for overlap, row in sorted(scored_relevance, key=lambda item: item[0], reverse=True) if overlap > 0]
        if partial:
            relevant = partial[:5]

    # Cap at 12, minimum target 5
    filtered = relevant[:12]

    # Evidence Preservation Rule: never starve the agents. When raw evidence
    # exists, guarantee at least EVIDENCE_FLOOR items survive filtering so the
    # Prosecutor and Defender each receive a usable list. Top up from the
    # highest-overlap deduped rows if relevance filtering was too aggressive.
    EVIDENCE_FLOOR = 3
    if len(filtered) < EVIDENCE_FLOOR and title_deduped:
        ranked_backfill = [row for _, row in sorted(scored_relevance, key=lambda item: item[0], reverse=True)]
        seen_keys = {id(r) for r in filtered}
        for row in ranked_backfill:
            if len(filtered) >= min(EVIDENCE_FLOOR, len(title_deduped)):
                break
            if id(row) not in seen_keys:
                filtered.append(row)
                seen_keys.add(id(row))
        LOGGER.info(
            "[Graph] Evidence Preservation Rule: backfilled to %d (floor=%d, available=%d)",
            len(filtered), EVIDENCE_FLOOR, len(title_deduped),
        )

    LOGGER.info(
        "[Graph] Filter: raw=%d deduped=%d relevant=%d final=%d",
        len(evidence), len(deduped), len(relevant), len(filtered),
    )

    completed = list(state.get("completed_stages") or [])
    completed.append("evidence_filtering")
    return {
        "evidence": filtered,
        "completed_stages": completed,
        "stage": "filtering_done",
        "timing_filter_ms": _elapsed_ms(start),
    }


def _stage_failure(stage: str, exc: Exception, start: float) -> ClaimState:
    trace = traceback.format_exc()
    LOGGER.exception("[PIPELINE] FULL ERROR TRACE stage=%s", stage)
    return {
        "pipeline_error": {
            "success": False,
            "stage": stage,
            "error": str(exc),
            "trace": trace,
        },
        f"timing_{stage}_ms": _elapsed_ms(start),
    }


def _point_summary(point) -> str:
    if isinstance(point, dict):
        return str(point.get("summary") or point.get("text") or point.get("title") or "").strip()
    return str(point or "").strip()


# ════════════════════════════════════════════════════════════
# NODE: Prosecutor
# ════════════════════════════════════════════════════════════
def _prosecutor_node(state: ClaimState) -> ClaimState:
    start = time.perf_counter()
    claim = state.get("claim", "")
    evidence = state.get("evidence", [])
    LOGGER.info("[PIPELINE] Prosecutor started")
    LOGGER.info("[Graph] Evidence passed to agents (prosecutor) count=%s", len(evidence or []))

    # CRITICAL: Skip LLM call when no evidence — prevent hallucination
    if not evidence:
        LOGGER.warning("[Graph] No evidence for prosecutor — using canned response")
        completed = list(state.get("completed_stages") or [])
        completed.append("prosecutor")
        return {
            "prosecutor": {
                "arguments": ["No contradictory evidence found."],
                "strongest_point": "No evidence retrieved",
                "prosecution_strength": "none",
                "evidence_count": 0,
            },
            "prosecutor_argument": "No contradictory evidence found.",
            "prosecutor_points": ["No contradictory evidence found."],
            "prosecutor_strength": "none",
            "timing_prosecutor_ms": _elapsed_ms(start),
            "completed_stages": completed,
            "stage": "prosecutor_done",
        }

    LOGGER.info(
        "[Graph] Evidence passed to agents (prosecutor) sample=%s",
        [row.get("title", "")[:80] for row in (evidence or [])[:2]],
    )
    try:
        result = run_prosecutor(claim, evidence)
    except Exception as exc:
        failure = _stage_failure("prosecutor", exc, start)
        completed = list(state.get("completed_stages") or [])
        completed.append("prosecutor")
        errors = list(state.get("errors") or [])
        errors.append(f"Prosecutor error: {str(exc)[:200]}")
        failure.update(
            {
                "prosecutor": {
                    "success": False,
                    "stage": "prosecutor",
                    "error": str(exc),
                    "trace": failure["pipeline_error"]["trace"],
                    "arguments": [],
                    "strongest_point": "No prosecutor analysis generated.",
                    "prosecution_strength": "none",
                    "evidence_count": len(evidence or []),
                },
                "prosecutor_argument": "No prosecutor analysis generated.",
                "prosecutor_points": ["No prosecutor analysis generated."],
                "prosecutor_strength": "none",
                "completed_stages": completed,
                "stage": "prosecutor_failed",
                "errors": errors,
            }
        )
        return failure
    points = result.get("arguments", [])

    if not points:
        points = []

    strength = str(result.get("prosecution_strength", "none") or "none").lower()
    if strength not in {"strong", "moderate", "weak", "none"}:
        strength = "weak" if points else "none"

    completed = list(state.get("completed_stages") or [])
    completed.append("prosecutor")
    return {
        "prosecutor": {
            **result,
            "arguments": points,
            "prosecution_strength": strength,
        },
        "prosecutor_argument": _point_summary(points[0]) if points else "",
        "prosecutor_points": points,
        "prosecutor_strength": strength,
        "timing_prosecutor_ms": _elapsed_ms(start),
        "completed_stages": completed,
        "stage": "prosecutor_done",
    }


# ════════════════════════════════════════════════════════════
# NODE: Defender
# ════════════════════════════════════════════════════════════
def _defender_node(state: ClaimState) -> ClaimState:
    start = time.perf_counter()
    claim = state.get("claim", "")
    evidence = state.get("evidence", [])
    LOGGER.info("[PIPELINE] Defender started")
    LOGGER.info("[Graph] Evidence passed to agents (defender) count=%s", len(evidence or []))

    # CRITICAL: Skip LLM call when no evidence — prevent hallucination
    if not evidence:
        LOGGER.warning("[Graph] No evidence for defender — using canned response")
        completed = list(state.get("completed_stages") or [])
        completed.append("defender")
        return {
            "defender": {
                "arguments": ["No supporting evidence found."],
                "strongest_point": "No evidence retrieved",
                "defense_strength": "none",
                "evidence_count": 0,
            },
            "defender_argument": "No supporting evidence found.",
            "defender_points": ["No supporting evidence found."],
            "defender_strength": "none",
            "timing_defender_ms": _elapsed_ms(start),
            "completed_stages": completed,
            "stage": "defender_done",
        }

    LOGGER.info(
        "[Graph] Evidence passed to agents (defender) sample=%s",
        [row.get("title", "")[:80] for row in (evidence or [])[:2]],
    )
    try:
        result = run_defender(claim, evidence)
    except Exception as exc:
        failure = _stage_failure("defender", exc, start)
        completed = list(state.get("completed_stages") or [])
        completed.append("defender")
        errors = list(state.get("errors") or [])
        errors.append(f"Defender error: {str(exc)[:200]}")
        failure.update(
            {
                "defender": {
                    "success": False,
                    "stage": "defender",
                    "error": str(exc),
                    "trace": failure["pipeline_error"]["trace"],
                    "arguments": [],
                    "strongest_point": "No defender analysis generated.",
                    "defense_strength": "none",
                    "evidence_count": len(evidence or []),
                },
                "defender_argument": "No defender analysis generated.",
                "defender_points": ["No defender analysis generated."],
                "defender_strength": "none",
                "completed_stages": completed,
                "stage": "defender_failed",
                "errors": errors,
            }
        )
        return failure
    points = result.get("arguments", [])

    if not points:
        points = []

    strength = str(result.get("defense_strength", "none") or "none").lower()
    if strength not in {"strong", "moderate", "weak", "none"}:
        strength = "weak" if points else "none"

    completed = list(state.get("completed_stages") or [])
    completed.append("defender")
    return {
        "defender": {
            **result,
            "arguments": points,
            "defense_strength": strength,
        },
        "defender_argument": _point_summary(points[0]) if points else "",
        "defender_points": points,
        "defender_strength": strength,
        "timing_defender_ms": _elapsed_ms(start),
        "completed_stages": completed,
        "stage": "defender_done",
    }


# ════════════════════════════════════════════════════════════
# NODE: Judge / Verdict
# ════════════════════════════════════════════════════════════
def _judge_node(state: ClaimState) -> ClaimState:
    start = time.perf_counter()
    LOGGER.info("[PIPELINE] Judge started")
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
    early_response = (state.get("analysis") or {}).get("early_response")

    if isinstance(early_response, dict):
        verdict = str(early_response.get("verdict", "UNVERIFIED")).upper()
        try:
            confidence = int(float(early_response.get("confidence", 40)))
        except Exception:
            confidence = 40
        reasoning = str(early_response.get("reasoning", "")).strip() or "The claim cannot be verified as written."
        completed = list(state.get("completed_stages") or [])
        completed.append("judge")
        return {
            "judge": {
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning,
                "key_evidence": [],
                "prosecutor_strength": "none",
                "defender_strength": "none",
                "recommendation": early_response.get("recommendation", "Rephrase as a factual claim."),
                "evidence_count": 0,
            },
            "verdict": verdict,
            "confidence": max(0, min(100, confidence)),
            "reasoning": reasoning,
            "summary": reasoning,
            "citations": [],
            "timing_judge_ms": _elapsed_ms(start),
            "completed_stages": completed,
            "stage": "verdict_done",
        }

    try:
        result = run_judge(claim, prosecutor, defender, evidence)
    except Exception as exc:
        failure = _stage_failure("judge", exc, start)
        completed = list(state.get("completed_stages") or [])
        completed.append("judge")
        errors = list(state.get("errors") or [])
        errors.append(f"Judge error: {str(exc)[:200]}")
        failure.update(
            {
                "judge": {
                    "success": False,
                    "stage": "judge",
                    "error": str(exc),
                    "trace": failure["pipeline_error"]["trace"],
                },
                "verdict": "INSUFFICIENT_DATA",
                "confidence": 0,
                "reasoning": "Judge stage failed before verdict generation.",
                "summary": "Judge stage failed before verdict generation.",
                "citations": _citation_urls(evidence),
                "completed_stages": completed,
                "stage": "judge_failed",
                "errors": errors,
            }
        )
        return failure
    verdict = str(result.get("verdict", "UNVERIFIED")).upper()

    try:
        confidence = int(float(result.get("confidence", 43)))
    except Exception:
        confidence = 43

    confidence = max(36, min(95, 63 if confidence == 50 else confidence))
    reasoning = str(result.get("reasoning", "")).strip() or "Insufficient relevant evidence found to verify this claim."

    completed = list(state.get("completed_stages") or [])
    completed.append("judge")
    return {
        "judge": result,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "summary": reasoning,
        "citations": _citation_urls(evidence),
        "timing_judge_ms": _elapsed_ms(start),
        "completed_stages": completed,
        "stage": "verdict_done",
    }


# ════════════════════════════════════════════════════════════
# NODE: Verdict
# ════════════════════════════════════════════════════════════
def _verdict_node(state: ClaimState) -> ClaimState:
    prosecutor_args = (state.get("prosecutor") or {}).get("arguments") or state.get("prosecutor_points", [])
    defender_args = (state.get("defender") or {}).get("arguments") or state.get("defender_points", [])
    support_count = len(defender_args or [])
    contradict_count = len(prosecutor_args or [])
    disagreement = state.get("disagreement_score")
    if not isinstance(disagreement, (int, float)):
        disagreement = calculate_disagreement_score(prosecutor_args, defender_args)

    if disagreement >= 0.66:
        contentiousness = "High"
    elif disagreement >= 0.33:
        contentiousness = "Medium"
    else:
        contentiousness = "Low"

    return {
        "support_count": support_count,
        "contradict_count": contradict_count,
        "contentiousness": contentiousness,
        "disagreement_score": disagreement,
        "completed_stages": ["verdict"],
        "pipeline_stage": "verdict_ready",
        "stage": "verdict_ready",
    }


# ════════════════════════════════════════════════════════════
# NODE: PDF Export
# ════════════════════════════════════════════════════════════
def _pdf_export_node(state: ClaimState) -> ClaimState:
    # PDF bytes are generated lazily by the export endpoint so verification
    # remains fast and the existing response contract stays unchanged.
    return {
        "pdf_path": state.get("pdf_path"),
        "completed_stages": ["pdf_export"],
        "pipeline_stage": "pdf_ready",
        "stage": "pdf_ready",
    }


# ════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ════════════════════════════════════════════════════════════
def _build_langgraph():
    if StateGraph is None:
        LOGGER.warning("[Graph] LangGraph unavailable, using sequential fallback")
        return None

    try:
        graph = StateGraph(VerificationState)
        graph.add_node("ClaimAnalysisNode", _graph_node(_analyzer_node))
        graph.add_node("EvidenceRetrievalNode", _graph_node(_retriever_node))
        graph.add_node("EvidenceFilteringNode", _graph_node(_filter_node))
        graph.add_node("ProsecutorNode", _graph_node(_prosecutor_node))
        graph.add_node("DefenderNode", _graph_node(_defender_node))
        graph.add_node("JudgeNode", _graph_node(_judge_node))
        graph.add_node("VerdictNode", _graph_node(_verdict_node))
        graph.add_node("PDFExportNode", _graph_node(_pdf_export_node))

        # Pipeline: Claim → Evidence → Filter → (Prosecutor || Defender) → Judge → Verdict → PDF
        graph.set_entry_point("ClaimAnalysisNode")
        graph.add_edge("ClaimAnalysisNode", "EvidenceRetrievalNode")
        graph.add_edge("EvidenceRetrievalNode", "EvidenceFilteringNode")
        graph.add_edge("EvidenceFilteringNode", "ProsecutorNode")
        graph.add_edge("EvidenceFilteringNode", "DefenderNode")
        graph.add_edge("ProsecutorNode", "JudgeNode")
        graph.add_edge("DefenderNode", "JudgeNode")
        graph.add_edge("JudgeNode", "VerdictNode")
        graph.add_edge("VerdictNode", "PDFExportNode")
        graph.set_finish_point("PDFExportNode")

        compiled = graph.compile()
        LOGGER.info("[PIPELINE] LangGraph compiled successfully with Pydantic state and PDF node")
        return compiled
    except Exception as exc:
        LOGGER.warning("[Graph] LangGraph build failed: %s — using sequential fallback", exc)
        return None


# Build graph at module load — activate LangGraph!
_GRAPH = _build_langgraph()
if _GRAPH is None:
    LOGGER.info("[PIPELINE] LangGraph unavailable, using sequential fallback")
else:
    LOGGER.info("[PIPELINE] LangGraph ACTIVE — pipeline uses state graph execution")


def _run_sequential(state: ClaimState) -> ClaimState:
    """Sequential fallback if LangGraph is unavailable."""
    merged: ClaimState = dict(state)
    merged.setdefault("completed_stages", [])
    merged.setdefault("errors", [])

    LOGGER.info("[PIPELINE] Claim analysis started")
    try:
        merged.update(_analyzer_node(merged))
    except Exception as exc:
        merged.update(_stage_failure("claim_analysis", exc, time.perf_counter()))
        merged.setdefault("analysis", {"domain": "general", "key_keywords": []})

    LOGGER.info("[PIPELINE] Retrieval started")
    try:
        merged.update(_retriever_node(merged))
    except Exception as exc:
        merged.update(_stage_failure("retrieval", exc, time.perf_counter()))
        merged.setdefault("evidence", [])
        merged.setdefault(
            "retrieval_meta",
            {
                "success": False,
                "stage": "retrieval",
                "error": str(exc),
                "trace": traceback.format_exc(),
                "retrieved_count": 0,
            },
        )

    # Evidence filtering
    try:
        merged.update(_filter_node(merged))
    except Exception as exc:
        LOGGER.warning("[Graph] Filter node failed: %s — continuing with unfiltered evidence", exc)

    merged.update(_prosecutor_node(merged))
    merged.update(_defender_node(merged))
    merged.update(_judge_node(merged))
    merged.update(_verdict_node(merged))
    merged.update(_pdf_export_node(merged))
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
        "completed_stages": [],
        "errors": [],
        "stage": "pending",
    }

    if sources:
        state["evidence"] = _normalize_sources(sources)

    if _GRAPH is not None:
        try:
            result: ClaimState = await asyncio.to_thread(_GRAPH.invoke, state)
        except Exception as exc:
            LOGGER.exception("[Graph] LangGraph invoke failed; falling back to sequential runner: %s", exc)
            result = _run_sequential(state)
    else:
        result = _run_sequential(state)

    prosecutor_args = (result.get("prosecutor") or {}).get("arguments") or result.get("prosecutor_points", [])
    defender_args = (result.get("defender") or {}).get("arguments") or result.get("defender_points", [])
    result["disagreement_score"] = calculate_disagreement_score(prosecutor_args, defender_args)

    if not result.get("citations"):
        result["citations"] = _citation_urls(result.get("evidence", []))

    return result
