import re

from .vector_store import search


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "best",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "true",
}


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\-]*", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def retrieve_evidence(claim: str, top_k: int = 5, min_score: float = 0.25) -> dict:
    claim_tokens = _tokenize(claim)
    results = search(claim, top_k=top_k * 2)
    articles = []

    for article in results:
        distance = float(article.get("distance_score", 999.0))
        similarity = 1 / (1 + distance)
        article_tokens = _tokenize(
            " ".join(
                [
                    article.get("title", ""),
                    article.get("content", "")[:400],
                    " ".join(article.get("keywords", [])),
                    article.get("category", ""),
                ]
            )
        )
        overlap = len(claim_tokens & article_tokens) / max(1, len(claim_tokens))
        combined_score = round((similarity * 0.8) + (overlap * 0.2), 3)

        if combined_score < min_score:
            continue
        if overlap == 0 and combined_score < 0.35:
            continue

        filtered = article.copy()
        filtered["relevance_score"] = combined_score
        filtered["semantic_score"] = round(similarity, 3)
        filtered["keyword_overlap"] = round(overlap, 3)
        filtered["content"] = article.get("content", "")[:500]
        articles.append(filtered)

    articles.sort(key=lambda item: item["relevance_score"], reverse=True)
    articles = articles[:top_k]

    if len(articles) < 2:
        return {
            "articles": [],
            "insufficient_evidence": True,
            "message": "No relevant fact-checked articles found for this specific claim.",
        }

    return {
        "articles": articles,
        "insufficient_evidence": False,
    }
