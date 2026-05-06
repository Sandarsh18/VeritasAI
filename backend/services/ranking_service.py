from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

from credibility import score_source

STOPWORDS = {
    "the",
    "is",
    "are",
    "was",
    "were",
    "a",
    "an",
    "in",
    "of",
    "to",
    "and",
    "or",
    "for",
    "with",
    "on",
    "at",
    "by",
    "from",
    "that",
    "this",
    "it",
    "as",
    "be",
    "been",
    "do",
    "does",
    "did",
    "can",
    "will",
    "would",
    "should",
    "could",
    "not",
    "no",
    "today",
    "latest",
    "news",
}


def extract_keywords(claim: str, keywords: Sequence[str] | None = None, limit: int = 10) -> List[str]:
    terms: List[str] = []
    for token in re.findall(r"[a-z0-9]+", (claim or "").lower()):
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token not in terms:
            terms.append(token)

    for token in keywords or []:
        normalized = re.sub(r"[^a-z0-9]+", "", str(token or "").lower())
        if len(normalized) < 3 or normalized in STOPWORDS:
            continue
        if normalized not in terms:
            terms.append(normalized)

    return terms[: max(1, int(limit))]


def _keyword_score(claim: str, article: Dict, keywords: Sequence[str] | None = None) -> float:
    terms = extract_keywords(claim, keywords)
    if not terms:
        return 0.0

    haystack = " ".join(
        [
            str(article.get("title", "")),
            str(article.get("content", "")),
            str(article.get("full_content", "")),
            str(article.get("source", "")),
        ]
    ).lower()

    matches = sum(1 for term in terms if term in haystack)
    score = matches / max(1, len(terms))

    phrases = [f"{terms[i]} {terms[i + 1]}" for i in range(len(terms) - 1)]
    phrase_hits = sum(1 for phrase in phrases if phrase in haystack)
    if phrase_hits:
        score += min(0.35, phrase_hits * 0.15)

    return max(0.0, min(1.0, round(score, 4)))


def source_credibility(url: str, fallback: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(score_source(url or ""))))
    except Exception:
        return max(0.0, min(1.0, float(fallback)))


def score_article(claim: str, article: Dict, keywords: Sequence[str] | None = None) -> Dict:
    url = str(article.get("url") or article.get("source_url") or article.get("link") or "")
    embedding_score = float(article.get("similarity_score", article.get("embedding_score", 0.0)) or 0.0)
    keyword_score = _keyword_score(claim, article, keywords)
    credibility = float(article.get("credibility_score", source_credibility(url)))

    hybrid_score = (0.7 * embedding_score) + (0.3 * keyword_score)
    final_score = (0.6 * embedding_score) + (0.2 * keyword_score) + (0.2 * credibility)

    scored = dict(article)
    scored["embedding_score"] = round(embedding_score, 4)
    scored["keyword_score"] = round(keyword_score, 4)
    scored["credibility_score"] = round(max(0.0, min(1.0, credibility)), 4)
    scored["hybrid_score"] = round(hybrid_score, 4)
    scored["final_score"] = round(final_score, 4)
    scored["rag_score"] = scored["final_score"]
    return scored


def rank_articles(
    claim: str,
    articles: Sequence[Dict],
    keywords: Sequence[str] | None = None,
    top_k: int = 5,
) -> Tuple[List[Dict], Dict]:
    ranked = [score_article(claim, article, keywords) for article in articles or []]
    ranked.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)

    vector_only = sorted(ranked, key=lambda item: item.get("embedding_score", 0.0), reverse=True)
    comparison = {
        "mode": "hybrid",
        "top_k": max(1, int(top_k)),
        "vector_only_top": [
            {
                "title": item.get("title", "")[:120],
                "source": item.get("source", ""),
                "final_score": round(float(item.get("embedding_score", 0.0)), 4),
            }
            for item in vector_only[: min(3, len(vector_only))]
        ],
        "hybrid_top": [
            {
                "title": item.get("title", "")[:120],
                "source": item.get("source", ""),
                "final_score": round(float(item.get("final_score", 0.0)), 4),
            }
            for item in ranked[: min(3, len(ranked))]
        ],
    }

    return ranked[: max(1, int(top_k))], comparison


def calculate_confidence(
    verdict: str,
    prosecutor_strength: str,
    defender_strength: str,
    supportive_sources: int,
    contradicting_sources: int,
    evidence_rows: Sequence[Dict],
    base_confidence: int | float | None = None,
    disagreement_score: float = 0.0,
) -> int:
    verdict = str(verdict or "UNVERIFIED").upper()
    support = max(0, int(supportive_sources or 0))
    contradict = max(0, int(contradicting_sources or 0))
    total = max(1, support + contradict)

    credibility_values = [float(row.get("credibility_score", 0.5) or 0.5) for row in evidence_rows or []]
    credibility_score = sum(credibility_values) / len(credibility_values) if credibility_values else 0.5

    strength_scale = {"none": 0.0, "weak": 0.28, "moderate": 0.62, "strong": 1.0}
    prosecution = strength_scale.get(str(prosecutor_strength or "none").lower(), 0.0)
    defense = strength_scale.get(str(defender_strength or "none").lower(), 0.0)
    agreement = 1.0 - min(1.0, abs(prosecution - defense))

    consistency = 1.0 - (abs(support - contradict) / total)
    volume = min(1.0, total / 6.0)
    balance = max(0.0, min(1.0, (agreement * 0.35) + (credibility_score * 0.35) + (consistency * 0.2) + (volume * 0.1)))

    if support > 0 and contradict > 0:
        balance *= 0.9
    if verdict == "INSUFFICIENT_DATA" or not evidence_rows:
        balance *= 0.45

    candidate = int(round(balance * 100))
    if base_confidence is not None:
        try:
            candidate = int(round((candidate * 0.45) + (float(base_confidence) * 0.55)))
        except Exception:
            pass

    if disagreement_score:
        candidate = int(round(candidate * (1.0 - min(0.2, max(0.0, disagreement_score) * 0.15))))

    if verdict == "TRUE":
        candidate = max(candidate, 55)
    elif verdict == "FALSE":
        candidate = max(candidate, 55)
    elif verdict == "MISLEADING":
        candidate = max(45, min(candidate, 78))
    elif verdict == "UNVERIFIED":
        candidate = min(candidate, 60)
    elif verdict == "INSUFFICIENT_DATA":
        candidate = min(candidate, 28)

    return max(0, min(100, candidate))


def compare_retrieval_modes(claim: str, articles: Sequence[Dict], keywords: Sequence[str] | None = None) -> Dict:
    ranked, comparison = rank_articles(claim, articles, keywords, top_k=min(5, len(list(articles or [])) or 1))
    vector_top = comparison.get("vector_only_top", [])
    hybrid_top = comparison.get("hybrid_top", [])
    if vector_top and hybrid_top:
        top_delta = round(float(hybrid_top[0].get("final_score", 0.0)) - float(vector_top[0].get("final_score", 0.0)), 4)
    else:
        top_delta = 0.0

    comparison.update(
        {
            "top_score_delta": top_delta,
            "hybrid_result_count": len(ranked),
        }
    )
    return comparison
