import re


PROMPT_TEMPLATE = """You are a fact-checking prosecutor analyzing a SPECIFIC claim.

CLAIM TO ANALYZE: '{claim}'

RELEVANT EVIDENCE ARTICLES:
{evidence_text}

YOUR TASK:
Find arguments that CONTRADICT or DISPROVE the claim above.

CRITICAL RULES:
1. ONLY use information from the provided articles
2. ONLY include arguments directly related to: '{claim}'
3. If the articles are NOT relevant to the claim, say so
4. Do NOT mix information from different unrelated topics
5. Each argument must mention the source article

If no relevant contradicting evidence exists in articles:
Return: {"arguments": [], "strongest_point": "No contradicting evidence found in available articles for this specific claim"}
"""

FALLBACK = {
    "arguments": [],
    "strongest_point": "No contradicting evidence found in available articles for this specific claim",
}


def _parse_articles(evidence_summary: str) -> list[dict]:
    articles = []
    for block in evidence_summary.split("ARTICLE "):
        block = block.strip()
        if not block:
            continue
        fields = {}
        for line in block.splitlines()[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
        articles.append(fields)
    return articles


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0].strip() if parts and parts[0].strip() else text.strip()


def prosecute(claim: str, evidence_summary: str) -> dict:
    articles = _parse_articles(evidence_summary)
    arguments = []

    for article in articles:
        verdict_label = article.get("verdict label", "").lower()
        if verdict_label not in {"false", "misleading"}:
            continue
        source = article.get("source", "Unknown source")
        title = article.get("title", "Untitled article")
        content = _first_sentence(article.get("content", ""))
        qualifier = "partially contradicts" if verdict_label == "misleading" else "contradicts"
        arguments.append(f"[{source}] {title} {qualifier} '{claim}': {content}"[:260])

    if not arguments:
        return FALLBACK.copy()

    return {
        "arguments": arguments[:4],
        "strongest_point": arguments[0][:260],
    }


run_prosecutor = prosecute
