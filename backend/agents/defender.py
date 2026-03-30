from llm_client import call_agent_json


def build_evidence_text(evidence: list) -> str:
    lines = []
    for i, a in enumerate(evidence, 1):
        cred_pct = int(a.get("credibility_score", 0) * 100)
        lines.append(
            f"Article {i}: {a.get('title', '')}\n"
            f"  Source: {a.get('source', '')} "
            f"(credibility: {cred_pct}%)\n"
            f"  URL: {a.get('source_url', 'N/A')}\n"
            f"  Content: "
            f"{a.get('content', '')[:200]}"
        )
    return "\n\n".join(lines)


def defend(claim, evidence, domain):
    """
    Run defender agent to find arguments supporting the claim.
    NEVER raises — always returns a valid dict.
    """
    try:
        evidence_text = build_evidence_text(evidence)
        prompt = f"""You are a researcher defending a claim.
Find arguments that SUPPORT this claim.

CLAIM: \"{claim}\"

EVIDENCE:
{evidence_text}

Return ONLY valid JSON:
{{
  \"arguments\": [
    \"Supporting point 1\",
    \"Supporting point 2\"
  ],
  \"strongest_point\": \"strongest support for claim\",
  \"defense_strength\": \"strong/moderate/weak/none\"
}}"""

        result = call_agent_json(
            prompt=prompt,
            context="defender",
            temperature=0,
            num_predict=500
        )
        
        # Validate result has required fields
        if not result.get("defense_strength"):
            result["defense_strength"] = "weak"
        if not result.get("arguments"):
            result["arguments"] = [
                "Insufficient evidence to defend"
            ]
        if not result.get("strongest_point"):
            result["strongest_point"] = (
                "No strong support found"
            )
        return result
        
    except Exception as e:
        print(f"[Defender] Unexpected error: {e}")
        return {
            "arguments": ["Analysis failed"],
            "strongest_point": "Unable to analyze",
            "defense_strength": "none"
        }
