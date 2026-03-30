import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


def search_serpapi(query: str) -> List[Dict]:
    if not query or not SERPAPI_KEY:
        return []

    try:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google",
                "q": query,
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


def search_newsapi(query: str) -> List[Dict]:
    if not query or not NEWSAPI_KEY:
        return []

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
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
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "source": (item.get("source") or {}).get("name", "Unknown"),
                "publishedAt": item.get("publishedAt", ""),
            }
            for item in articles
            if item.get("url")
        ]
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
