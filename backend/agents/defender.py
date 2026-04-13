from llm_client import GROQ_DEFENDER_MODEL, call_with_fallback, extract_json


def run_defender(claim: str, evidence: list) -> dict:
    ev_text = ""
    for i, article in enumerate(evidence[:4], 1):
        title = article.get("title", "No title")
        source = article.get("source", "Unknown")
        content = article.get("content", "")[:350]
        ev_text += (
            f"\nARTICLE {i} - Source: {source}\n"
            f"Title: {title}\n"
            f"Content: {content}\n"
        )

    if not ev_text.strip():
        ev_text = "No evidence articles were retrieved."

    prompt = f"""You are a researcher defending a claim.
Your ONLY job: find SPECIFIC arguments FOR this claim.

CLAIM TO SUPPORT: "{claim}"

EVIDENCE ARTICLES:
{ev_text}

RULES:
1. Read each article's actual content carefully
2. Quote or paraphrase specific facts that support
3. Format: "[Source] states [specific fact] which
    supports the claim because [specific reason]"
4. If an article contradicts - do NOT include it
5. If NO articles support the claim, set
   defense_strength to "none" honestly
6. NEVER write "contains details supporting claim wording"
7. Be specific about WHAT supports and WHY

GOOD example:
"BBC reports Iran and US agreed to conditional 2-week
ceasefire allowing Strait of Hormuz shipping - directly
confirming a ceasefire agreement was made."

Return ONLY this JSON:
{{
  "arguments": [
    "Specific supporting fact from [Source]",
    "Second supporting fact from [Source]"
  ],
  "strongest_point": "Most specific supporting fact",
  "defense_strength": "strong/moderate/weak/none"
}}"""

    raw = call_with_fallback(prompt, GROQ_DEFENDER_MODEL, 600, "Defender")
    result = extract_json(raw)

    if not result or not result.get("arguments"):
        return {
            "arguments": [
                "No specific supporting evidence found in the retrieved articles."
            ],
            "strongest_point": "No support identified",
            "defense_strength": "none",
        }

    return result


def defend(claim, evidence, domain=None):
    return run_defender(claim, evidence or [])
