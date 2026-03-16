from llm_client import call_llm, extract_json


def run_prosecutor(claim: str, evidence: list) -> dict:
    ev_text = "\n".join(
        [
            f"- [{article.get('source', '?')}]: {article.get('title', '')} — {article.get('content', '')[:200]}"
            for article in evidence[:3]
        ]
    ) or "No articles available."

    prompt = f"""You are a fact-checking prosecutor.

CLAIM: "{claim}"

EVIDENCE:
{ev_text}

Find arguments CONTRADICTING "{claim}".
Use your knowledge AND the evidence above.

If claim is TRUE (like "light faster than sound"):
  state that prosecution is weak.
If claim is FALSE (like "mobile used for cooking"):
  state phones are electronic communication/computing
  devices, not cooking appliances.

Return JSON ONLY:
{{
  "arguments": [
    "First specific argument against the claim",
    "Second argument with evidence or known fact"
  ],
  "strongest_point": "Most important contradiction",
  "prosecution_strength": "strong|moderate|weak|none"
}}"""

    raw = call_llm(prompt, 400, 0.1, "Prosecutor")
    result = extract_json(raw)
    if not result or not result.get("arguments"):
        return {
            "arguments": ["Insufficient evidence to prosecute"],
            "strongest_point": "Unable to find contradictions",
            "prosecution_strength": "none",
        }
    return result