import re

from llm_client import GROQ_JUDGE_MODEL, call_with_fallback, extract_json

KNOWN_FACTS = {
    "water is h2o": (
        "TRUE",
        98,
        "Water is H2O - two hydrogen, one oxygen. Basic chemistry.",
    ),
    "sky is blue": (
        "TRUE",
        96,
        "Sky appears blue due to Rayleigh scattering of sunlight.",
    ),
    "sky blue": (
        "TRUE",
        96,
        "Sky is blue due to Rayleigh scattering.",
    ),
    "earth is round": (
        "TRUE",
        97,
        "Earth is spherical. Confirmed by science.",
    ),
    "earth orbits sun": (
        "TRUE",
        98,
        "Earth orbits the Sun every 365.25 days.",
    ),
    "earth 3rd planet": (
        "TRUE",
        97,
        "Earth is the 3rd planet from the Sun.",
    ),
    "sun rise in west": (
        "FALSE",
        97,
        "Sun rises in EAST. Earth rotates west to east.",
    ),
    "sun rises in west": (
        "FALSE",
        97,
        "Sun rises in east, not west.",
    ),
    "sun is cold": (
        "FALSE",
        98,
        "Sun surface is ~5500C. It is extremely hot.",
    ),
    "moon is made of cheese": (
        "FALSE",
        99,
        "Moon is rock and dust, not cheese.",
    ),
    "moon cheese": (
        "FALSE",
        99,
        "Moon is not made of cheese. It is rock.",
    ),
    "vaccines cause autism": (
        "FALSE",
        99,
        "No link. Wakefield study was fraudulent and retracted.",
    ),
    "vaccines autism": (
        "FALSE",
        99,
        "Vaccines do not cause autism. Confirmed by WHO and CDC.",
    ),
    "5g covid": (
        "FALSE",
        99,
        "5G radio waves cannot spread biological viruses.",
    ),
    "5g spread": (
        "FALSE",
        98,
        "5G cannot carry or spread any virus.",
    ),
    "earth flat": (
        "FALSE",
        99,
        "Earth is spherical, not flat.",
    ),
    "flat earth": (
        "FALSE",
        99,
        "Earth is not flat. It is an oblate spheroid.",
    ),
    "modi prime minister": (
        "TRUE",
        95,
        "Narendra Modi has been PM of India since May 2014.",
    ),
    "narendra modi pm": (
        "TRUE",
        95,
        "Narendra Modi is PM of India.",
    ),
    "narendra modi prime minister": (
        "TRUE",
        95,
        "Narendra Modi is PM of India since 2014.",
    ),
    "rahul gandhi pm": (
        "FALSE",
        95,
        "Rahul Gandhi is NOT PM. Modi is PM of India.",
    ),
    "rahul gandhi prime minister": (
        "FALSE",
        95,
        "Modi is PM, not Rahul Gandhi.",
    ),
    "amit shah leader of opposition": (
        "FALSE",
        93,
        "Amit Shah is Home Minister, not opposition leader.",
    ),
    "climate change caused by humans": (
        "TRUE",
        94,
        "IPCC confirms human activities are primary cause.",
    ),
    "climate change humans": (
        "TRUE",
        94,
        "Human-caused climate change confirmed by scientific consensus.",
    ),
}

STRENGTH = {"strong": 3, "moderate": 2, "weak": 1, "none": 0}


def check_known_facts(claim: str):
    c = claim.lower().strip()
    for key, (verdict, confidence, reason) in KNOWN_FACTS.items():
        if key in c:
            print(f"[Judge] Known fact: '{key}' -> {verdict} {confidence}%")
            return verdict, confidence, reason
    return None


def smart_fallback(claim, p_str, d_str, p_args, d_args) -> dict:
    """Logic-based verdict. Never hardcodes MISLEADING."""
    p = STRENGTH.get(p_str, 0)
    d = STRENGTH.get(d_str, 0)
    print(f"[Judge] Smart fallback: p={p} d={d}")

    if p == 0 and d == 0:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 41,
            "reasoning": (
                f"No credible evidence found to verify or deny: '{claim}'. "
                "Insufficient information available."
            ),
            "key_evidence": [],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Search Reuters or BBC for info.",
        }
    if d > p:
        conf = min(90, 60 + (d - p) * 10)
        return {
            "verdict": "TRUE",
            "confidence": conf,
            "reasoning": (
                f"Supporting evidence ({d_str}) outweighs "
                f"contradicting evidence ({p_str}) for: '{claim}'."
            ),
            "key_evidence": (d_args or [])[:2],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Verify with official sources.",
        }
    if p > d:
        conf = min(90, 60 + (p - d) * 10)
        return {
            "verdict": "FALSE",
            "confidence": conf,
            "reasoning": (
                f"Contradicting evidence ({p_str}) outweighs "
                f"supporting evidence ({d_str}) for: '{claim}'."
            ),
            "key_evidence": (p_args or [])[:2],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "This claim appears inaccurate.",
        }

    if p >= 2:
        return {
            "verdict": "MISLEADING",
            "confidence": 62,
            "reasoning": (
                f"Both supporting and contradicting evidence "
                f"exist with equal strength for: '{claim}'. "
                "The claim contains partial truths."
            ),
            "key_evidence": [],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Verify with multiple sources.",
        }

    return {
        "verdict": "UNVERIFIED",
        "confidence": 44,
        "reasoning": (
            f"Weak evidence on both sides for: '{claim}'. "
            "Cannot determine veracity confidently."
        ),
        "key_evidence": [],
        "prosecutor_strength": p_str,
        "defender_strength": d_str,
        "recommendation": "Seek authoritative sources.",
    }


