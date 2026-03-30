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


def prosecute(claim, evidence, domain):
    """
    Run prosecutor agent to find arguments against the claim.
    NEVER raises — always returns a valid dict.
    """
    try:
        evidence_text = build_evidence_text(evidence)
        prompt = f"""You are a fact-checking prosecutor.
Find arguments that CONTRADICT or DISPROVE this claim.

CLAIM: \"{claim}\"

EVIDENCE:
{evidence_text}

RULES:
1. Only use evidence directly related to the claim
2. Cite which source article contradicts the claim
3. If claim appears TRUE, set prosecution_strength none
4. Do NOT fabricate arguments

Return ONLY valid JSON:
{{
  \"arguments\": [
    \"Point 1 citing [Source Name]\",
    \"Point 2 citing specific fact\"
  ],
  \"strongest_point\": \"most powerful contradiction\",
  \"prosecution_strength\": \"strong/moderate/weak/none\"
}}"""
        
        result = call_agent_json(
            prompt=prompt,
            context="prosecutor",
            temperature=0,
            num_predict=500
        )
        
        # Validate result has required fields
        if not result.get("prosecution_strength"):
            result["prosecution_strength"] = "weak"
        if not result.get("arguments"):
            result["arguments"] = [
                "Insufficient evidence to prosecute"
            ]
        if not result.get("strongest_point"):
            result["strongest_point"] = (
                "No strong contradictions found"
            )
        return result
        
    except Exception as e:
        print(f"[Prosecutor] Unexpected error: {e}")
        return {
            "arguments": ["Analysis failed"],
            "strongest_point": "Unable to analyze",
            "prosecution_strength": "none"
        }
