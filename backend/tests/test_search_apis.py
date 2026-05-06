import os

import requests
from dotenv import load_dotenv


load_dotenv()


def _require_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    assert value, f"{name} is missing"
    return value


def test_serpapi_returns_results():
    key = _require_key("SERPAPI_KEY")
    response = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google",
            "q": "why is the sky blue fact check",
            "api_key": key,
            "num": 3,
            "hl": "en",
        },
        timeout=20,
    )

    if response.status_code >= 400:
        print(response.text)
    assert response.status_code < 400

    payload = response.json()
    results = payload.get("organic_results") or payload.get("news_results") or []
    print(f"SerpAPI status={response.status_code} results={len(results)}")
    assert len(results) > 0
    assert any(item.get("link") for item in results)


def test_newsapi_returns_articles():
    key = _require_key("NEWSAPI_KEY")
    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": "why is the sky blue",
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 3,
            "apiKey": key,
        },
        timeout=20,
    )

    if response.status_code >= 400:
        print(response.text)
    assert response.status_code < 400

    payload = response.json()
    if payload.get("status") != "ok":
        print(payload)
    assert payload.get("status") == "ok"

    articles = payload.get("articles") or []
    print(f"NewsAPI status={response.status_code} articles={len(articles)}")
    assert len(articles) > 0
    assert any(item.get("url") for item in articles)

