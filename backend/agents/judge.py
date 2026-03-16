from llm_client import call_llm, extract_json


def run_judge(claim: str, prosecutor: dict, defender: dict, evidence: list) -> dict:
    cred_scores = [float(article.get("credibility_score", 0.5)) for article in evidence]
    avg_cred = round(sum(cred_scores) / len(cred_scores), 2) if cred_scores else 0.5

    p_strength = prosecutor.get("prosecution_strength", "unknown")
    d_strength = defender.get("defense_strength", "unknown")

    p_args = "\n".join([f"  - {item}" for item in prosecutor.get("arguments", [])[:3]])
    d_args = "\n".join([f"  - {item}" for item in defender.get("arguments", [])[:3]])

    prompt = f"""You are an impartial fact-checking judge with expertise in science, politics, and current events.

THE CLAIM: "{claim}"

PROSECUTION ARGUED (AGAINST claim):
{p_args or "  - No strong contradictions found"}
Prosecution strength: {p_strength}

DEFENSE ARGUED (FOR claim):
{d_args or "  - No supporting arguments found"}
Defense strength: {d_strength}

AVERAGE SOURCE CREDIBILITY: {avg_cred:.0%}

YOUR TASK: Deliver an accurate, evidence-based verdict SPECIFICALLY about: "{claim}"

VERDICT RULES:
- TRUE:        Claim is factually correct
- FALSE:       Claim is factually incorrect
- MISLEADING:  Claim is partially true but exaggerated
- UNVERIFIED:  Cannot determine with available evidence

CONFIDENCE RULES:
- Defense strong, prosecution weak → TRUE, 80-95%
- Prosecution strong, defense weak → FALSE, 80-95%
- Both sides moderate → MISLEADING, 55-75%
- Both sides weak → UNVERIFIED, 30-50%
- NEVER return exactly 60

IMPORTANT: Use your knowledge.
"Light is faster than sound" is TRUE (scientific consensus).
"Rahul Gandhi is PM of India" is FALSE (Modi is PM).

Return ONLY this exact JSON:
{{
  "verdict": "TRUE|FALSE|MISLEADING|UNVERIFIED",
  "confidence": <integer 30-97, NEVER 60>,
  "reasoning": "2-3 sentences specifically about '{claim}' with factual explanation",
  "key_evidence": [
    "Most important fact supporting the verdict",
    "Second important fact"
  ],
  "prosecutor_strength": "{p_strength}",
  "defender_strength": "{d_strength}",
  "recommendation": "One sentence: what should reader know about this claim"
}}"""

    raw = call_llm(prompt, max_tokens=500, temperature=0.1, agent_name="Judge")
    result = extract_json(raw)

    if not result:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 35,
            "reasoning": f"Unable to determine verdict for: {claim}",
            "key_evidence": [],
            "prosecutor_strength": p_strength,
            "defender_strength": d_strength,
            "recommendation": "Please verify with trusted sources.",
        }

    conf = int(result.get("confidence", 35))
    if conf == 60:
        conf = 61
    result["confidence"] = max(30, min(97, conf))

    allowed = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
    if result.get("verdict") not in allowed:
        result["verdict"] = "UNVERIFIED"

    return result

