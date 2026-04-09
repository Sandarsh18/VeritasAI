from llm_client import call_ollama, extract_json


def run_prosecutor(claim: str, evidence: list) -> dict:
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

    prompt = f"""You are a strict fact-checking prosecutor.
Your job: find specific arguments AGAINST this claim
using the actual content of the articles provided.

CLAIM: \"{claim}\"

EVIDENCE ARTICLES:
{ev_text}

INSTRUCTIONS:
1. Read each article's actual content carefully
2. Find what SPECIFICALLY in the article contradicts
   or raises doubt about the claim
3. Quote or paraphrase the actual fact from the article
4. Format: "[Source Name] reports that [specific fact
   from article] which contradicts the claim because
   [reason]"
5. If an article SUPPORTS the claim, say prosecution
   strength is weak or none - do NOT fabricate arguments
6. Never say "does not conclusively establish" - be specific

BAD example (do not do this):
"Article does not conclusively establish the claim."

GOOD example (do this):
"Al Jazeera reports that a two-week ceasefire was halted
40 days into US-Israeli attacks, meaning the ceasefire
existed but was temporary - contradicting a permanent
ceasefire claim."

Return ONLY valid JSON:
{{
  "arguments": [
    "Argument 1 with specific fact from [Source Name]",
    "Argument 2 with specific fact from [Source Name]"
  ],
  "strongest_point": "Most specific contradiction with source",
  "prosecution_strength": "strong/moderate/weak/none"
}}"""

    raw = call_ollama(prompt, 0, 500, 768, "Prosecutor")
    result = extract_json(raw)

    if not result or not result.get("arguments"):
        return {
            "arguments": ["No specific contradicting evidence found"],
            "strongest_point": "No contradictions identified",
            "prosecution_strength": "none",
        }

    return result


def prosecute(claim, evidence, domain):
    # Compatibility wrapper for existing orchestrator imports.
    return run_prosecutor(claim, evidence or [])
