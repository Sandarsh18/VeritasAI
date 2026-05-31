import re
import os

from llm_client import OLLAMA_ANALYZER, call_ollama, extract_json

ENABLE_CLAIM_ANALYZER_LLM = os.getenv("VERITAS_ENABLE_CLAIM_ANALYZER_LLM", "0") == "1"


ALLOWED_DOMAINS = {
    "politics",
    "health",
    "science",
    "sports",
    "economy",
    "religion",
    "technology",
}

DOMAIN_HINTS = {
    "politics": [
        "election",
        "minister",
        "parliament",
        "government",
        "policy",
        "modi",
        "bjp",
        "congress",
        "vote",
        "war",
        "border",
        "diplomacy",
    ],
    "health": [
        "covid",
        "vaccine",
        "virus",
        "disease",
        "hospital",
        "medical",
        "health",
        "doctor",
    ],
    "science": [
        "space",
        "nasa",
        "physics",
        "chemistry",
        "biology",
        "climate",
        "research",
        "experiment",
        "moon",
        "earth",
        "isro",
        "dinosaur",
        "t-rex",
        "trex",
        "tyrannosaurus",
        "mount everest",
    ],
    "sports": [
        "cricket",
        "ipl",
        "football",
        "tennis",
        "match",
        "csk",
        "rcb",
        "world cup",
        "olympics",
        "olympic",
    ],
    "economy": [
        "economy",
        "gdp",
        "inflation",
        "market",
        "stock",
        "rupee",
        "tax",
        "budget",
    ],
    "religion": [
        "religion",
        "hindu",
        "islam",
        "christian",
        "temple",
        "mosque",
        "church",
        "bible",
        "quran",
    ],
    "technology": [
        "ai",
        "artificial intelligence",
        "software",
        "app",
        "mobile",
        "phone",
        "internet",
        "chip",
        "robot",
        "5g",
        "6g",
        "telecom",
    ],
}


def _fallback_domain(claim: str) -> str:
    text = (claim or "").lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))

    # Required hard fallback rules.
    if "covid" in text:
        return "health"
    if "cricket" in text:
        return "sports"
    if "india economy" in text or ("india" in text and "economy" in text):
        return "economy"

    scores = {domain: 0 for domain in ALLOWED_DOMAINS}
    for domain, hints in DOMAIN_HINTS.items():
        for hint in hints:
            if hint == "ai":
                if hint in tokens:
                    scores[domain] += 1
            elif hint in text:
                scores[domain] += 1

    best_domain = max(scores, key=scores.get)
    if scores[best_domain] > 0:
        return best_domain

    return "general"


def classify_domain(claim: str) -> str:
    if not ENABLE_CLAIM_ANALYZER_LLM:
        return _fallback_domain(claim)

    prompt = (
        "Domain from [politics, health, science, sports, economy, religion, technology]. "
        f"Claim: {claim}. Return only the domain."
    )

    raw = call_ollama(prompt, 0, 40, 256, OLLAMA_ANALYZER, "DomainClassifier")
    parsed = extract_json(raw)

    candidate = ""
    if isinstance(parsed, dict):
        candidate = str(parsed.get("domain", "")).strip().lower()

    if not candidate:
        tokens = re.findall(r"[a-z]+", str(raw or "").lower())
        if tokens:
            candidate = tokens[0]

    if candidate in ALLOWED_DOMAINS:
        return candidate

    return _fallback_domain(claim)


def analyze_claim(claim: str) -> dict:
    domain = classify_domain(claim)
    fallback = {
        "claim_type": "factual_claim",
        "domain": domain,
        "key_keywords": [w for w in re.findall(r"[a-z0-9]+", claim.lower()) if len(w) > 2][:6],
        "key_entities": [],
        "should_proceed": True,
        "early_response": None,
    }

    if not ENABLE_CLAIM_ANALYZER_LLM:
        return fallback

    prompt = (
        "Classify the claim for fact-checking and return JSON only. "
        "Keys: claim_type (factual_claim/opinion/question/already_known_true), "
        "key_keywords (3-6 words), key_entities (names/places), should_proceed, early_response. "
        "If opinion, set should_proceed false and early_response with verdict UNVERIFIED, confidence 40, "
        "reasoning and recommendation. "
        f"Claim: \"{claim}\""
    )

    raw = call_ollama(prompt, 0, 300, 512, OLLAMA_ANALYZER, "Analyzer")
    result = extract_json(raw)

    if not isinstance(result, dict):
        return fallback

    claim_type = str(result.get("claim_type", "factual_claim") or "factual_claim").strip()
    if claim_type not in {"factual_claim", "opinion", "question", "already_known_true"}:
        claim_type = "factual_claim"

    keywords = result.get("key_keywords") if isinstance(result.get("key_keywords"), list) else []
    entities = result.get("key_entities") if isinstance(result.get("key_entities"), list) else []
    normalized_keywords = [str(item).strip() for item in keywords if str(item).strip()][:6]
    normalized_entities = [str(item).strip() for item in entities if str(item).strip()][:6]

    should_proceed = bool(result.get("should_proceed", True))
    early_response = result.get("early_response")
    if claim_type == "opinion" and not isinstance(early_response, dict):
        should_proceed = False
        early_response = {
            "verdict": "UNVERIFIED",
            "confidence": 40,
            "reasoning": "This is a subjective opinion.",
            "recommendation": "Rephrase as a factual claim.",
        }

    return {
        "claim_type": claim_type,
        "domain": domain,
        "key_keywords": normalized_keywords,
        "key_entities": normalized_entities,
        "should_proceed": should_proceed,
        "early_response": early_response,
    }


def analyze(claim: str) -> dict:
    return analyze_claim(claim)