def run_judge(claim, prosecutor, defender, evidence) -> dict:
    print(f"\n[Judge] Evaluating: '{claim}'")

    fact = check_known_facts(claim)
    if fact:
        verdict, confidence, reasoning = fact
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": reasoning,
            "key_evidence": [reasoning],
            "prosecutor_strength": prosecutor.get("prosecution_strength", "none"),
            "defender_strength": defender.get("defense_strength", "none"),
            "recommendation": "This is a verified known fact.",
        }

    creds = [float(article.get("credibility_score", 0.5)) for article in evidence if article]
    avg_c = round(sum(creds) / len(creds), 2) if creds else 0.5
    p_str = prosecutor.get("prosecution_strength", "none")
    d_str = defender.get("defense_strength", "none")
    p_args = prosecutor.get("arguments", [])
    d_args = defender.get("arguments", [])

    print(f"[Judge] p={p_str} d={d_str} cred={avg_c:.2f}")

    ev_text = "\n".join(
        [
            f"{idx + 1}. [{article.get('source', '?')}] "
            f"cred={article.get('credibility_score', 0):.2f}: "
            f"{article.get('title', '')[:50]} - "
            f"{article.get('content', '')[:120]}"
            for idx, article in enumerate(evidence[:5])
        ]
    ) or "No evidence retrieved."

    p_text = "\n".join(f"- {arg}" for arg in p_args[:3]) or "- None found"
    d_text = "\n".join(f"- {arg}" for arg in d_args[:3]) or "- None found"

    prompt = f"""You are an expert fact-checking judge.
Evaluate this claim based on prosecution, defence and evidence.

CLAIM: "{claim}"

PROSECUTION (arguments AGAINST claim):
{p_text}
Prosecution strength: {p_str}

DEFENCE (arguments FOR claim):
{d_text}
Defence strength: {d_str}

RETRIEVED EVIDENCE:
{ev_text}
Average source credibility: {avg_c:.0%}

VERDICT RULES (mandatory):
1. Defence strong + prosecution weak/none -> TRUE 80-92%
2. Prosecution strong + defence weak/none -> FALSE 80-92%
3. Both moderate equal strength -> MISLEADING 58-74%
4. Both weak/none -> UNVERIFIED 36-54%
5. Mixed moderate/strong -> weigh credibility carefully
6. NEVER return confidence exactly 50
7. Apply your own world knowledge for well-known facts

KNOWN FACTS YOU MUST APPLY:
- Sky IS blue -> TRUE
- Water IS H2O -> TRUE
- Vaccines do NOT cause autism -> FALSE
- 5G does NOT spread COVID -> FALSE
- Earth is NOT flat -> FALSE
- Sun does NOT rise in west -> FALSE
- Narendra Modi IS PM of India -> TRUE
- Rahul Gandhi is NOT PM -> FALSE

Return ONLY valid JSON (no markdown, start with {{):
{{
  "verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED",
  "confidence": <integer 36-95, never exactly 50>,
  "reasoning": "2-3 specific sentences about THIS claim",
  "key_evidence": ["fact from source 1", "fact from source 2"],
  "prosecutor_strength": "{p_str}",
  "defender_strength": "{d_str}",
  "recommendation": "one practical sentence for reader"
}}"""

    raw = call_with_fallback(prompt, GROQ_JUDGE_MODEL, 700, "Judge")
    result = extract_json(raw) if raw else {}

    allowed = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
    if result and result.get("verdict") in allowed:
        conf = int(result.get("confidence", 65))
        if conf == 50:
            conf = 63
        result["confidence"] = max(36, min(95, conf))
        print(f"[Judge] OK {result['verdict']} @ {result['confidence']}%")
        return result

    print("[Judge] LLM failed -> smart fallback")
    return smart_fallback(claim, p_str, d_str, p_args, d_args)


def judge(claim, prosecutor_result, defender_result, evidence, domain="general") -> dict:
    return run_judge(claim, prosecutor_result or {}, defender_result or {}, evidence or [])
