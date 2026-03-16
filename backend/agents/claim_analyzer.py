from llm_client import call_llm, extract_json


def analyze_claim(claim: str) -> dict:
    prompt = f"""Classify this input for fact-checking.

INPUT: "{claim}"

Classify as ONE of:
- factual_claim: Can be verified TRUE/FALSE
  (scientific facts, historical dates, who holds
  positions, health claims, technology claims)
- opinion: Subjective preference, cannot be verified
  ("X is best", "X is better than Y")
- question: Phrased as question ("Is X true?")
- already_known_true: Universally known fact

"mobile is used as tool for cooking" = factual_claim
"light is faster than sound" = factual_claim
"world war 2 started in 2000" = factual_claim
"is rvce best college" = opinion

Return ONLY JSON:
{{
  "claim_type": "factual_claim",
  "domain": "technology|science|history|health|politics|general",
  "key_keywords": ["keyword1","keyword2","keyword3"],
  "should_proceed": true,
  "early_response": null
}}

For opinions only set should_proceed=false and:
"early_response": {{
  "verdict":"UNVERIFIED","confidence":40,
  "reasoning":"This is a subjective opinion.",
  "recommendation":"Rephrase as factual claim."
}}"""

    raw = call_llm(prompt, 300, 0.1, "Analyzer")
    result = extract_json(raw)
    if not result:
        return {
            "claim_type": "factual_claim",
            "domain": "general",
            "key_keywords": claim.lower().split()[:5],
            "should_proceed": True,
            "early_response": None,
        }
    return result


def suggest_factual_claim(user_input: str) -> dict:
    cleaned = (user_input or "").strip()
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
    suggestion = call_llm(prompt, max_tokens=80, temperature=0.1, agent_name="ClaimSuggestor").strip()
    suggestion = suggestion.splitlines()[0].strip() if suggestion else ""
    if not suggestion:
        suggestion = "Rewrite this into a specific factual claim with a date, person, or measurable fact."

    return {
        "original": cleaned,
        "type": claim_type,
        "suggestion": suggestion,
        "message": "Try this factual version instead",
    }