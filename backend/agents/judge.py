"""
judge.py
Uses call_judge_llm() which tries:
  Gemini -> DeepSeek -> Ollama
Logic fallback NEVER returns MISLEADING by default.
"""

from llm_client import call_judge_llm, extract_json

KNOWN_FACTS = {
    "water is h2o": ("TRUE", 98, "Water is H2O - two hydrogen atoms, one oxygen."),
    "sky is blue": ("TRUE", 96, "Sky appears blue due to Rayleigh scattering."),
    "sky blue": ("TRUE", 96, "Sky is blue due to Rayleigh scattering of sunlight."),
    "earth is round": ("TRUE", 97, "Earth is an oblate spheroid - essentially round."),
    "earth orbits sun": ("TRUE", 98, "Earth orbits the Sun every 365.25 days."),
    "earth 3rd planet": ("TRUE", 97, "Earth is 3rd planet from the Sun."),
    "sun rise in west": ("FALSE", 97, "Sun rises in EAST, not west. Basic geography."),
    "sun rises in west": ("FALSE", 97, "Sun rises in east. Earth rotates west to east."),
    "sun is cold": ("FALSE", 98, "Sun surface is ~5500C. Not cold."),
    "moon is made of cheese": ("FALSE", 99, "Moon is rock and dust. Not cheese."),
    "vaccines cause autism": ("FALSE", 99, "No link. Original Wakefield study retracted."),
    "vaccines autism": ("FALSE", 99, "Vaccines do not cause autism. Proven by WHO."),
    "5g covid": ("FALSE", 99, "5G cannot spread biological viruses."),
    "5g spread": ("FALSE", 98, "Radio waves cannot carry viruses."),
    "earth flat": ("FALSE", 99, "Earth is spherical. Proven science."),
    "flat earth": ("FALSE", 99, "Earth is not flat. Oblate spheroid shape."),
    "modi prime minister": ("TRUE", 95, "Narendra Modi has been PM of India since 2014."),
    "narendra modi pm": ("TRUE", 95, "Narendra Modi is PM of India."),
    "rahul gandhi pm": ("FALSE", 95, "Rahul Gandhi is NOT PM. Modi is PM."),
    "rahul gandhi prime minister": ("FALSE", 95, "Modi is PM, not Rahul Gandhi."),
    "amit shah leader of opposition": ("FALSE", 93, "Amit Shah is Home Minister, not opposition leader."),
    "climate change caused by humans": ("TRUE", 94, "IPCC confirms human activities cause climate change."),
}

STRENGTH = {"strong": 3, "moderate": 2, "weak": 1, "none": 0}


def check_known_facts(claim: str):
    c = (claim or "").lower().strip()

    if "narendra" in c and "modi" in c and ("pm" in c or "prime minister" in c):
        return "TRUE", 95, "Narendra Modi is the Prime Minister of India."

    if "rahul" in c and "gandhi" in c and ("pm" in c or "prime minister" in c):
        return "FALSE", 95, "Rahul Gandhi is not the Prime Minister of India."

    for key, (verdict, conf, reason) in KNOWN_FACTS.items():
        if key in c:
            print(f"[Judge] Known fact match: '{key}' -> {verdict} {conf}%")
            return verdict, conf, reason
    return None


def logic_fallback(claim, p_str, d_str, p_args, d_args, avg_cred) -> dict:
    """
    Smart logic fallback based on argument strengths.
    NEVER defaults to MISLEADING just because LLM failed.
    """
    p = STRENGTH.get(p_str, 0)
    d = STRENGTH.get(d_str, 0)

    print(f"[Judge] Logic fallback: p={p}({p_str}) d={d}({d_str}) cred={avg_cred:.2f}")

    if p == 0 and d == 0:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 41,
            "reasoning": (
                f"No credible evidence found to confirm or deny: '{claim}'. "
                "Both agents found insufficient information."
            ),
            "key_evidence": [],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Search Reuters, BBC, or WHO for verified information on this claim.",
        }

    if d > p:
        conf = min(88, 60 + (d - p) * 9)
        return {
            "verdict": "TRUE",
            "confidence": conf,
            "reasoning": (
                f"Supporting evidence outweighs contradicting evidence for '{claim}'. "
                f"Defense strength: {d_str}, Prosecution strength: {p_str}."
            ),
            "key_evidence": d_args[:2],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Verify with official sources.",
        }

    if p > d:
        conf = min(88, 60 + (p - d) * 9)
        return {
            "verdict": "FALSE",
            "confidence": conf,
            "reasoning": (
                f"Contradicting evidence outweighs supporting evidence for '{claim}'. "
                f"Prosecution strength: {p_str}, Defense strength: {d_str}."
            ),
            "key_evidence": p_args[:2],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "This claim appears inaccurate.",
        }

    if p >= 2:
        return {
            "verdict": "MISLEADING",
            "confidence": 62,
            "reasoning": (
                f"Both supporting and contradicting evidence exist for '{claim}' with similar strength. "
                "The claim contains partial truths."
            ),
            "key_evidence": [],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Verify with multiple sources.",
        }

    return {
        "verdict": "UNVERIFIED",
        "confidence": 43,
        "reasoning": (
            f"Insufficient evidence to verify '{claim}'. "
            "Both prosecution and defense found weak evidence only."
        ),
        "key_evidence": [],
        "prosecutor_strength": p_str,
        "defender_strength": d_str,
        "recommendation": "Seek authoritative sources.",
    }


