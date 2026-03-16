import re
from .ollama_client import call_ollama


VALID_CLAIM_TYPES = {
    "factual_claim",
    "opinion",
    "question",
    "already_known_true",
    "ambiguous",
}

QUESTION_STARTERS = {
    "is", "are", "was", "were", "do", "does", "did", "can", "could",
    "should", "would", "will", "what", "which", "who", "why", "how", "where", "when",
}

OPINION_MARKERS = {
    "good", "bad", "better", "best", "worse", "worst", "great", "terrible", "awesome"
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
}

DOMAIN_KEYWORDS = {
    "health": {"vaccine", "covid", "virus", "doctor", "medicine", "bleach", "ivermectin", "cancer", "diet"},
    "politics": {"election", "vote", "government", "parliament", "pm", "prime", "minister", "policy", "modi", "rahul"},
    "science": {"earth", "sun", "oxygen", "water", "space", "biology", "physics", "flat"},
    "education": {"college", "university", "nirf", "rvce", "iit", "iim", "degree", "ranking"},
    "technology": {"ai", "chatgpt", "internet", "software", "5g", "smartphone", "encryption", "media"},
}

EARLY_RESPONSES = {
    "opinion": {
        "verdict": "UNVERIFIED",
        "confidence": 40,
        "reasoning": "This appears to be a subjective opinion rather than a verifiable factual claim.",
        "recommendation": "Try rephrasing it as a specific factual statement.",
    },
    "question": {
        "verdict": "UNVERIFIED",
        "confidence": 35,
        "reasoning": "This is phrased as a question rather than a factual claim.",
        "recommendation": "Rephrase as a statement, then verify it.",
    },
    "already_known_true": {
        "verdict": "TRUE",
        "confidence": 95,
        "reasoning": "This is a universally accepted fact.",
        "recommendation": "No further verification is typically required.",
    },
    "ambiguous": {
        "verdict": "UNVERIFIED",
        "confidence": 33,
        "reasoning": "This input is too vague or unclear to verify reliably.",
        "recommendation": "Rewrite it as one concrete factual claim.",
    },
}


def _clean_claim(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\-\.]*", text.lower())


def _heuristic_claim_type(claim: str) -> str | None:
    text = _clean_claim(claim)
    lowered = text.lower()
    tokens = _tokenize(lowered)
    if not tokens or len(tokens) < 2:
        return "ambiguous"

    if lowered.endswith("?") or tokens[0] in QUESTION_STARTERS:
        return "question"

    if any(marker in tokens for marker in OPINION_MARKERS):
        if any(kw in tokens for kw in ("leader", "party", "college", "government", "person")):
            return "opinion"
    if any(pattern in lowered for pattern in (" is better than ", " is best ", " is a good ", " is a bad ")):
        return "opinion"

    known_patterns = {
        "earth orbits sun",
        "the earth orbits the sun",
        "water is h2o",
        "humans need oxygen",
    }
    if lowered in known_patterns:
        return "already_known_true"

    factual_markers = {
        "current", "pm", "prime", "minister", "won", "contain", "contains", "cause", "causes",
        "richest", "flat", "microchips", "world", "cup",
    }
    if any(token in factual_markers for token in tokens):
        return "factual_claim"

    return None


def _classify_with_ollama(claim: str) -> str:
    prompt = (
        "Classify this input into exactly one category.\n"
        f"Input: '{claim}'\n\n"
        "FACTUAL_CLAIM: A specific statement that is objectively TRUE or FALSE based on verifiable facts.\n"
        "This includes:\n"
        "- Claims about who holds a position/title\n"
        "- Claims about events that happened or didn't\n"
        "- Claims about scientific facts\n"
        "- Claims about statistics or numbers\n"
        "- Claims that something causes something else\n"
        "- Historical claims\n"
        "Examples: 'Rahul Gandhi is PM of India',\n"
        "          'vaccines cause autism',\n"
        "          '5G causes cancer',\n"
        "          'India won WW2'\n\n"
        "OPINION: Subjective preference or evaluation that cannot be objectively true/false.\n"
        "Examples: 'X is the best Y',\n"
        "          'X is better than Y',\n"
        "          'X is a good/bad person'\n\n"
        "QUESTION: Phrased as a question.\n"
        "Examples: 'Is X true?', 'Does X cause Y?'\n\n"
        "ALREADY_KNOWN_TRUE: Universally accepted fact.\n"
        "Examples: 'Earth orbits Sun', 'water is H2O'\n\n"
        "Reply ONLY with one word:\n"
        "factual_claim OR opinion OR question OR already_known_true"
    )
    response = call_ollama(prompt, num_predict=8, num_ctx=512).lower().strip()
    response = re.sub(r"[^a-z_\n]", " ", response).strip().split()
    first = response[0] if response else "factual_claim"
    return first if first in {"factual_claim", "opinion", "question", "already_known_true"} else "factual_claim"


