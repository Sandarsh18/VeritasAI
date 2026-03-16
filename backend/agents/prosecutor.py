from llm_client import call_llm, extract_json


def run_prosecutor(claim: str, evidence: list) -> dict:
    ev_text = ""
    for i, article in enumerate(evidence[:4], 1):
        ev_text += (
            f"\nArticle {i}: {article.get('title', '')}\n"
            f"Source: {article.get('source', 'Unknown')} (credibility: {float(article.get('credibility_score', 0.5)):.0%})\n"
            f"Content: {article.get('content', '')[:300]}\n"
        )

    if not ev_text:
        ev_text = "No specific articles available."

    prompt = f"""You are a rigorous fact-checking prosecutor.

CLAIM TO ANALYZE: "{claim}"

AVAILABLE EVIDENCE:
{ev_text}

YOUR TASK: Find arguments that CONTRADICT or DISPROVE the claim: "{claim}"

CRITICAL RULES:
1. Only argue about "{claim}" specifically
2. Only cite evidence directly related to this claim
3. If evidence is about a different topic, ignore it
4. Use your knowledge + the evidence provided
5. Be factually accurate — do not fabricate

For scientific claims like "light is faster than sound":
- Use known scientific facts (speed of light ~300,000 km/s, speed of sound ~343 m/s in air)
- This would be a VERY WEAK prosecution (claim is true)

Return ONLY valid JSON:
{{
  "arguments": [
    "Specific point 1 directly about the claim",
    "Specific point 2 with source citation if available"
  ],
  "strongest_point": "The most important contradicting argument, or 'No strong contradictions found' if claim appears true",
  "prosecution_strength": "strong|moderate|weak|none"
}}"""

    raw = call_llm(prompt, max_tokens=400, agent_name="Prosecutor")
    result = extract_json(raw)

    if not result or not result.get("arguments"):
        return {
            "arguments": ["No strong contradicting evidence found"],
            "strongest_point": "No strong contradictions found",
            "prosecution_strength": "none",
        }

    if "prosecution_strength" not in result:
        result["prosecution_strength"] = "weak"
    return result
