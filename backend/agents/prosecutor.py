from llm_client import OLLAMA_FALLBACK, call_deepseek, call_ollama, extract_json


def run_prosecutor(claim: str, evidence: list) -> dict:
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

    prompt = f"""You are a strict fact-checking prosecutor.
Your ONLY job: find SPECIFIC arguments AGAINST this claim.

CLAIM TO CHALLENGE: "{claim}"

EVIDENCE ARTICLES:
{ev_text}

RULES:
1. Read each article's actual content carefully
2. Quote or paraphrase specific facts from articles
3. Format each argument as:
   "[Source Name] reports [specific fact] which
    contradicts the claim because [specific reason]"
4. If an article supports the claim - do NOT
   include it. Only use articles that contradict.
5. If NO articles contradict the claim, set
   prosecution_strength to "none" honestly
6. NEVER write "does not conclusively establish"
7. NEVER write "core claim wording"
8. Be specific about WHAT contradicts and WHY

GOOD example:
"Al Jazeera reports that the ceasefire was temporary
and halted after 40 days of US-Israeli attacks,
contradicting any claim of a permanent ceasefire."

BAD example:
"This article does not conclusively establish the claim."

Return ONLY this JSON:
{{
  "arguments": [
    "Specific argument from [Source] citing [fact]",
    "Second specific argument from [Source]"
  ],
  "strongest_point": "Most powerful specific contradiction",
  "prosecution_strength": "strong/moderate/weak/none"
}}"""

    raw = call_deepseek(prompt, 800, "Prosecutor")

    if not raw:
        print("[Prosecutor] DeepSeek failed -> Ollama fallback")
        raw = call_ollama(prompt, 0.1, 500, 1024, OLLAMA_FALLBACK, "Prosecutor")

    result = extract_json(raw)

    if not result or not result.get("arguments"):
        return {
            "arguments": [
                "No specific contradicting evidence found in the retrieved articles."
            ],
            "strongest_point": "No contradictions identified",
            "prosecution_strength": "none",
        }

    return result


def prosecute(claim, evidence, domain=None):
    return run_prosecutor(claim, evidence or [])
