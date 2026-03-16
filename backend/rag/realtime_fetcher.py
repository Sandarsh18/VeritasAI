import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import feedparser
import requests

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_BASE_URL = os.getenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2/everything")
CACHE_HOURS = int(os.getenv("CACHE_DURATION_HOURS", 6))
BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_FILE = BASE_DIR / "data" / "realtime_cache.json"

SOURCE_CREDIBILITY = {
    "reuters.com": {"score": 0.97, "logo": "🔵", "type": "Wire Agency", "name": "Reuters", "country": "International"},
    "apnews.com": {"score": 0.97, "logo": "🔵", "type": "Wire Agency", "name": "AP News", "country": "International"},
    "bbc.com": {"score": 0.95, "logo": "🔴", "type": "Public Broadcaster", "name": "BBC News", "country": "International"},
    "bbc.co.uk": {"score": 0.95, "logo": "🔴", "type": "Public Broadcaster", "name": "BBC News", "country": "International"},
    "theguardian.com": {"score": 0.92, "logo": "🔵", "type": "Newspaper", "name": "The Guardian", "country": "International"},
    "nytimes.com": {"score": 0.91, "logo": "⚫", "type": "Newspaper", "name": "The New York Times", "country": "International"},
    "washingtonpost.com": {"score": 0.90, "logo": "⚫", "type": "Newspaper", "name": "The Washington Post", "country": "International"},
    "who.int": {"score": 0.99, "logo": "🟢", "type": "Health Authority", "name": "World Health Organization", "country": "International"},
    "cdc.gov": {"score": 0.99, "logo": "🟢", "type": "Health Authority", "name": "CDC", "country": "International"},
    "nature.com": {"score": 0.98, "logo": "🟣", "type": "Scientific Journal", "name": "Nature", "country": "International"},
    "science.org": {"score": 0.98, "logo": "🟣", "type": "Scientific Journal", "name": "Science", "country": "International"},
    "factcheck.org": {"score": 0.96, "logo": "✅", "type": "Fact Checker", "name": "FactCheck.org", "country": "International"},
    "snopes.com": {"score": 0.94, "logo": "✅", "type": "Fact Checker", "name": "Snopes", "country": "International"},
    "politifact.com": {"score": 0.93, "logo": "✅", "type": "Fact Checker", "name": "PolitiFact", "country": "International"},
    "thehindu.com": {"score": 0.93, "logo": "🟠", "type": "Newspaper", "name": "The Hindu", "country": "India"},
    "hindustantimes.com": {"score": 0.88, "logo": "🟠", "type": "Newspaper", "name": "Hindustan Times", "country": "India"},
    "ndtv.com": {"score": 0.87, "logo": "🟠", "type": "News Channel", "name": "NDTV", "country": "India"},
    "timesofindia.com": {"score": 0.86, "logo": "🟠", "type": "Newspaper", "name": "Times of India", "country": "India"},
    "indianexpress.com": {"score": 0.90, "logo": "🟠", "type": "Newspaper", "name": "Indian Express", "country": "India"},
    "deccanherald.com": {"score": 0.87, "logo": "🟠", "type": "Newspaper", "name": "Deccan Herald", "country": "India"},
    "theprint.in": {"score": 0.85, "logo": "🟠", "type": "Digital News", "name": "The Print", "country": "India"},
    "scroll.in": {"score": 0.84, "logo": "🟠", "type": "Digital News", "name": "Scroll.in", "country": "India"},
    "wire.in": {"score": 0.83, "logo": "🟠", "type": "Digital News", "name": "The Wire", "country": "India"},
    "boomlive.in": {"score": 0.95, "logo": "✅", "type": "Fact Checker", "name": "BOOM Live", "country": "India"},
    "altnews.in": {"score": 0.95, "logo": "✅", "type": "Fact Checker", "name": "Alt News", "country": "India"},
    "factly.in": {"score": 0.94, "logo": "✅", "type": "Fact Checker", "name": "Factly", "country": "India"},
    "vishvasnews.com": {"score": 0.90, "logo": "✅", "type": "Fact Checker", "name": "Vishvas News", "country": "India"},
}

RSS_FEEDS = {
    "Reuters World": "https://feeds.reuters.com/reuters/worldNews",
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "Times of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "The Hindu": "https://www.thehindu.com/news/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/feed/",
    "Hindustan Times": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
}

STOP_WORDS = {
    "is", "are", "was", "were", "the", "a", "an", "in", "of", "to", "and", "or", "that", "this",
    "it", "for", "on", "with", "at", "by", "from", "will", "would", "could", "should", "may", "might",
    "can", "than", "then", "be", "been", "have", "has", "had", "do", "does", "did", "not", "no",
    "yes", "i", "my", "your", "he", "she", "they", "we", "started", "year", "time", "current",
    "claim", "says", "about", "into", "after", "before", "over", "under", "news",
}


