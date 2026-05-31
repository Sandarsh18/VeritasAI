from llm_client import call_reasoning, extract_json
from services.evidence_classifier import classify_evidence
import logging
import os
import traceback

LOGGER = logging.getLogger("veritas.prosecutor")
ENABLE_LLM_AGENTS = os.getenv("VERITAS_ENABLE_LLM_AGENTS", "0") == "1"


def _clean_snippet(text: str, limit: int = 260) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit]


def _minimal_opposing_arguments(claim: str, evidence: list) -> list:
    """Build a minimal CHALLENGING analysis when no source clearly contradicts
    the claim but evidence exists.

    The prosecutor must not stay silent on one-sided claims. Instead of an empty
    result it surfaces honest skeptical angles — limitations, uncertainty,
    source limitations, and alternative interpretations — anchored to the real
    retrieved sources (so it never fabricates contradictions)."""
    arguments = []
    angles = [
        ("limitation", "does not independently rule out every interpretation of the claim, leaving a residual margin of uncertainty"),
        ("source limitation", "is a single source whose framing may not capture competing scholarly or contextual views"),
        ("alternative interpretation", "could be read differently depending on definitions, time frame, or scope used in the claim"),
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
                "stance": "challenges",
                "summary": (
                    f"Caveat ({angle_kind}): source '{title}' ({source}) {angle_text}."
                ),
                "evidence_quote": _clean_snippet(content),
                "credibility": article.get("credibility_score", 0.5),
                "minimal": True,
            }
        )
    return arguments


