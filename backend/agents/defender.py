from llm_client import call_llm, extract_json


def run_defender(claim: str, evidence: list) -> dict:
    ev_text = "\n".join(
        [
            f"- [{article.get('source', '?')}]: {article.get('title', '')} — {article.get('content', '')[:200]}"
            for article in evidence[:3]
        ]
    ) or "No articles available."

    prompt = f"""You are a researcher defending a claim.

CLAIM: "{claim}"

EVIDENCE:
{ev_text}

Find arguments SUPPORTING "{claim}".
Use your knowledge AND the evidence above.

Return JSON ONLY:
{{
  "arguments": [
    "First supporting argument",
    "Second supporting argument"
  ],
  "strongest_point": "Strongest support for claim",
  "defense_strength": "strong|moderate|weak|none"
}}"""

    raw = call_llm(prompt, 400, 0.1, "Defender")
    result = extract_json(raw)
    if not result or not result.get("arguments"):
        return {
            "arguments": ["No supporting evidence found"],
            "strongest_point": "No support found",
            "defense_strength": "none",
        }
    return result