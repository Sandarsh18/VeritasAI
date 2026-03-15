import re
from .ollama_client import call_ollama


VALID_CLAIM_TYPES = {
    "factual_claim",
    "opinion",
    "question",
    "ambiguous",
    "already_known",
}

QUESTION_STARTERS = {
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "can",
    "could",
    "should",
    "would",
    "will",
    "what",
    "which",
    "who",
    "why",
    "how",
    "where",
    "when",
}

FACTUAL_SIGNAL_WORDS = {
    "cause",
    "causes",
    "cure",
    "cures",
    "prevent",
    "prevents",
    "spread",
    "spreads",
    "works",
    "orbits",
    "contains",
    "reduces",
    "increases",
    "ranked",
    "rank",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}

DOMAIN_KEYWORDS = {
    "health": {"vaccine", "covid", "virus", "doctor", "medicine", "bleach", "ivermectin", "cancer", "weight", "diet"},
    "politics": {"election", "vote", "government", "parliament", "citizenship", "caa", "gdp", "speech", "policy"},
    "science": {"earth", "sun", "oxygen", "water", "space", "quantum", "stem", "cell", "biology", "nuclear"},
    "education": {"college", "university", "nirf", "rvce", "iit", "iim", "degree", "campus", "ranking"},
    "technology": {"ai", "chatgpt", "internet", "software", "5g", "smartphone", "encryption", "social", "media"},
}

EARLY_RESPONSES = {
    "opinion": {
        "verdict": "UNVERIFIED",
        "confidence": 40,
        "reasoning": "This appears to be a subjective opinion rather than a verifiable factual claim. VeritasAI works best with specific factual claims that can be checked against evidence.",
        "recommendation": "Try rephrasing as a specific factual claim for better results.",
    },
    "question": {
        "verdict": "UNVERIFIED",
        "confidence": 35,
        "reasoning": "This is phrased as a question rather than a factual claim. Please rephrase it as a statement for verification.",
        "recommendation": "Example: Instead of 'Is X true?' try 'X is true' as the claim.",
    },
    "already_known": {
        "verdict": "TRUE",
        "confidence": 95,
        "reasoning": "This is a well-established fact supported by overwhelming scientific consensus.",
        "recommendation": "This fact is universally accepted.",
    },
    "ambiguous": {
        "verdict": "UNVERIFIED",
        "confidence": 33,
        "reasoning": "This input is too vague or unclear to verify reliably. VeritasAI needs a concrete statement with a clear subject and claim.",
        "recommendation": "Try rewriting this as one specific factual statement.",
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
        if any(marker in lowered for marker in ("best", "better", "good", "great", "worst", "bad")):
            return "opinion"
        return "question"

    if any(pattern in lowered for pattern in ("best ", " better ", " worse ", "good college", "great college", "terrible", "amazing", "bad college", "best college", "best phone")):
        return "opinion"

    known_patterns = (
        "earth orbits the sun",
        "the earth orbits the sun",
        "sun rises in the east",
        "the sun rises in the east",
        "water is h2o",
        "humans need oxygen",
        "oxygen is necessary for humans",
    )
    if any(pattern == lowered for pattern in known_patterns):
        return "already_known"

    if any(token in FACTUAL_SIGNAL_WORDS for token in tokens):
        return "factual_claim"

    vague_patterns = {"tell me", "what about", "this is", "that thing", "maybe true"}
    if lowered in vague_patterns:
        return "ambiguous"

    return None


def _classify_with_ollama(claim: str) -> str:
    prompt = (
        "Classify this input into exactly one category.\n"
        f"Input: '{claim}'\n\n"
        "Categories:\n"
        "- factual_claim: a specific verifiable statement that could be true or false based on evidence\n"
        "  Examples: 'vaccines cause autism', '5G towers spread disease', 'drinking bleach cures COVID'\n"
        "- opinion: subjective preference or evaluation\n"
        "  Examples: 'X is the best Y', 'X is better than Y', 'X is great/bad/terrible'\n"
        "- question: phrased as a question\n"
        "  Examples: 'is X true?', 'does X cause Y?', 'can X do Y?'\n"
        "- already_known: universally accepted scientific fact\n"
        "  Examples: 'earth orbits sun', 'water is H2O', 'humans need oxygen'\n"
        "- ambiguous: too vague or unclear to classify\n\n"
        "Reply with ONLY one word from the list above.\n"
        "No explanation. No punctuation. Just the category."
    )
    response = call_ollama(prompt, num_predict=8, num_ctx=512).lower().strip()
    response = re.sub(r"[^a-z_\n]", " ", response).strip().split()
    if not response:
        return "factual_claim"
    first = response[0]
    return first if first in VALID_CLAIM_TYPES else "factual_claim"


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
