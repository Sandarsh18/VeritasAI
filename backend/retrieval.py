import os
import re
from typing import Dict, List
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


STOP_WORDS = {
    "is", "are", "was", "were", "the", "a", "an",
    "in", "of", "to", "and", "or", "that", "this",
    "it", "for", "on", "with", "at", "by", "from",
    "will", "would", "could", "should", "be", "been",
    "have", "has", "do", "does", "did", "not", "no",
    "as", "but", "if", "year", "2026", "2025", "2024",
    "india", "latest", "news", "today", "new"
}


def build_search_query(claim: str, keywords: List[str] | None = None) -> str:
    """Build a claim-focused search query from meaningful terms."""
    stop = {
        "is", "are", "was", "the", "a", "an", "in", "of",
        "to", "and", "or", "will", "can", "does", "do"
    }
    important = [
        token.strip(".,!?\"'").lower()
        for token in (claim or "").split()
        if token and len(token.strip(".,!?\"'")) > 2 and token.lower() not in stop
    ]
    if important:
        return " ".join(important[:5])
    return " ".join((keywords or [])[:5]).strip() or (claim or "").strip()


def _claim_words(claim: str) -> list[str]:
    words = []
    for token in re.findall(r"[a-z0-9]+", (claim or "").lower()):
        if len(token) > 2 and token not in STOP_WORDS:
            words.append(token)
    seen = set()
    ordered = []
    for token in words:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def calculate_relevance(claim: str, article: Dict) -> float:
    """Compute relevance score in range [0.0, 1.0] from claim-term overlap."""
    claim_terms = _claim_words(claim)
    if not claim_terms:
        return 0.5

    title = (article.get("title", "") or "").lower()
    content = (
        article.get("snippet")
        or article.get("description")
        or article.get("content")
        or ""
    ).lower()
    full = f"{title} {title} {content}"

    matched_terms = [term for term in claim_terms if term in full]
    matches = len(matched_terms)
    score = matches / max(len(claim_terms), 1)

    phrases = [f"{claim_terms[i]} {claim_terms[i + 1]}" for i in range(len(claim_terms) - 1)]
    phrase_hits = sum(1 for phrase in phrases if phrase in full)
    if phrase_hits:
        score += min(0.4, phrase_hits * 0.2)

    if len(claim_terms) >= 3 and matches == 1:
        score *= 0.4

    return round(max(0.0, min(1.0, score)), 3)


def filter_relevant_results(claim: str, results: List[Dict], min_relevance: float = 0.15) -> List[Dict]:
    """Keep only claim-relevant results, preserving relevance score for ranking."""
    relevant: List[Dict] = []
    for row in results or []:
        score = calculate_relevance(claim, row)
        row["relevance_score"] = score
        if score >= min_relevance:
            relevant.append(row)
    return relevant


def search_serpapi(query: str) -> List[Dict]:
    if not query or not SERPAPI_KEY:
        return []

    focused_query = build_search_query(query)

    try:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google",
                "q": focused_query,
                "api_key": SERPAPI_KEY,
                "num": 12,
                "hl": "en",
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        organic = data.get("organic_results", [])[:12]
        return [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in organic
            if item.get("link")
        ]
    except Exception:
        return []


def search_newsapi(query: str, published_after_days: int = 90) -> List[Dict]:
    if not query or not NEWSAPI_KEY:
        return []

    focused_query = build_search_query(query)

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": focused_query,
                "pageSize": 12,
                "language": "en",
                "sortBy": "relevancy",
            },
            headers={"X-Api-Key": NEWSAPI_KEY},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])[:12]

        threshold_date = datetime.now(timezone.utc) - timedelta(days=published_after_days)

        filtered_articles = []
        for item in articles:
            if not item.get("url"):
                continue

            published_at_str = item.get("publishedAt")
            if published_at_str:
                try:
                    # Attempt to parse with 'Z' for UTC
                    published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    if published_at < threshold_date:
                        continue  # Skip old articles
                except ValueError:
                    # Handle cases where timezone info might be missing or in a different format
                    try:
                        published_at = datetime.fromisoformat(published_at_str)
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                        if published_at < threshold_date:
                            continue
                    except ValueError:
                        pass  # Keep article if date is unparsable

            filtered_articles.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "source": (item.get("source") or {}).get("name", "Unknown"),
                    "publishedAt": published_at_str,
                }
            )

        return filtered_articles
    except Exception:
        return []


def merge_results(serp: List[Dict], news: List[Dict]) -> List[Dict]:
    normalized: List[Dict] = []

    for item in serp or []:
        normalized.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serpapi",
                "date": "",
            }
        )

    for item in news or []:
        normalized.append(
            {
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": item.get("description", ""),
                "source": item.get("source", "newsapi"),
                "date": item.get("publishedAt", ""),
            }
        )

    seen = set()
    deduped: List[Dict] = []
    for row in normalized:
        key = (row.get("link") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return deduped