def run_judge(claim, prosecutor, defender, evidence) -> dict:
    print(f"\n[Judge] Evaluating: '{claim}'")

    # Step 1: Known facts check
    fact = check_known_facts(claim)
    if fact:
        verdict, conf, reasoning = fact
        return {
            "verdict": verdict,
            "confidence": conf,
            "reasoning": reasoning,
            "key_evidence": [reasoning],
            "prosecutor_strength": prosecutor.get("prosecution_strength", "none"),
            "defender_strength": defender.get("defense_strength", "none"),
            "recommendation": "Verified established fact.",
        }

    # Step 2: Calculate metrics
    creds = [float(a.get("credibility_score", 0.5)) for a in evidence if a]
    avg_c = round(sum(creds) / len(creds), 2) if creds else 0.5
    p_str = prosecutor.get("prosecution_strength", "none")
    d_str = defender.get("defense_strength", "none")
    p_args = prosecutor.get("arguments", [])
    d_args = defender.get("arguments", [])

    print(f"[Judge] p={p_str} d={d_str} avg_cred={avg_c:.2f} evidence={len(evidence)}")

    # Step 3: Build evidence text
    ev_text = "\n".join(
        [
            f"{i + 1}. [{a.get('source', '?')}] cred={float(a.get('credibility_score', 0)):.2f}: "
            f"{a.get('title', '')[:50]} - {a.get('content', '')[:100]}"
            for i, a in enumerate(evidence[:5])
        ]
    ) or "No evidence retrieved."

    p_text = "\n".join(f"- {a}" for a in p_args[:3]) or "- No contradictions found"
    d_text = "\n".join(f"- {a}" for a in d_args[:3]) or "- No support found"

    # Step 4: Judge prompt
    prompt = f"""You are an expert fact-checking judge.

CLAIM: "{claim}"

PROSECUTION ARGUED AGAINST:
{p_text}
Prosecution strength: {p_str}

DEFENSE ARGUED FOR:
{d_text}
Defense strength: {d_str}

EVIDENCE RETRIEVED:
{ev_text}
Average credibility: {avg_c:.0%}

VERDICT LOGIC (follow strictly):
- Defense strong + prosecution weak/none -> TRUE 80-92%
- Prosecution strong + defense weak/none -> FALSE 80-92%
- Both moderate strength -> MISLEADING 58-74%
- Both weak or none -> UNVERIFIED 36-54%
- NEVER return empty verdict string
- NEVER return confidence 50 exactly
- Use your own world knowledge for well-known facts

MANDATORY FACTS:
- Narendra Modi IS PM of India -> TRUE
- Rahul Gandhi is NOT PM -> FALSE
- Vaccines do NOT cause autism -> FALSE
- 5G does NOT spread COVID -> FALSE
- Earth is NOT flat -> FALSE
- Sky IS blue -> TRUE
- Water IS H2O -> TRUE

Return ONLY valid JSON (no markdown, no other text):
{{
  "verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED",
  "confidence": <integer 36-95, NOT 50>,
  "reasoning": "2-3 specific sentences about this claim",
  "key_evidence": ["specific fact 1", "specific fact 2"],
  "prosecutor_strength": "{p_str}",
  "defender_strength": "{d_str}",
  "recommendation": "one practical sentence"
}}"""

    # Step 5: Call LLM chain
    raw = call_judge_llm(prompt, "Judge")
    result = extract_json(raw) if raw else {}

    # Step 6: Validate result
    allowed = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
    verdict = str(result.get("verdict", "")).upper()
    if result and verdict in allowed:
        conf = int(result.get("confidence", 65))
        if conf == 50:
            conf = 63
        result["verdict"] = verdict
        result["confidence"] = max(36, min(95, conf))
        print(f"[Judge] {result['verdict']} @ {result['confidence']}%")
        return result

    # Step 7: Logic fallback (smart, not hardcoded)
    print("[Judge] LLM result invalid, using logic fallback")
    return logic_fallback(claim, p_str, d_str, p_args, d_args, avg_c)


def judge(claim, prosecutor_result, defender_result, evidence, domain="general") -> dict:
    """Compatibility wrapper for older callers."""
    return run_judge(claim, prosecutor_result or {}, defender_result or {}, evidence or [])