def _deterministic_arguments(claim: str, evidence: list) -> list:
    """Build prosecutor (contradicting) arguments using the shared stance
    classifier rather than a brittle keyword list. An article counts against
    the claim when the classifier labels it CONTRADICTS, or when it carries an
    explicit CONTRADICTS stance assigned upstream."""
    arguments = []
    for article in evidence[:8]:
        title = (article.get("title", "") or "").strip() or "Untitled source"
        source = (article.get("source", "") or "").strip() or "Unknown"
        content = (article.get("content", "") or article.get("snippet", "") or "").strip()

        stance = str(article.get("stance") or "").upper().strip()
        if stance not in {"SUPPORTS", "CONTRADICTS", "NEUTRAL"}:
            stance = classify_evidence(claim, article)

        if stance != "CONTRADICTS":
            continue

        arguments.append(
            {
                "title": title,
                "source": source,
                "stance": "contradicts",
                "summary": (
                    f"Source '{title}' ({source}) contradicts the claim: it reports "
                    f"information that conflicts with the claim as stated."
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
    avg_cred = 0.5
    creds = [float(a.get("credibility", 0.5) or 0.5) for a in arguments]
    if creds:
        avg_cred = sum(creds) / len(creds)
    if len(arguments) >= 3 and avg_cred >= 0.75:
        return "strong"
    if len(arguments) >= 2 or avg_cred >= 0.7:
        return "moderate"
    return "weak"


def run_prosecutor(claim: str, evidence: list) -> dict:
    """
    Prosecutor agent: finds arguments AGAINST the claim.
    Uses ONLY provided evidence - no hallucination.
    
    RULE: If evidence is empty, return immediately with no-evidence message.
    """
    # CRITICAL: Check evidence count first
    if not evidence:
        LOGGER.warning("[Prosecutor] NO EVIDENCE PROVIDED - returning no-evidence verdict")
        return {
            "arguments": [],
            "strongest_point": "No evidence retrieved",
            "prosecution_strength": "none",
            "evidence_count": 0,
        }
    
    evidence_count = len(evidence)
    LOGGER.info("[Prosecutor] Processing %d evidence articles", evidence_count)
    LOGGER.info(
        "PROSECUTOR INPUT: claim='%s' evidence_count=%d sample_titles=%s",
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
        LOGGER.warning("[Prosecutor] No usable evidence content found")
        return {
            "arguments": [],
            "strongest_point": "No evidence with content",
            "prosecution_strength": "none",
            "evidence_count": evidence_count,
        }

    if not ENABLE_LLM_AGENTS:
        arguments = _deterministic_arguments(claim, evidence)
        if not arguments:
            LOGGER.info("[Prosecutor] No contradicting source; using minimal opposing analysis")
            arguments = _minimal_opposing_arguments(claim, evidence)
        result = {
            "arguments": arguments,
            "strongest_point": arguments[0]["summary"] if arguments else "No contradictions identified",
            "prosecution_strength": _strength_from_arguments(arguments, evidence),
            "evidence_count": evidence_count,
        }
        LOGGER.info(
            "PROSECUTOR OUTPUT: args=%d strength=%s (deterministic)",
            len(result["arguments"]), result["prosecution_strength"],
        )
        return result

    prompt = f"""You are a fact-checking prosecutor analyzing evidence.

CLAIM TO CHALLENGE: "{claim}"

RETRIEVED EVIDENCE (use ONLY these, no external facts):
{ev_text}

TASK: Find specific contradictions in the evidence.

RULES:
1. Use ONLY what's written in the evidence above
2. Return a list of arguments as JSON objects.
3. If articles are unrelated, ignore them  
4. If NO contradictions found, set prosecution_strength to "none" and arguments to an empty list.
5. NEVER assume external knowledge

Return ONLY valid JSON:
{{
  "arguments": [
    {{
      "title": "Article Title",
      "source": "Source Name",
      "stance": "contradicts",
      "summary": "Brief explanation of how it contradicts",
      "evidence_quote": "Exact quote from article",
      "credibility": 92
    }}
  ],
  "strongest_point": "most important contradiction summary",
  "prosecution_strength": "strong|moderate|weak|none"
}}"""

    try:
        raw = call_reasoning(prompt, max_tokens=1000, agent_name="Prosecutor")
        result = extract_json(raw)
    except Exception as exc:
        LOGGER.exception("[Prosecutor] FULL ERROR TRACE")
        return {
            "success": False,
            "stage": "prosecutor",
            "error": str(exc),
            "trace": traceback.format_exc(),
            "arguments": [],
            "strongest_point": "No prosecutor analysis generated.",
            "prosecution_strength": "none",
            "evidence_count": evidence_count,
        }

    if not result or not result.get("arguments"):
        LOGGER.warning("[Prosecutor] LLM returned no arguments — using deterministic stance fallback")
        arguments = _deterministic_arguments(claim, evidence)
        if not arguments:
            LOGGER.info("[Prosecutor] No contradicting source; using minimal opposing analysis")
            arguments = _minimal_opposing_arguments(claim, evidence)
        out = {
            "arguments": arguments,
            "strongest_point": arguments[0]["summary"] if arguments else "No contradictions identified",
            "prosecution_strength": _strength_from_arguments(arguments, evidence),
            "evidence_count": evidence_count,
        }
        LOGGER.info(
            "PROSECUTOR OUTPUT: args=%d strength=%s (fallback)",
            len(out["arguments"]), out["prosecution_strength"],
        )
        return out

    arguments = result.get("arguments", [])
    if not isinstance(arguments, list):
        arguments = []
    if not arguments:
        arguments = _minimal_opposing_arguments(claim, evidence)

    final = {
        "arguments": arguments[:6],
        "strongest_point": str(result.get("strongest_point", arguments[0].get("summary", "") if arguments else "")).strip(),
        "prosecution_strength": str(result.get("prosecution_strength", "weak")).strip().lower(),
        "evidence_count": evidence_count,
    }
    LOGGER.info(
        "PROSECUTOR OUTPUT: args=%d strength=%s (llm)",
        len(final["arguments"]), final["prosecution_strength"],
    )
    return final


def prosecute(claim, evidence, domain=None):
    """Public API for prosecutor."""
    return run_prosecutor(claim, evidence or [])
