PROMPT_TEMPLATE = """You are a researcher finding support for a SPECIFIC claim.

CLAIM TO ANALYZE: '{claim}'

AVAILABLE EVIDENCE:
{evidence_text}

YOUR TASK:
Find arguments that SUPPORT or partially support the claim.

CRITICAL RULES:
1. ONLY use information directly related to: '{claim}'
2. Do NOT use unrelated articles
3. If no relevant supporting evidence exists, say so clearly
"""

FALLBACK = {
    "arguments": [],
    "strongest_point": "No supporting evidence found",
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
    for separator in (". ", "! ", "? "):
        if separator in text:
            return text.split(separator, 1)[0].strip() + separator.strip()
    return text.strip()


def defend(claim: str, evidence_summary: str) -> dict:
    articles = _parse_articles(evidence_summary)
    arguments = []

    for article in articles:
        verdict_label = article.get("verdict label", "").lower()
        if verdict_label != "true":
            continue
        source = article.get("source", "Unknown source")
        title = article.get("title", "Untitled article")
        content = _first_sentence(article.get("content", ""))
        arguments.append(f"[{source}] {title} supports '{claim}': {content}"[:260])

    if not arguments:
        return FALLBACK.copy()

    return {
        "arguments": arguments[:4],
        "strongest_point": arguments[0][:260],
    }


run_defender = defend
