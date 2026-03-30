import re
from typing import Dict, List
from rag.knowledge_base import KNOWLEDGE_BASE
from llm_client import call_agent_json

STOPWORDS = {
    "the",
    "is",
    "are",
    "was",
    "were",
    "and",
    "or",
    "to",
    "of",
    "in",
    "a",
    "an",
    "for",
    "on",
    "with",
    "by",
    "this",
    "that",
    "it",
    "as",
    "at",
    "from",
    "has",
    "have",
    "had",
    "be",
    "been",
    "being",
    "right",
    "now",
}

DOMAIN_HINTS = {
    "health": ["vaccine", "autism", "virus", "covid", "disease", "medical"],
    "politics": ["prime minister", "election", "government", "nato", "un", "war"],
    "science": ["light", "earth", "physics", "science", "technology", "5g"],
    "history": ["ww2", "historical", "started", "ended", "ancient"],
    "technology": ["5g", "ai", "software", "internet", "chip", "model"],
}



def _extract_keywords(claim: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", claim.lower())
    keywords = []
    for token in tokens:
        if len(token) < 3 or token in STOPWORDS:
            continue
        keywords.append(token)
    ordered = []
    seen = set()
    for token in keywords:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered[:12]



def _extract_entities(claim: str) -> List[str]:
    entities = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", claim)
    unique = []
    seen = set()
    for entity in entities:
        if entity.lower() not in seen:
            seen.add(entity.lower())
            unique.append(entity)
    return unique[:6]



def _detect_domain(claim: str) -> str:
    lower = claim.lower()
    for domain, hints in DOMAIN_HINTS.items():
        if any(hint in lower for hint in hints):
            return domain
    return "general"



def analyze(claim: str) -> Dict:
    """
    Analyze a claim and determine its type and domain.
    Uses LLM with fallback to heuristics.
    """
    try:
        # Build prompt for LLM analysis
        prompt = f"""Analyze this claim and return a JSON object with:
- claim_type: one of (factual_claim, question, opinion, already_known_true)
- domain: one of (health, politics, science, history, technology, general)
- key_keywords: list of 3-5 most important keywords
- key_entities: list of 2-3 named entities mentioned

IMPORTANT CLASSIFICATION RULES:
- "WW3 is happening" → factual_claim (NOT already_known_true — needs verification)
- "Earth is round" → already_known_true
- "2+2=4" → already_known_true
- Claims about CURRENT EVENTS always → factual_claim
- Claims about PRICES/RATES always → factual_claim
- Only classify as already_known_true for absolute scientific/mathematical constants

CLAIM: "{claim}"

Return ONLY valid JSON, no markdown:
{{"claim_type":"factual_claim","domain":"general","key_keywords":[],"key_entities":[]}}"""

        result = call_agent_json(
            prompt=prompt,
            context="claim_analyzer",
            temperature=0,
            num_predict=300
        )
    except Exception:
        # Fallback to heuristics
        result = {}

    # Ensure required fields exist
    if not result.get("claim_type"):
        result["claim_type"] = "factual_claim"
    if not result.get("domain"):
        result["domain"] = _detect_domain(claim)
    if not result.get("key_keywords"):
        result["key_keywords"] = _extract_keywords(claim)
    if not result.get("key_entities"):
        result["key_entities"] = _extract_entities(claim)

    # Safety: if claim mentions known false topics,
    # always classify as factual_claim
    claim_lower = claim.lower()
    force_factual = [
        "ww3", "world war 3", "world war three",
        "gold rate", "gold price", "gold dropped",
        "5g covid", "5g coronavirus",
        "flat earth", "vaccines autism"
    ]
    if any(f in claim_lower for f in force_factual):
        result["claim_type"] = "factual_claim"
        print(f"[Analyzer] Force-classified as "
              f"factual_claim: '{claim}'")

    return result
