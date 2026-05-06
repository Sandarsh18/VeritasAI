from llm_client import call_reasoning, extract_json
import logging
import os
import traceback

LOGGER = logging.getLogger("veritas.prosecutor")
ENABLE_LLM_AGENTS = os.getenv("VERITAS_ENABLE_LLM_AGENTS", "0") == "1"


def _deterministic_arguments(claim: str, evidence: list) -> list:
    cues = ["false", "no evidence", "no link", "misleading", "fake", "debunk", "conspiracy", "hoax", "cannot"]
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
                    "stance": "contradicts",
                    "summary": f"{source} reports evidence that challenges the claim.",
                    "evidence_quote": content[:260],
                    "credibility": article.get("credibility_score", 0.5),
                }
            )
    return arguments[:4]


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
        return {
            "arguments": arguments,
            "strongest_point": arguments[0]["summary"] if arguments else "No contradictions identified",
            "prosecution_strength": "moderate" if arguments else "none",
            "evidence_count": evidence_count,
        }

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
        LOGGER.warning("[Prosecutor] LLM returned no arguments")
        return {
            "arguments": [],
            "strongest_point": "No contradictions identified",
            "prosecution_strength": "none",
            "evidence_count": evidence_count,
        }

    arguments = result.get("arguments", [])
    if not isinstance(arguments, list):
        arguments = []

    return {
        "arguments": arguments[:6],
        "strongest_point": str(result.get("strongest_point", arguments[0].get("summary", "") if arguments else "")).strip(),
        "prosecution_strength": str(result.get("prosecution_strength", "weak")).strip().lower(),
        "evidence_count": evidence_count,
    }


def prosecute(claim, evidence, domain=None):
    """Public API for prosecutor."""
    return run_prosecutor(claim, evidence or [])
