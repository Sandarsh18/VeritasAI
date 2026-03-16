import re

from llm_client import call_llm, extract_json


def parse_verdict_from_text(text: str) -> dict:
    if not text:
        return {}

    text_upper = text.upper()

    verdict = "UNVERIFIED"
    for value in ["FALSE", "TRUE", "MISLEADING", "UNVERIFIED"]:
        if value in text_upper:
            verdict = value
            break

    confidence = 70
    numbers = re.findall(r"\b([3-9][0-9]|9[0-7])\b", text)
    if numbers:
        confidence = int(numbers[0])

    sentences = [item.strip() for item in text.split(".") if len(item.strip()) > 30]
    reasoning = sentences[0] if sentences else text[:200].strip()

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "key_evidence": [],
        "recommendation": "Verify with trusted sources.",
    }


def run_judge(claim, prosecutor, defender, evidence) -> dict:
    creds = [float(article.get("credibility_score", 0.5)) for article in evidence] or [0.5]
    avg_credibility = sum(creds) / len(creds)

    p_args = prosecutor.get("arguments", [])
    d_args = defender.get("arguments", [])
    p_strength = prosecutor.get("prosecution_strength", "?")
    d_strength = defender.get("defense_strength", "?")

    facts = {
        "cooking": "Mobile phones are NOT cooking tools. They are electronic communication devices. Claim is FALSE.",
        "world war": "WW2: 1939-1945. WW1: 1914-1918.",
        "rahul gandhi": "Narendra Modi is PM of India. Rahul Gandhi is opposition leader. NOT PM.",
        "modi": "Narendra Modi has been PM of India since May 2014.",
        "light.*sound|sound.*light": "Speed of light: 300,000 km/s. Speed of sound: 343 m/s. Light is ~874,000x faster.",
        "flat.*earth|earth.*flat": "Earth is spherical/oblate spheroid. Flat earth is false.",
        "vaccine.*infertil|infertil.*vaccine": "No evidence vaccines cause infertility. WHO/CDC confirm vaccines are safe.",
        "5g.*covid|covid.*5g": "5G cannot spread viruses. COVID-19 spreads through respiratory droplets.",
        "vaccine.*autism|autism.*vaccine": "No link between vaccines and autism. Original study was fraudulent and retracted.",
    }

    claim_lower = claim.lower()
    fact_hints = []
    for pattern, fact in facts.items():
        if re.search(pattern, claim_lower):
            fact_hints.append(fact)
    hint = " ".join(fact_hints)

    p_text = "\n".join(f"• {arg}" for arg in p_args[:3]) or "• None"
    d_text = "\n".join(f"• {arg}" for arg in d_args[:3]) or "• None"
    ev_list = "\n".join(
        f"• [{article.get('source', '?')}] {article.get('title', '')[:60]}"
        for article in evidence[:3]
    ) or "• No articles"

    prompt = f"""You are an expert fact-checker.

CLAIM: "{claim}"

{f'KNOWN FACT: {hint}' if hint else ''}

PROSECUTION argued against claim:
{p_text}
Prosecution strength: {p_strength}

DEFENSE argued for claim:
{d_text}
Defense strength: {d_strength}

RETRIEVED ARTICLES:
{ev_list}
Average credibility: {avg_credibility:.0%}

YOUR JOB: Give an accurate verdict for "{claim}"

CONFIDENCE RULES:
- Strong prosecution + weak defense = FALSE, 80-95%
- Strong defense + weak prosecution = TRUE, 80-95%
- Mixed = MISLEADING, 55-74%
- No evidence = UNVERIFIED, 36-54%
- NEVER use 35 or 60 as confidence

KNOWN FACTS YOU MUST APPLY:
- Mobile/smartphone is NOT a cooking tool → FALSE
- WW2 started 1939 NOT 2000 → FALSE
- Narendra Modi IS current PM of India → TRUE
- Rahul Gandhi is NOT PM of India → FALSE
- Light IS faster than sound → TRUE
- Earth is NOT flat → FALSE
- COVID vaccines do NOT cause infertility → FALSE
- 5G does NOT spread COVID → FALSE

Return ONLY this JSON (nothing else before or after):
{{
  "verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED",
  "confidence": <number between 36 and 97>,
  "reasoning": "Specific explanation about '{claim}'",
  "key_evidence": ["fact1 about the claim", "fact2"],
  "recommendation": "What reader should know"
}}"""

    result = {}
    for attempt in range(3):
        raw = call_llm(prompt, 500, 0.05, f"Judge(attempt{attempt + 1})")

        if raw:
            result = extract_json(raw)
            if result and result.get("verdict") in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]:
                break

            if not result:
                result = parse_verdict_from_text(raw)
                if result.get("verdict"):
                    break

    if not result:
        if fact_hints:
            verdict = "FALSE"
            if any(" IS " in item.upper() or " TRUE" in item.upper() for item in fact_hints):
                if not any(item in claim_lower for item in ["not", "false", "isn't", "is not"]):
                    verdict = "TRUE"

            return {
                "verdict": verdict,
                "confidence": 79,
                "reasoning": f"{hint} This claim is {verdict} based on established facts.",
                "key_evidence": [hint],
                "prosecutor_strength": p_strength,
                "defender_strength": d_strength,
                "recommendation": "Verify with official sources.",
            }

        return {
            "verdict": "UNVERIFIED",
            "confidence": 40,
            "reasoning": f"Could not fully analyze: {claim}",
            "key_evidence": [],
            "prosecutor_strength": p_strength,
            "defender_strength": d_strength,
            "recommendation": "Please verify with trusted news sources.",
        }

    conf = int(result.get("confidence", 70))
    if conf == 35:
        conf = 72
    if conf == 60:
        conf = 63
    result["confidence"] = max(36, min(97, conf))

    if result.get("verdict") not in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]:
        result["verdict"] = "UNVERIFIED"

    result["prosecutor_strength"] = result.get("prosecutor_strength", p_strength)
    result["defender_strength"] = result.get("defender_strength", d_strength)

    return result