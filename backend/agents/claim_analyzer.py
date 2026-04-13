from llm_client import OLLAMA_ANALYZER, call_ollama, extract_json


def analyze_claim(claim: str) -> dict:
    prompt = f"""Classify this input for fact-checking.

INPUT: "{claim}"

Classify as ONE of:
- factual_claim: can be verified true or false
- opinion: subjective, cannot be verified
- question: phrased as question
- already_known_true: universally known fact

Also extract:
- key_keywords: 3-5 important words from the claim
- domain: health/politics/science/history/sports/general
- key_entities: names, places, organisations mentioned

Return ONLY JSON:
{{
  "claim_type": "factual_claim",
  "domain": "general",
  "key_keywords": ["word1","word2","word3"],
  "key_entities": ["entity1"],
  "should_proceed": true,
  "early_response": null
}}

For opinion, set should_proceed false and:
"early_response": {{
  "verdict":"UNVERIFIED","confidence":40,
  "reasoning":"This is a subjective opinion.",
  "recommendation":"Rephrase as a factual claim."
}}"""

    raw = call_ollama(prompt, 0, 300, 512, OLLAMA_ANALYZER, "Analyzer")
    result = extract_json(raw)

    if not result:
        return {
            "claim_type": "factual_claim",
            "domain": "general",
            "key_keywords": claim.lower().split()[:4],
            "key_entities": [],
            "should_proceed": True,
            "early_response": None,
        }

    return result


def analyze(claim: str) -> dict:
    return analyze_claim(claim)
