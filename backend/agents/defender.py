from llm_client import call_ollama, extract_json


def run_defender(claim: str, evidence: list) -> dict:
    ev_text = ""
    for i, article in enumerate(evidence[:4], 1):
        title = article.get("title", "")
        source = article.get("source", "Unknown")
        content = article.get("content", "")[:300]
        ev_text += (
            f"\n--- Article {i} ---\n"
            f"Title: {title}\n"
            f"Source: {source}\n"
            f"Content: {content}\n"
        )

    if not ev_text:
        ev_text = "No evidence articles available."

    prompt = f"""You are a researcher defending a claim.
Your job: find specific arguments FOR this claim
using the actual content of the articles provided.

CLAIM: \"{claim}\"

EVIDENCE ARTICLES:
{ev_text}

INSTRUCTIONS:
1. Read each article's actual content carefully
2. Find what SPECIFICALLY in the article supports
   or is consistent with the claim
3. Quote or paraphrase the actual fact from the article
4. Format: "[Source Name] states that [specific fact
   from article] which supports the claim because [reason]"
5. If an article CONTRADICTS the claim, say defense
   strength is weak - do NOT fabricate support
6. Never say "contains details that support the core
   claim wording" - be specific about what those details are

BAD example:
"BBC contains details that support the core claim wording."

GOOD example:
"BBC reports that Iran and the US agreed to a
conditional two-week ceasefire allowing shipping
through Strait of Hormuz - directly confirming
a ceasefire agreement exists."

Return ONLY valid JSON:
{{
  "arguments": [
    "Argument 1 with specific fact from [Source Name]",
    "Argument 2 with specific fact from [Source Name]"
  ],
  "strongest_point": "Most specific supporting fact with source",
  "defense_strength": "strong/moderate/weak/none"
}}"""

    raw = call_ollama(prompt, 0, 500, 768, "Defender")
    result = extract_json(raw)

    if not result or not result.get("arguments"):
        return {
            "arguments": ["No specific supporting evidence found"],
            "strongest_point": "No support identified",
            "defense_strength": "none",
        }

    return result


def defend(claim, evidence, domain):
    # Compatibility wrapper for existing orchestrator imports.
    return run_defender(claim, evidence or [])
