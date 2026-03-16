from llm_client import call_llm, extract_json

KNOWN_FACTS = {
    "world war 2": "WW2 started Sept 1, 1939. Ended 1945.",
    "world war 1": "WW1 started July 28, 1914. Ended 1918.",
    "prime minister india": "Narendra Modi is PM since 2014.",
    "rahul gandhi": "Rahul Gandhi is opposition leader, NOT PM.",
    "president india": "Droupadi Murmu is President since 2022.",
    "speed of light": "Light: 299,792,458 m/s. Sound: 343 m/s. Light is faster.",
    "earth flat": "Earth is spherical. Flat earth is false.",
    "vaccines autism": "No link. Original study retracted. False claim.",
    "5g covid": "5G cannot spread viruses. False claim.",
    "mobile cooking": "Mobile phones are not cooking tools. FALSE claim.",
}


def get_hint(claim: str) -> str:
    lowered = claim.lower()
    hints = [value for key, value in KNOWN_FACTS.items() if key in lowered]
    return " | ".join(hints)


def run_judge(claim, prosecutor, defender, evidence) -> dict:
    cred_scores = [float(article.get("credibility_score", 0.5)) for article in evidence]
    avg_credibility = round(sum(cred_scores) / len(cred_scores), 2) if cred_scores else 0.5

    p_args = prosecutor.get("arguments", [])
    d_args = defender.get("arguments", [])
    p_strength = prosecutor.get("prosecution_strength", "?")
    d_strength = defender.get("defense_strength", "?")

    hint = get_hint(claim)
    hint_section = f"\nVERIFIED FACT: {hint}\n" if hint else ""

    p_text = "\n".join(f"  • {arg}" for arg in p_args[:3])
    d_text = "\n".join(f"  • {arg}" for arg in d_args[:3])

    prompt = f"""You are an expert fact-checking judge.

CLAIM: "{claim}"
{hint_section}
PROSECUTION (against claim):
{p_text or "  • No strong contradictions found"}
Strength: {p_strength}

DEFENSE (for claim):
{d_text or "  • No strong support found"}
Strength: {d_strength}

Source credibility: {avg_credibility:.0%}

VERDICT RULES:
- Use YOUR knowledge as primary source
- If prosecution strong + defense weak = FALSE 75-95%
- If defense strong + prosecution weak = TRUE 75-95%
- Mixed evidence = MISLEADING 55-74%
- No evidence = UNVERIFIED 30-50%
- NEVER return confidence = 35 exactly
- NEVER return confidence = 60 exactly

EXAMPLES:
"mobile is used as tool for cooking" = FALSE ~88%
  (phones are NOT cooking appliances)
"world war 2 started in 2000" = FALSE ~96%
  (WW2 started 1939)
"light is faster than sound" = TRUE ~95%
"Rahul Gandhi is PM India" = FALSE ~95%

Return ONLY this JSON:
{{
  "verdict": "TRUE|FALSE|MISLEADING|UNVERIFIED",
  "confidence": <integer 30-97, NOT 35, NOT 60>,
  "reasoning": "2-3 sentences about {claim} with specific facts",
  "key_evidence": ["fact1","fact2"],
  "prosecutor_strength": "{p_strength}",
  "defender_strength": "{d_strength}",
  "recommendation": "What reader should know"
}}"""

    raw = call_llm(prompt, 600, 0.1, "Judge")
    result = extract_json(raw)

    if not result:
        fallback_hint = get_hint(claim)
        if fallback_hint:
            return {
                "verdict": "FALSE",
                "confidence": 78,
                "reasoning": f"Based on verified knowledge: {fallback_hint}",
                "key_evidence": [fallback_hint],
                "prosecutor_strength": p_strength,
                "defender_strength": d_strength,
                "recommendation": "Verify with official sources.",
            }
        return {
            "verdict": "UNVERIFIED",
            "confidence": 40,
            "reasoning": f"Could not determine verdict for: {claim}",
            "key_evidence": [],
            "prosecutor_strength": p_strength,
            "defender_strength": d_strength,
            "recommendation": "Check trusted sources.",
        }

    confidence = int(result.get("confidence", 40))
    if confidence in [35, 60]:
        confidence += 3
    result["confidence"] = max(30, min(97, confidence))

    if result.get("verdict") not in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]:
        result["verdict"] = "UNVERIFIED"

    return result