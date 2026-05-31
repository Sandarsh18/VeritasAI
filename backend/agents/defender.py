from llm_client import call_reasoning, extract_json
from services.evidence_classifier import classify_evidence
import logging
import os
import traceback

LOGGER = logging.getLogger("veritas.defender")
ENABLE_LLM_AGENTS = os.getenv("VERITAS_ENABLE_LLM_AGENTS", "0") == "1"


def _clean_snippet(text: str, limit: int = 260) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit]


def _minimal_supporting_arguments(claim: str, evidence: list) -> list:
    """Build a minimal SUPPORTING analysis when no source clearly supports the
    claim but evidence exists.

    Mirrors the prosecutor's minimal-opposing logic so the defender is never
    silent on a one-sided claim: it surfaces contextual support, partial
    relevance, and corroborating angles anchored to real retrieved sources."""
    arguments = []
    angles = [
        ("contextual support", "provides relevant context consistent with at least part of the claim"),
        ("partial relevance", "addresses the same topic and does not rule the claim out"),
        ("corroboration", "can be read as broadly compatible with the claim depending on interpretation"),
    ]
    for idx, article in enumerate(evidence[:3]):
        title = (article.get("title", "") or "").strip() or "Untitled source"
        source = (article.get("source", "") or "").strip() or "Unknown"
        content = (article.get("content", "") or article.get("snippet", "") or "").strip()
        angle_kind, angle_text = angles[idx % len(angles)]
        arguments.append(
            {
                "title": title,
                "source": source,
                "stance": "supports",
                "summary": (
                    f"Context ({angle_kind}): source '{title}' ({source}) {angle_text}."
                ),
                "evidence_quote": _clean_snippet(content),
                "credibility": article.get("credibility_score", 0.5),
                "minimal": True,
            }
        )
    return arguments


def _deterministic_arguments(claim: str, evidence: list) -> list:
    """Build defender (supporting) arguments using the shared stance classifier.

    The previous implementation matched generic cues like "is"/"are"/"has",
    which flagged essentially every article as supporting and forced a TRUE
    verdict for any claim. We now only keep articles the classifier labels
    SUPPORTS."""
    arguments = []
    for article in evidence[:8]:
        title = (article.get("title", "") or "").strip() or "Untitled source"
        source = (article.get("source", "") or "").strip() or "Unknown"
        content = (article.get("content", "") or article.get("snippet", "") or "").strip()

        stance = str(article.get("stance") or "").upper().strip()
        if stance not in {"SUPPORTS", "CONTRADICTS", "NEUTRAL"}:
            stance = classify_evidence(claim, article)

        if stance != "SUPPORTS":
            continue

        arguments.append(
            {
                "title": title,
                "source": source,
                "stance": "supports",
                "summary": (
                    f"Source '{title}' ({source}) supports the claim: it reports "
                    f"information consistent with the claim as stated."
                ),
                "evidence_quote": _clean_snippet(content),
                "credibility": article.get("credibility_score", 0.5),
            }
        )
        if len(arguments) >= 6:
            break
    return arguments


def _strength_from_arguments(arguments: list, evidence: list) -> str:
    if not arguments:
        return "none"
    creds = [float(a.get("credibility", 0.5) or 0.5) for a in arguments]
    avg_cred = sum(creds) / len(creds) if creds else 0.5
    if len(arguments) >= 3 and avg_cred >= 0.75:
        return "strong"
    if len(arguments) >= 2 or avg_cred >= 0.7:
        return "moderate"
    return "weak"