def get_source_credibility(url: str) -> Dict:
    if not url:
        return {"score": 0.50, "logo": "⚪", "type": "Unknown", "name": "Unknown", "country": "Unknown"}
    lowered = url.lower()
    for domain, info in SOURCE_CREDIBILITY.items():
        if domain in lowered:
            return info
    return {"score": 0.55, "logo": "⚪", "type": "Unknown Source", "name": "Unknown Source", "country": "Unknown"}


def extract_relevance_terms(text: str) -> dict:
    words = [word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in STOP_WORDS]
    unique_words = sorted(set(words))

    phrases = set()
    for size in (3, 2):
        for index in range(len(words) - size + 1):
            phrase_words = words[index:index + size]
            if len(set(phrase_words)) == size:
                phrases.add(" ".join(phrase_words))

    return {"words": unique_words, "phrases": sorted(phrases)}


def is_relevant(claim: str, article: dict, threshold: float = 0.15) -> bool:
    terms = extract_relevance_terms(claim)
    claim_words = terms["words"]
    claim_phrases = terms["phrases"]

    if not claim_words:
        return True

    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    keywords = " ".join(article.get("keywords", []) or []).lower()
    combined = f"{title} {content} {keywords}"

    word_matches = sum(1 for word in claim_words if word in combined)
    phrase_matches = sum(1 for phrase in claim_phrases if phrase in combined)

    if claim_phrases and phrase_matches == 0 and word_matches < min(2, len(claim_words)):
        return False

    overlap = (word_matches + (2 * phrase_matches)) / max(len(claim_words) + (2 * len(claim_phrases)), 1)
    return overlap >= threshold


def get_sources_registry() -> List[Dict]:
    return [
        {
            "domain": domain,
            "name": info.get("name", domain),
            "score": info.get("score", 0.55),
            "type": info.get("type", "Unknown Source"),
            "logo": info.get("logo", "⚪"),
            "country": info.get("country", "Unknown"),
        }
        for domain, info in SOURCE_CREDIBILITY.items()
    ]


def load_cache() -> Dict:
    try:
        if CACHE_FILE.exists():
            with CACHE_FILE.open("r", encoding="utf-8") as file:
                return json.load(file)
    except Exception:
        pass
    return {}


def save_cache(cache: Dict) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w", encoding="utf-8") as file:
            json.dump(cache, file, indent=2)
    except Exception as exc:
        print(f"Cache save error: {exc}")


def is_cache_valid(cache_entry: Dict) -> bool:
    if not cache_entry.get("cached_at"):
        return False
    cached_time = datetime.fromisoformat(cache_entry["cached_at"])
    return datetime.now() - cached_time < timedelta(hours=CACHE_HOURS)


def fetch_newsapi(query: str, max_results: int = 10) -> List[Dict]:
    if not NEWSAPI_KEY:
        print("NewsAPI key not configured")
        return []

    try:
        params = {
            "q": query,
            "apiKey": NEWSAPI_KEY,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": max_results,
            "from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        }

        response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=10)
        if response.status_code != 200:
            print(f"NewsAPI error: {response.status_code}")
            return []

        data = response.json()
        articles = []

        for item in data.get("articles", []):
            if item.get("title") == "[Removed]":
                continue

            source_url = item.get("url", "")
            source_name = item.get("source", {}).get("name", "Unknown")
            author = item.get("author", "")
            published_at = item.get("publishedAt", "")
            cred_info = get_source_credibility(source_url)

            pub_date = "Unknown date"
            if published_at:
                try:
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    pub_date = dt.strftime("%d %B %Y")
                except Exception:
                    pub_date = published_at[:10]

            if author:
                author = author.split(",")[0].strip()
                if len(author) > 50:
                    author = ""

            articles.append(
                {
                    "id": hashlib.md5(source_url.encode()).hexdigest()[:8],
                    "title": item.get("title", ""),
                    "content": f"{item.get('description', '')} {(item.get('content', '') or '')[:500]}".strip(),
                    "source": source_name,
                    "source_url": source_url,
                    "author": author or "Staff Reporter",
                    "published_date": pub_date,
                    "published_raw": published_at,
                    "credibility_score": cred_info["score"],
                    "source_logo": cred_info["logo"],
                    "source_type": cred_info["type"],
                    "category": "realtime",
                    "is_realtime": True,
                    "image_url": item.get("urlToImage", ""),
                    "keywords": [word for word in re.findall(r"[a-z0-9]+", f"{item.get('title', '')} {item.get('description', '')}".lower()) if len(word) > 3],
                }
            )

        print(f"NewsAPI: fetched {len(articles)} articles")
        return articles
    except Exception as exc:
        print(f"NewsAPI fetch error: {exc}")
        return []


