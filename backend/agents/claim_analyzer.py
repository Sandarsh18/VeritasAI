import re

from llm_client import call_llm, extract_json


def _clean_claim(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def analyze_claim(claim: str) -> dict:
    claim = _clean_claim(claim)
    prompt = f"""You are a claim classification expert.

Classify this input and extract key information.

INPUT: "{claim}"

CLASSIFICATION RULES:
- factual_claim: Objectively TRUE or FALSE based on verifiable facts. Includes scientific facts, who holds positions, historical events, cause-effect claims.
  Examples: "light is faster than sound" (scientific fact), "Rahul Gandhi is PM of India" (political fact), "vaccines cause autism" (health claim)

- opinion: Subjective, cannot be objectively verified.
  Examples: "X is the best Y", "X is better than Y"

- question: Phrased as a question.
  Examples: "Is X true?", "Does X work?"

- already_known_true: Universally accepted scientific fact with absolute scientific consensus.
  Examples: "Earth orbits Sun", "water boils at 100C"

IMPORTANT: "light is faster than sound" IS a factual_claim (can be scientifically verified as TRUE).

Return ONLY this JSON:
{{
  "claim_type": "factual_claim|opinion|question|already_known_true",
  "domain": "science|health|politics|technology|sports|history|general",
  "key_entities": ["entity1", "entity2"],
  "key_keywords": ["keyword1", "keyword2", "keyword3"],
  "should_proceed": true,
  "is_verifiable": true,
  "early_response": null
}}

For opinions only, set should_proceed=false and add:
"early_response": {{
  "verdict": "UNVERIFIED",
  "confidence": 40,
  "reasoning": "This is a subjective opinion that cannot be objectively verified.",
  "recommendation": "Try rephrasing as a specific factual claim."
}}"""

    raw = call_llm(prompt, max_tokens=300, agent_name="ClaimAnalyzer")
    result = extract_json(raw)

    if not result:
        return {
            "claim_type": "factual_claim",
            "domain": "general",
            "key_entities": [],
            "key_keywords": claim.lower().split()[:5],
            "should_proceed": True,
            "is_verifiable": True,
            "early_response": None,
        }

    if "entities" not in result:
        result["entities"] = result.get("key_entities", [])

    if result.get("claim_type") in {"opinion", "question"} and result.get("should_proceed", True):
        result["should_proceed"] = False

    return result


def suggest_factual_claim(user_input: str) -> dict:
    cleaned = _clean_claim(user_input)
    analysis = analyze_claim(cleaned)
    claim_type = analysis.get("claim_type", "factual_claim")

    if claim_type == "factual_claim":
        return {
            "original": cleaned,
            "type": claim_type,
            "suggestion": cleaned,
            "message": "This already looks like a factual claim",
        }

    prompt = f"""Rewrite the following text into one concise, verifiable factual claim.

Input: "{cleaned}"

Rules:
- Output only one sentence
- No question mark
- Must be objectively testable
- No extra explanation"""
    suggestion = call_llm(prompt, max_tokens=60, temperature=0.1, agent_name="ClaimSuggestor").strip()
    suggestion = suggestion.splitlines()[0].strip() if suggestion else ""
    if not suggestion:
        suggestion = "Rewrite this into a specific factual claim with a date, person, or measurable fact."

    return {
        "original": cleaned,
        "type": claim_type,
        "suggestion": suggestion,
        "message": "Try this factual version instead",
    }
