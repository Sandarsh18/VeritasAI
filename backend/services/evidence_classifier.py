import logging
import os
from llm_client import call_ollama, extract_json

LOGGER = logging.getLogger("veritas.evidence_classifier")
ENABLE_EVIDENCE_CLASSIFIER_LLM = os.getenv("VERITAS_ENABLE_EVIDENCE_CLASSIFIER_LLM", "0") == "1"


def _keyword_classify(claim: str, title: str, content: str) -> str:
    claim_lower = claim.lower()
    content_lower = f"{title} {content}".lower()

    support_words = ["confirms", "proves", "supports", "true", "agrees", "shows", "found that"]
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
    ]

    support_score = sum(1 for word in support_words if word in content_lower)
    contradict_score = sum(1 for word in contradict_words if word in content_lower)

    claim_terms = [term for term in claim_lower.split() if len(term) > 2]
    overlap = sum(1 for term in claim_terms if term in content_lower)
    if overlap:
        support_score += 1
        contradict_score += 1

    if contradict_score > support_score:
        return "CONTRADICTS"
    if support_score > contradict_score:
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