def run_defender(claim: str, evidence: list) -> dict:
    """
    Defender agent: finds arguments FOR the claim.
    Uses ONLY provided evidence - no hallucination.
    
    RULE: If evidence is empty, return immediately with no-evidence message.
    """
    # CRITICAL: Check evidence count first
    if not evidence:
        LOGGER.warning("[Defender] NO EVIDENCE PROVIDED - returning no-evidence verdict")
        return {
            "arguments": [],
            "strongest_point": "No evidence retrieved",
            "defense_strength": "none",
            "evidence_count": 0,
        }
    
    evidence_count = len(evidence)
    LOGGER.info("[Defender] Processing %d evidence articles", evidence_count)
    LOGGER.info(
        "DEFENDER INPUT: claim='%s' evidence_count=%d sample_titles=%s",
        claim,
        evidence_count,
        [str(a.get("title", ""))[:60] for a in evidence[:3]],
    )
    
    ev_text = ""
    
    # Only include first 6 articles with actual content
    for i, article in enumerate(evidence[:6], 1):
        title = article.get("title", "").strip() or "No title"
        source = article.get("source", "").strip() or "Unknown"
        url = article.get("url", "").strip() or ""
        content = (article.get("content", "") or article.get("snippet", "")).strip()[:400]
        credibility = article.get("credibility_score", 0.5)
        
        if not content:
            continue
            
        ev_text += (
            f"\nARTICLE {i} [{source}]:\n"
            f"Title: {title}\n"
            f"Credibility: {credibility}\n"
            f"Content: {content}\n"
        )

    if not ev_text.strip():
        LOGGER.warning("[Defender] No usable evidence content found")
        return {
            "arguments": [],
            "strongest_point": "No evidence with content",
            "defense_strength": "none",
            "evidence_count": evidence_count,
        }

    if not ENABLE_LLM_AGENTS:
        arguments = _deterministic_arguments(claim, evidence)
        if not arguments:
            LOGGER.info("[Defender] No supporting source; using minimal supporting analysis")
            arguments = _minimal_supporting_arguments(claim, evidence)
        result = {
            "arguments": arguments,
            "strongest_point": arguments[0]["summary"] if arguments else "No supporting evidence identified",
            "defense_strength": _strength_from_arguments(arguments, evidence),
            "evidence_count": evidence_count,
        }
        LOGGER.info(
            "DEFENDER OUTPUT: args=%d strength=%s (deterministic)",
            len(result["arguments"]), result["defense_strength"],
        )
        return result

    prompt = f"""You are a fact-checking defender analyzing evidence.

CLAIM TO SUPPORT: "{claim}"

RETRIEVED EVIDENCE (use ONLY these, no external facts):
{ev_text}

TASK: Find specific support for the claim in the evidence.

RULES:
1. Use ONLY what's written in the evidence above
2. Return a list of arguments as JSON objects.
3. If articles are unrelated, ignore them
4. If NO supporting evidence found, set defense_strength to "none" and arguments to an empty list.
5. NEVER assume external knowledge

Return ONLY valid JSON:
{{
  "arguments": [
    {{
      "title": "Article Title",
      "source": "Source Name",
      "stance": "supports",
      "summary": "Brief explanation of how it supports",
      "evidence_quote": "Exact quote from article",
      "credibility": 92
    }}
  ],
  "strongest_point": "most important supporting fact summary",
  "defense_strength": "strong|moderate|weak|none"
}}"""

    try:
        raw = call_reasoning(prompt, max_tokens=1000, agent_name="Defender")
        result = extract_json(raw)
    except Exception as exc:
        LOGGER.exception("[Defender] FULL ERROR TRACE")
        return {
            "success": False,
            "stage": "defender",
            "error": str(exc),
            "trace": traceback.format_exc(),
            "arguments": [],
            "strongest_point": "No defender analysis generated.",
            "defense_strength": "none",
            "evidence_count": evidence_count,
        }

    if not result or not result.get("arguments"):
        LOGGER.warning("[Defender] LLM returned no arguments — using deterministic stance fallback")
        arguments = _deterministic_arguments(claim, evidence)
        if not arguments:
            LOGGER.info("[Defender] No supporting source; using minimal supporting analysis")
            arguments = _minimal_supporting_arguments(claim, evidence)
        out = {
            "arguments": arguments,
            "strongest_point": arguments[0]["summary"] if arguments else "No supporting evidence identified",
            "defense_strength": _strength_from_arguments(arguments, evidence),
            "evidence_count": evidence_count,
        }
        LOGGER.info(
            "DEFENDER OUTPUT: args=%d strength=%s (fallback)",
            len(out["arguments"]), out["defense_strength"],
        )
        return out

    arguments = result.get("arguments", [])
    if not isinstance(arguments, list):
        arguments = []
    if not arguments:
        arguments = _minimal_supporting_arguments(claim, evidence)

    final = {
        "arguments": arguments[:6],
        "strongest_point": str(result.get("strongest_point", arguments[0].get("summary", "") if arguments else "")).strip(),
        "defense_strength": str(result.get("defense_strength", "weak")).strip().lower(),
        "evidence_count": evidence_count,
    }
    LOGGER.info(
        "DEFENDER OUTPUT: args=%d strength=%s (llm)",
        len(final["arguments"]), final["defense_strength"],
    )
    return final


def defend(claim, evidence, domain=None):
    """Public API for defender."""
    return run_defender(claim, evidence or [])