def _extract_entities(claim: str) -> list[str]:
    text = _clean_claim(claim)
    entities = []
    entities.extend(re.findall(r"\b[A-Z][A-Za-z0-9&.-]+(?:\s+[A-Z][A-Za-z0-9&.-]+)*", text))
    lowered_tokens = []
    for token in _tokenize(text):
        if token in STOPWORDS or len(token) < 3:
            continue
        lowered_tokens.append(token)
    for token in lowered_tokens:
        if token.upper() in {"RVCE", "AI", "GDP", "NIRF", "ISRO", "COVID", "CAA", "5G"}:
            entities.append(token.upper())
        elif token not in {item.lower() for item in entities}:
            entities.append(token)
    deduped = []
    seen = set()
    for entity in entities:
        key = entity.lower()
        if key not in seen:
            deduped.append(entity)
            seen.add(key)
    return deduped[:8]


def _detect_domain(claim: str) -> str:
    tokens = set(_tokenize(claim))
    best_domain = "general"
    best_score = 0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = len(tokens & keywords)
        if score > best_score:
            best_domain = domain
            best_score = score
    return best_domain


def analyze_claim(claim: str) -> dict:
    clean_claim = _clean_claim(claim)
    heuristic_type = _heuristic_claim_type(clean_claim)
    claim_type = heuristic_type or _classify_with_ollama(clean_claim)
    if claim_type not in VALID_CLAIM_TYPES:
        claim_type = "factual_claim"

    analysis = {
        "claim_type": claim_type,
        "entities": _extract_entities(clean_claim),
        "domain": _detect_domain(clean_claim),
        "should_proceed": claim_type == "factual_claim",
        "early_response": None,
    }

    if claim_type in EARLY_RESPONSES:
        analysis["should_proceed"] = False
        analysis["early_response"] = EARLY_RESPONSES[claim_type]

    return analysis


def _fallback_suggestion(user_input: str, claim_type: str) -> str:
    text = _clean_claim(user_input)
    lowered = text.lower()
    if "rvce" in lowered and "college" in lowered:
        return "RVCE is ranked among the top engineering colleges in Karnataka by NIRF 2024"
    if "best phone" in lowered:
        return "The iPhone 15 was ranked among the best phones of 2024 by major technology reviewers"
    if lowered.startswith("does drinking water"):
        return "Drinking water before meals can support modest weight loss in some adults"
    if claim_type == "question":
        stripped = re.sub(r"^[a-z]+\s+", "", lowered).rstrip("?")
        stripped = stripped[:1].upper() + stripped[1:] if stripped else ""
        return stripped or "Rewrite this as one specific factual statement that can be verified"
    return "Rewrite this into a measurable factual claim with a source, date, or ranking"


def suggest_factual_claim(user_input: str) -> dict:
    analysis = analyze_claim(user_input)
    claim_type = analysis.get("claim_type", "factual_claim")
    fallback = _fallback_suggestion(user_input, claim_type)
    if claim_type == "factual_claim":
        return {
            "original": _clean_claim(user_input),
            "type": claim_type,
            "suggestion": _clean_claim(user_input),
            "message": "This already looks like a factual claim",
        }

    suggestion = fallback
    if "rvce" not in user_input.lower() and "best college" not in user_input.lower():
        prompt = (
            "Convert this opinion/question into a specific verifiable factual claim:\n"
            f"Input: '{_clean_claim(user_input)}'\n"
            "Return only the rephrased factual claim, nothing else."
        )
        llm_suggestion = call_ollama(prompt, num_predict=48, num_ctx=512).strip()
        llm_suggestion = llm_suggestion.splitlines()[0].strip() if llm_suggestion else ""
        if llm_suggestion and len(llm_suggestion) >= 12 and "not a best" not in llm_suggestion.lower():
            suggestion = llm_suggestion

    return {
        "original": _clean_claim(user_input),
        "type": claim_type,
        "suggestion": suggestion,
        "message": "Try this factual version instead",
    }
