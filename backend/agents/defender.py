from llm_client import call_reasoning, extract_json
import logging
import os
import traceback

LOGGER = logging.getLogger("veritas.defender")
ENABLE_LLM_AGENTS = os.getenv("VERITAS_ENABLE_LLM_AGENTS", "0") == "1"


def _deterministic_arguments(claim: str, evidence: list) -> list:
    cues = ["confirms", "supports", "shows", "found", "reports", "will", "is", "are", "has"]
    arguments = []
    for article in evidence[:6]:
        title = article.get("title", "").strip() or "Untitled source"
        source = article.get("source", "").strip() or "Unknown"
        content = (article.get("content", "") or article.get("snippet", "")).strip()
        lower = f"{title} {content}".lower()
        if any(cue in lower for cue in cues):
            arguments.append(
                {
                    "title": title,
                    "source": source,
                    "stance": "supports",
                    "summary": f"Source '{title}' ({source}) contains evidence relevant to the claim.",
                    "evidence_quote": content[:260],
                    "credibility": article.get("credibility_score", 0.5),
                }
            )
    return arguments[:6]


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
        return {
            "arguments": arguments,
            "strongest_point": arguments[0]["summary"] if arguments else "No supporting evidence identified",
            "defense_strength": "moderate" if arguments else "none",
            "evidence_count": evidence_count,
        }

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
        LOGGER.warning("[Defender] LLM returned no arguments")
        return {
            "arguments": [],
            "strongest_point": "No supporting evidence identified",
            "defense_strength": "none",
            "evidence_count": evidence_count,
        }

    arguments = result.get("arguments", [])
    if not isinstance(arguments, list):
        arguments = []

    return {
        "arguments": arguments[:6],
        "strongest_point": str(result.get("strongest_point", arguments[0].get("summary", "") if arguments else "")).strip(),
        "defense_strength": str(result.get("defense_strength", "weak")).strip().lower(),
        "evidence_count": evidence_count,
    }


def defend(claim, evidence, domain=None):
    """Public API for defender."""
    return run_defender(claim, evidence or [])