def fetch_gdelt_free(query: str, max_results: int = 5) -> List[Dict]:
    try:
        import urllib.parse

        encoded = urllib.parse.quote(query)
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={encoded}&mode=artlist&maxrecords={max_results}&format=json&timespan=2weeks"
        )

        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []

        data = response.json()
        articles = []

        for item in data.get("articles", []):
            source_url = item.get("url", "")
            source_name = item.get("domain", "Unknown")
            pub_date = item.get("seendate", "")[:8]
            cred_info = get_source_credibility(source_url)

            formatted_date = "Recent"
            if len(pub_date) == 8:
                try:
                    dt = datetime.strptime(pub_date, "%Y%m%d")
                    formatted_date = dt.strftime("%d %B %Y")
                except Exception:
                    pass

            articles.append(
                {
                    "id": hashlib.md5(source_url.encode()).hexdigest()[:8],
                    "title": item.get("title", ""),
                    "content": item.get("title", ""),
                    "source": source_name,
                    "source_url": source_url,
                    "author": "Staff Reporter",
                    "published_date": formatted_date,
                    "credibility_score": cred_info["score"],
                    "source_logo": cred_info["logo"],
                    "source_type": cred_info["type"],
                    "category": "realtime",
                    "is_realtime": True,
                    "image_url": "",
                    "keywords": [word for word in re.findall(r"[a-z0-9]+", item.get("title", "").lower()) if len(word) > 3],
                }
            )

        print(f"GDELT: fetched {len(articles)} articles")
        return articles
    except Exception as exc:
        print(f"GDELT error: {exc}")
        return []


def fetch_rss_feeds(query: str) -> List[Dict]:
    terms = extract_relevance_terms(query)
    articles = []

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                combined = f"{title} {summary}"
                phrase_match = any(phrase in combined for phrase in terms["phrases"])
                word_hits = sum(1 for word in terms["words"] if word in combined)

                if not phrase_match and word_hits == 0:
                    continue

                pub_date = "Recent"
                if hasattr(entry, "published"):
                    try:
                        from email.utils import parsedate_to_datetime

                        dt = parsedate_to_datetime(entry.published)
                        pub_date = dt.strftime("%d %B %Y")
                    except Exception:
                        pub_date = str(entry.published)[:10]

                source_url = entry.get("link", "")
                cred_info = get_source_credibility(source_url)

                articles.append(
                    {
                        "id": hashlib.md5(source_url.encode()).hexdigest()[:8],
                        "title": entry.get("title", ""),
                        "content": entry.get("summary", "")[:400],
                        "source": source_name,
                        "source_url": source_url,
                        "author": entry.get("author", "Staff Reporter"),
                        "published_date": pub_date,
                        "credibility_score": cred_info["score"],
                        "source_logo": cred_info["logo"],
                        "source_type": cred_info["type"],
                        "category": "realtime",
                        "is_realtime": True,
                        "image_url": "",
                        "keywords": [word for word in re.findall(r"[a-z0-9]+", combined) if len(word) > 3],
                    }
                )
        except Exception as exc:
            print(f"RSS {source_name} error: {exc}")
            continue

    print(f"RSS: fetched {len(articles)} relevant articles")
    return articles


def fetch_realtime_evidence(claim: str, max_results: int = 10) -> List[Dict]:
    cache = load_cache()
    cache_key = hashlib.md5(claim.lower().encode()).hexdigest()

    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print(f"Cache hit for: {claim[:50]}")
        return cache[cache_key].get("articles", [])

    print(f"Fetching real-time news for: {claim[:50]}")

    all_articles = []
    if NEWSAPI_KEY:
        all_articles.extend(fetch_newsapi(claim, 8))
    all_articles.extend(fetch_gdelt_free(claim, 5))
    all_articles.extend(fetch_rss_feeds(claim)[:5])

    seen_urls = set()
    unique = []
    for article in all_articles:
        url = article.get("source_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    relevant = [article for article in unique if is_relevant(claim, article, threshold=0.10)]
    print(f"[NewsAPI] {len(unique)} fetched, {len(relevant)} relevant after filter")

    if len(relevant) < 2:
        relevant = [article for article in unique if is_relevant(claim, article, threshold=0.05)]

    relevant.sort(key=lambda item: item.get("credibility_score", 0), reverse=True)
    final = relevant[:max_results]

    cache[cache_key] = {
        "articles": final,
        "cached_at": datetime.now().isoformat(),
        "claim": claim,
    }
    save_cache(cache)

    print(f"Real-time: {len(final)} relevant articles found")
    return final
