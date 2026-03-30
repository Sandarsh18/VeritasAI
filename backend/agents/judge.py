from llm_client import call_judge_json, _emergency_verdict

KNOWN_FACTS = {
    "ww3": "No WW3 currently. Regional conflicts only.",
    "world war 3": "No WW3 declared by any nation.",
    "gold rate": (
        "Gold dropped ~Rs 4000/10g in India "
        "in early 2026 per MCX data."
    ),
    "gold price": (
        "Gold prices in India fell Rs 3900-4100 "
        "per 10g in March 2026."
    ),
    "5g covid": "5G cannot spread COVID-19. WHO confirmed.",
    "5g coronavirus": "5G-COVID link is false. WHO debunked.",
    "earth flat": "Earth is spherical. Flat earth is false.",
    "vaccines autism": (
        "No vaccine-autism link. "
        "Original study retracted."
    ),
    "speed of light": (
        "Light: 299,792 km/s. "
        "Faster than sound (343 m/s)."
    ),
}

def judge(claim, prosecutor_result, defender_result, evidence, domain) -> dict:
    """
    Judge agent to deliver final verdict on a claim.
    NEVER raises — always returns a valid dict.
    """
    try:
        # Build hint from KNOWN_FACTS
        hint = ""
        hint_section = ""
        claim_lower = claim.lower()
        for key, fact in KNOWN_FACTS.items():
            if key in claim_lower:
                hint = fact
                hint_section = (
                    f"VERIFIED FACT (use this): {fact}"
                )
                break
        
        # Calculate evidence credibility
        cred_scores = [
            a.get("credibility_score", 0.5)
            for a in evidence
        ] or [0.5]
        avg_cred = sum(cred_scores) / len(cred_scores)
        
        p_strength = prosecutor_result.get(
            "prosecution_strength", "none")
        d_strength = defender_result.get(
            "defense_strength", "none")
        p_args = prosecutor_result.get("arguments", [])
        d_args = defender_result.get("arguments", [])
        
        # Build evidence text
        ev_lines = []
        for i, a in enumerate(evidence, 1):
            cred_pct = int(
                a.get("credibility_score", 0) * 100)
            ev_lines.append(
                f"Source {i}: {a.get('title','')}\n"
                f"  From: {a.get('source','')} "
                f"({cred_pct}% credibility)\n"
                f"  URL: {a.get('source_url','')}\n"
                f"  Content: "
                f"{a.get('content','')[:150]}"
            )
        evidence_text = "\n\n".join(ev_lines) or \
                        "No external evidence retrieved."
        
        prompt = f"""You are a strict impartial 
fact-checking judge. Return ONLY a JSON object.

CLAIM: "{claim}"
DOMAIN: {domain}

{hint_section}

PROSECUTION (against claim):
{chr(10).join(f"• {a}" for a in p_args)}
Strength: {p_strength}

DEFENSE (for claim):
{chr(10).join(f"• {a}" for a in d_args)}
Strength: {d_strength}

EVIDENCE SOURCES:
{evidence_text}

SOURCE CREDIBILITY AVG: {avg_cred:.2f}/1.0

VERDICT RULES:
- If VERIFIED FACT is provided above, it overrides 
  all other inputs — use it for your verdict
- Strong prosecution + weak defense → FALSE 80-95%
- Strong defense + weak prosecution → TRUE 80-95%
- Both moderate → MISLEADING 55-74%
- Both weak + no credible sources → UNVERIFIED 36-54%
- NEVER use confidence exactly 35 or 60

Return ONLY this JSON object, nothing else:
{{
  "verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED",
  "confidence": <integer 36-97>,
  "reasoning": "2-3 sentences citing specific sources",
  "key_evidence": ["fact 1", "fact 2"],
  "prosecutor_strength": "{p_strength}",
  "defender_strength": "{d_strength}",
  "recommendation": "one sentence for the reader"
}}"""
        
        result = call_judge_json(
            prompt=prompt,
            claim=claim,
            hint=hint
        )
        
        return result
        
    except Exception as e:
        print(f"[Judge] Unexpected error: {e}")
        # Last resort emergency fallback
        return _emergency_verdict(claim, "")
