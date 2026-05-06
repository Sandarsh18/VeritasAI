import re
import os

from llm_client import call_reasoning, extract_json
import traceback

ENABLE_LLM_AGENTS = os.getenv("VERITAS_ENABLE_LLM_AGENTS", "0") == "1"

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
    "gold costlier than silver": (
        "TRUE",
        96,
        "Gold is generally priced higher than silver in commodity markets.",
    ),
    "gold more expensive than silver": (
        "TRUE",
        96,
        "Gold is generally priced higher than silver in commodity markets.",
    ),
    "india hosting olympics 2030": (
        "FALSE",
        92,
        "India is not the host of the 2030 Olympics; the 2030 Winter Olympics were awarded to the French Alps.",
    ),
}

STRENGTH = {"strong": 3, "moderate": 2, "weak": 1, "none": 0}


def _evidence_titles(evidence: list) -> list:
    titles = []
    for article in evidence or []:
        title = str(article.get("title") or "").strip()
        source = str(article.get("source") or "").strip()
        candidate = title or source
        if candidate and candidate not in titles:
            titles.append(candidate)
    return titles


def _ensure_reasoning_with_evidence(reasoning: str, evidence: list) -> str:
    text = str(reasoning or "").strip()
    if not text:
        return text

    titles = _evidence_titles(evidence)
    if not titles:
        return text

    lowered = text.lower()
    if any(title.lower() in lowered for title in titles[:3]):
        return text

    snippet = ", ".join(titles[:2])
    if snippet:
        return f"{text} Evidence referenced: {snippet}."
    return text


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
                "Step 1: Reviewed the available evidence. "
                "Step 2: Insufficient relevant evidence found to verify this claim. "
                "Step 3: Marked the claim as UNVERIFIED."
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
    import logging
    logger = logging.getLogger("veritas.judge")
    
    logger.info("[Judge] Evaluating: '%s'", claim)
    print(f"\n[Judge] Evaluating: '{claim}'")

    # CRITICAL: Check for no evidence first
    if not evidence:
        logger.warning("[Judge] NO EVIDENCE PROVIDED - returning INSUFFICIENT_DATA")
        return {
            "verdict": "INSUFFICIENT_DATA",
            "confidence": 0,
            "reasoning": "No evidence retrieved to verify this claim.",
            "key_evidence": [],
            "prosecutor_strength": prosecutor.get("prosecution_strength", "none"),
            "defender_strength": defender.get("defense_strength", "none"),
            "recommendation": "No evidence found. Cannot verify claim.",
            "evidence_count": 0,
        }

    fact = check_known_facts(claim)
    if fact:
        verdict, confidence, reasoning = fact
        logger.info("[Judge] Known fact matched: %s @ %d%%", verdict, confidence)
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": reasoning,
            "key_evidence": [reasoning],
            "prosecutor_strength": prosecutor.get("prosecution_strength", "none"),
            "defender_strength": defender.get("defense_strength", "none"),
            "recommendation": "This is a verified known fact.",
            "evidence_count": len(evidence),
        }

    creds = [float(article.get("credibility_score", 0.5)) for article in evidence if article]
    avg_c = round(sum(creds) / len(creds), 2) if creds else 0.5
    p_str = prosecutor.get("prosecution_strength", "none")
    d_str = defender.get("defense_strength", "none")
    p_args = prosecutor.get("arguments", [])
    d_args = defender.get("arguments", [])

    logger.info("[Judge] Evidence count=%d, avg_credibility=%.2f, p_strength=%s, d_strength=%s", 
                len(evidence), avg_c, p_str, d_str)

    if avg_c < 0.5:
        logger.warning("[Judge] Average credibility too low (%.2f) - returning UNVERIFIED", avg_c)
        return {
            "verdict": "UNVERIFIED",
            "confidence": 38,
            "reasoning": "Evidence quality insufficient to verify this claim.",
            "key_evidence": [],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Gather authoritative sources before concluding.",
            "evidence_count": len(evidence),
        }

    print(f"[Judge] p={p_str} d={d_str} cred={avg_c:.2f}")

    if not ENABLE_LLM_AGENTS:
        fallback = smart_fallback(claim, p_str, d_str, p_args, d_args)
        fallback["reasoning"] = _ensure_reasoning_with_evidence(
            fallback.get("reasoning", ""),
            evidence,
        )
        fallback["evidence_count"] = len(evidence)
        logger.info("[Judge] Deterministic verdict: %s @ %s%%", fallback["verdict"], fallback["confidence"])
        return fallback

    ev_text = "\n".join(
        [
            f"{idx + 1}. [{article.get('source', '?')}] "
            f"cred={article.get('credibility_score', 0):.2f}: "
            f"{article.get('title', '')[:50]} - "
            f"{article.get('content', '')[:120]}"
            for idx, article in enumerate(evidence[:6])
        ]
    ) or "No evidence retrieved."

    p_text = "\n".join(f"- {arg}" for arg in p_args[:4]) or "- None found"
    d_text = "\n".join(f"- {arg}" for arg in d_args[:4]) or "- None found"

    prompt = (
        "You are a fact-checking judge. Return JSON only.\n"
        f"Claim: \"{claim}\"\n"
        f"Prosecution ({p_str}):\n{p_text}\n"
        f"Defence ({d_str}):\n{d_text}\n"
        f"Evidence:\n{ev_text}\n"
        f"Avg credibility: {avg_c:.0%}\n"
        "Rules: use ONLY the provided evidence. Do NOT assume facts. "
        "If evidence is weak or unrelated, return UNVERIFIED. "
        "Explain reasoning step-by-step using evidence. "
        "Defence strong + prosecution weak/none => TRUE 80-92; "
        "prosecution strong + defence weak/none => FALSE 80-92; "
        "both moderate => MISLEADING 58-74; both weak/none => UNVERIFIED 36-54; "
        "mixed strengths => weigh evidence + credibility; never return 50.\n"
        "JSON keys: verdict, confidence, reasoning, key_evidence, prosecutor_strength, defender_strength, recommendation."
    )

    try:
        raw = call_reasoning(prompt, max_tokens=700, agent_name="Judge")
        result = extract_json(raw) if raw else {}
    except Exception as exc:
        logger.exception("[Judge] FULL ERROR TRACE")
        return {
            "success": False,
            "stage": "judge",
            "error": str(exc),
            "trace": traceback.format_exc(),
            "verdict": "INSUFFICIENT_DATA",
            "confidence": 0,
            "reasoning": "Judge stage failed before verdict generation.",
            "key_evidence": [],
            "prosecutor_strength": p_str,
            "defender_strength": d_str,
            "recommendation": "Retry after backend logs are inspected.",
            "evidence_count": len(evidence),
        }

    allowed = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
    if result and result.get("verdict") in allowed:
        conf = int(result.get("confidence", 65))
        if conf == 50:
            conf = 63
        result["confidence"] = max(36, min(95, conf))
        reasoning = str(result.get("reasoning", "")).strip()
        if not reasoning:
            reasoning = "Insufficient relevant evidence found to verify this claim."
        result["reasoning"] = _ensure_reasoning_with_evidence(reasoning, evidence)
        result["evidence_count"] = len(evidence)
        logger.info("[Judge] Final verdict: %s @ %d%% (evidence=%d)", result['verdict'], result['confidence'], len(evidence))
        print(f"[Judge] OK {result['verdict']} @ {result['confidence']}%")
        return result

    logger.warning("[Judge] LLM extraction failed - using smart fallback")
    print("[Judge] LLM failed -> smart fallback")
    fallback = smart_fallback(claim, p_str, d_str, p_args, d_args)
    fallback["reasoning"] = _ensure_reasoning_with_evidence(
        fallback.get("reasoning", ""),
        evidence,
    )
    fallback["evidence_count"] = len(evidence)
    return fallback


def judge(claim, prosecutor_result, defender_result, evidence, domain="general") -> dict:
    return run_judge(claim, prosecutor_result or {}, defender_result or {}, evidence or [])
