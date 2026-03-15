PROMPT_TEMPLATE = """You are an impartial fact-checking judge.

THE CLAIM BEING JUDGED: '{claim}'

PROSECUTOR ARGUED (against claim):
{prosecutor_arguments}

DEFENDER ARGUED (for claim):
{defender_arguments}

SOURCE CREDIBILITY SCORES: {credibility_info}

YOUR TASK:
Deliver a verdict SPECIFICALLY about: '{claim}'

STRICT RULES:
1. Your verdict MUST be about '{claim}' only
2. Your reasoning MUST mention '{claim}' specifically
3. Your recommendation MUST relate to '{claim}'
4. Do NOT mention topics unrelated to '{claim}'
5. If evidence is insufficient -> verdict = UNVERIFIED
"""


def _meaningful_arguments(arguments: list[str]) -> list[str]:
    meaningful = []
    for argument in arguments or []:
        text = str(argument).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered.startswith("no contradicting evidence") or lowered.startswith("no supporting evidence"):
            continue
        meaningful.append(text)
    return meaningful


def _compute_verdict(contra_count: int, support_count: int, avg_credibility: float) -> tuple[str, int]:
    if contra_count == 0 and support_count == 0:
        confidence = min(48, 34 + int(avg_credibility * 10))
        return "UNVERIFIED", 61 if confidence == 60 else confidence
    if contra_count >= support_count + 1:
        confidence = min(90, 72 + (contra_count - support_count) * 6 + int(avg_credibility * 8))
        return "FALSE", 61 if confidence == 60 else confidence
    if support_count >= contra_count + 1:
        confidence = min(90, 72 + (support_count - contra_count) * 6 + int(avg_credibility * 8))
        return "TRUE", 61 if confidence == 60 else confidence
    confidence = min(78, 50 + int(avg_credibility * 10))
    return "MISLEADING", 61 if confidence == 60 else confidence


def _reasoning(claim: str, verdict: str, contra_count: int, support_count: int) -> str:
    if verdict == "FALSE":
        return f"The retrieved evidence about '{claim}' is predominantly contradicting, with {contra_count} contradicting points and {support_count} supporting points. Based on the available articles, this claim is not supported."
    if verdict == "TRUE":
        return f"The retrieved evidence about '{claim}' is predominantly supportive, with {support_count} supporting points and {contra_count} contradicting points. Based on the available articles, this claim is supported."
    if verdict == "MISLEADING":
        return f"The retrieved evidence about '{claim}' is mixed, with both supportive and contradicting details present. The claim needs more precise wording because the available articles do not support it cleanly in its current form."
    return f"The retrieved evidence about '{claim}' is insufficient or too weak for a reliable verdict. This claim should remain unverified until stronger claim-specific evidence is available."


def _recommendation(claim: str, verdict: str) -> str:
    if verdict == "FALSE":
        return f"Do not rely on '{claim}' unless you can provide stronger evidence from primary or highly credible sources."
    if verdict == "TRUE":
        return f"'{claim}' is supported by the current evidence, but you should still prefer primary or official sources when sharing it."
    if verdict == "MISLEADING":
        return f"Refine '{claim}' into a narrower statement so it can be checked against a more precise evidence base."
    return f"Look for more claim-specific evidence before drawing conclusions about '{claim}'."


def judge(claim: str, prosecutor_result: dict, defender_result: dict, avg_credibility: float) -> dict:
    prosecutor_points = _meaningful_arguments(prosecutor_result.get("arguments", []))
    defender_points = _meaningful_arguments(defender_result.get("arguments", []))
    contra_count = len(prosecutor_points)
    support_count = len(defender_points)
    verdict, confidence = _compute_verdict(contra_count, support_count, avg_credibility)
    key_evidence = (prosecutor_points + defender_points)[:2]

    return {
        "verdict": verdict,
        "confidence": max(30, min(97, confidence)),
        "reasoning": _reasoning(claim, verdict, contra_count, support_count),
        "key_evidence": key_evidence,
        "recommendation": _recommendation(claim, verdict),
    }


run_judge = judge

