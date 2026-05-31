import logging
import os
import re
from llm_client import call_ollama, extract_json

LOGGER = logging.getLogger("veritas.evidence_classifier")
ENABLE_EVIDENCE_CLASSIFIER_LLM = os.getenv("VERITAS_ENABLE_EVIDENCE_CLASSIFIER_LLM", "0") == "1"


def _keyword_classify(claim: str, title: str, content: str) -> str:
    claim_lower = claim.lower()
    content_lower = f"{title} {content}".lower()

    explicit_stance = str(content or "")
    if explicit_stance.upper() in {"SUPPORTS", "CONTRADICTS", "NEUTRAL"}:
        return explicit_stance.upper()

    support_words = [
        "confirmed",
        "confirms",
        "verified",
        "officially",
        "evidence shows",
        "data shows",
        "research shows",
        "according to",
        "announced",
        "landed",
        "successful",
    ]
    contradict_words = [
        "debunked",
        "false",
        "misleading",
        "fake",
        "denies",
        "no evidence",
        "hoax",
        "untrue",
        "wrong",
        "no link",
        "not supported",
        "myth",
        "conspiracy",
        "extinct",
        "does not",
        "did not",
        "not true",
    ]

    support_score = sum(1 for word in support_words if word in content_lower)
    contradict_score = sum(1 for word in contradict_words if word in content_lower)

    stop = {
        "the", "is", "are", "was", "were", "and", "for", "with", "that", "this",
        "claim", "today", "latest", "news", "does", "contain", "contains"
    }
    claim_terms = [
        term for term in re.findall(r"[a-z0-9]+", claim_lower)
        if len(term) > 2 and term not in stop
    ]
    overlap = sum(1 for term in claim_terms if term in content_lower)
    if claim_terms and overlap == 0:
        return "NEUTRAL"

    if len(claim_terms) >= 3 and overlap < 2:
        return "NEUTRAL"

    exact_claim = " ".join(claim_terms[:5])
    if exact_claim and exact_claim in content_lower:
        support_score += 2

    # Negation directly attached to a claim term signals contradiction, e.g.
    # claim "Sun is a planet" + content "the Sun is not a planet".
    for term in claim_terms:
        if any(neg in content_lower for neg in (f"not a {term}", f"not {term}", f"no {term}", f"isn't {term}", f"is not {term}")):
            contradict_score += 2

    if contradict_score > support_score:
        return "CONTRADICTS"
    if support_score > contradict_score:
        return "SUPPORTS"

    # Tie-break: a clearly on-topic source (strong claim-term overlap) is treated
    # as weak support rather than NEUTRAL, so evidence cards and the defender
    # split are not left empty for relevant results.
    if claim_terms:
        ratio = overlap / len(claim_terms)
        if ratio >= 0.6 and overlap >= 2:
            return "SUPPORTS"
    return "NEUTRAL"

def classify_evidence(claim: str, article: dict) -> str:
    """
    Classifies an article as SUPPORTS, CONTRADICTS, or NEUTRAL relative to a claim.
    """
    title = article.get("title", "").strip()
    content = article.get("snippet", "") or article.get("content", "") or ""
    content = content.strip()[:300]
    
    if not title and not content:
        return "NEUTRAL"

    if not ENABLE_EVIDENCE_CLASSIFIER_LLM:
        return _keyword_classify(claim, title, content)
        
    prompt = f"""You are an evidence classification engine.
    
CLAIM: "{claim}"

ARTICLE TITLE: "{title}"
ARTICLE CONTENT: "{content}"

TASK: Does the article support, contradict, or is it neutral/unrelated to the claim?
Return ONLY valid JSON in this exact format:
{{
  "stance": "SUPPORTS|CONTRADICTS|NEUTRAL"
}}
"""
    try:
        raw_response = call_ollama(prompt, model="llama3.2:1b", max_tokens=50)
        parsed = extract_json(raw_response)
        
        stance = str(parsed.get("stance", "NEUTRAL")).upper().strip()
        if stance in ["SUPPORTS", "CONTRADICTS", "NEUTRAL"]:
            return stance
            
    except Exception as e:
        LOGGER.warning("[Classifier] Failed to classify evidence: %s", str(e)[:100])
        
    return _keyword_classify(claim, title, content)
