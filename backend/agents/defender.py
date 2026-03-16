from llm_client import call_llm, extract_json


def run_defender(claim: str, evidence: list) -> dict:
    ev_text = ""
    for i, article in enumerate(evidence[:4], 1):
        ev_text += (
            f"\nArticle {i}: {article.get('title', '')}\n"
            f"Source: {article.get('source', 'Unknown')}\n"
            f"Content: {article.get('content', '')[:300]}\n"
        )

    prompt = f"""You are a researcher finding support for a specific claim.

CLAIM: "{claim}"

AVAILABLE EVIDENCE:
{ev_text}

YOUR TASK: Find arguments SUPPORTING the claim: "{claim}"

CRITICAL RULES:
1. Only argue about "{claim}" specifically
2. Use your scientific/factual knowledge
3. For well-known facts like "light is faster than sound":
   - Speed of light: ~299,792,458 m/s in vacuum
   - Speed of sound: ~343 m/s in air at 20°C
   - Light travels ~874,030 times faster than sound
   - Observable: thunder seen before heard
   - This claim has VERY STRONG support

Return ONLY valid JSON:
{{
  "arguments": [
    "Strong supporting point 1 about the specific claim",
    "Supporting point 2 with evidence or known fact"
  ],
  "strongest_point": "The most powerful supporting argument",
  "defense_strength": "strong|moderate|weak|none"
}}"""

    raw = call_llm(prompt, max_tokens=400, agent_name="Defender")
    result = extract_json(raw)

    if not result or not result.get("arguments"):
        return {
            "arguments": ["No supporting evidence found"],
            "strongest_point": "No supporting evidence found",
            "defense_strength": "none",
        }

    if "defense_strength" not in result:
        result["defense_strength"] = "weak"
    return result
