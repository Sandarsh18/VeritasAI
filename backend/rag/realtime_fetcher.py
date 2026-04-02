import hashlib
from datetime import datetime, timedelta
from typing import Dict, List
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


BLOCKED_DOMAINS = {
    "brainly.in",
    "zhihu.com",
    "answers.com",
    "quora.com",
    "reddit.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "baidu.com",
}


def _domain_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def _credibility_from_domain(domain: str) -> float:
    if any(x in domain for x in ["reuters.com", "bbc.", "apnews.com", "afp.com"]):
        return 0.95
    if any(x in domain for x in ["gov", "eci.gov.in", "pib.gov.in", "who.int", "un.org", "nasa.gov"]):
        return 0.98
    if any(x in domain for x in ["wikipedia.org"]):
        return 0.84
    if any(x in domain for x in ["thehindu.com", "indianexpress.com", "ndtv.com", "economictimes.", "livemint.com"]):
        return 0.90
    if "news" in domain:
        return 0.78
    return 0.64


def _clean_text(text: str, limit: int = 320) -> str:
    plain = BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
    plain = " ".join(plain.split())
    if len(plain) > limit:
        return plain[: limit - 1].rstrip() + "…"
    return plain


def _source_from_title_or_domain(title: str, domain: str) -> str:
    if " - " in title:
        tail = title.rsplit(" - ", 1)[-1].strip()
        if tail and len(tail) <= 50:
            return tail
    return domain


def filter_old_articles(articles: list, max_age_days: int = 90) -> list:
    """Remove articles older than max_age_days. Keep articles with no date."""
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    filtered = []
    for article in articles:
        pub_date = article.get("publishedAt") or article.get("published_date")
        if not pub_date:
            article["published_date"] = None
            filtered.append(article)
            continue
        try:
            parsed = datetime.fromisoformat(pub_date.replace("Z", "+00:00").replace("+00:00", ""))
            if parsed >= cutoff:
                article["published_date"] = parsed.strftime("%Y-%m-%d")
                filtered.append(article)
        except Exception:
            article["published_date"] = None
            filtered.append(article)
    return filtered

def fetch_rss_articles(keywords: List[str]) -> List[Dict]:
    """
    Overriding to use duckduckgo search instead of RSS feeds, so we can get REAL results
    for ANY claim.
    """
    if not keywords:
        return []

    query = keywords[0]
    keyword_tokens = {k.lower() for k in keywords[1:] if k}

    matches = []

    try:
        results = list(DDGS().text(query, region="in-en", safesearch="off", max_results=12))
    except Exception as e:
        print(f"DDGS error: {e}")
        results = []

    for res in results:
        title = _clean_text((res.get("title") or "").strip(), limit=180)
        summary = _clean_text((res.get("body") or "").strip(), limit=300)
        link = (res.get("href") or "").strip()
        if not title or not link:
            continue

        domain = _domain_of(link)
        if not domain or any(blocked in domain for blocked in BLOCKED_DOMAINS):
            continue

        content_blob = f"{title} {summary}".lower()
        if keyword_tokens:
            overlap = sum(1 for token in keyword_tokens if token in content_blob)
            if overlap == 0:
                continue

        source_name = _source_from_title_or_domain(title, domain)
        cred_score = _credibility_from_domain(domain)

        article_id = "ddg_" + hashlib.md5((link + title).encode("utf-8")).hexdigest()[:12]

        matches.append({
            "id": article_id,
            "title": title,
            "content": summary,
            "source": source_name,
            "source_url": link,
            "author": "Web Source",
            "published_date": datetime.utcnow().strftime("%d %B %Y"),
            "credibility_score": cred_score,
            "source_logo": "🌐", 
            "source_type": "Web Article",
            "keywords": keywords[1:],
            "is_realtime": True,
        })

    if not matches:
        fallback_query = " ".join(keywords[:8]) + " fact check official"
        try:
            fallback_results = list(
                DDGS().text(fallback_query, region="in-en", safesearch="off", max_results=10)
            )
        except Exception:
            fallback_results = []

        for res in fallback_results:
            title = _clean_text((res.get("title") or "").strip(), limit=180)
            summary = _clean_text((res.get("body") or "").strip(), limit=300)
            link = (res.get("href") or "").strip()
            if not title or not link:
                continue

            domain = _domain_of(link)
            if not domain or any(blocked in domain for blocked in BLOCKED_DOMAINS):
                continue

            source_name = _source_from_title_or_domain(title, domain)
            cred_score = _credibility_from_domain(domain)
            article_id = "ddg_" + hashlib.md5((link + title).encode("utf-8")).hexdigest()[:12]
            matches.append(
                {
                    "id": article_id,
                    "title": title,
                    "content": summary,
                    "source": source_name,
                    "source_url": link,
                    "author": "Web Source",
                    "published_date": datetime.utcnow().strftime("%d %B %Y"),
                    "credibility_score": cred_score,
                    "source_logo": "🌐",
                    "source_type": "Web Article",
                    "keywords": keywords[1:],
                    "is_realtime": True,
                }
            )

    if not matches:
        try:
            rss_query = "+".join((" ".join(keywords[:8])).split())
            rss_url = f"https://news.google.com/rss/search?q={rss_query}&hl=en-IN&gl=IN&ceid=IN:en"
            parsed = feedparser.parse(rss_url)
            for entry in parsed.entries[:12]:
                title = _clean_text((entry.get("title") or "").strip(), limit=180)
                link = (entry.get("link") or "").strip()
                summary = _clean_text((entry.get("summary") or "").strip(), limit=300)
                if not title or not link:
                    continue

                domain = _domain_of(link)
                if not domain or any(blocked in domain for blocked in BLOCKED_DOMAINS):
                    continue

                article_id = "rss_" + hashlib.md5((link + title).encode("utf-8")).hexdigest()[:12]
                matches.append(
                    {
                        "id": article_id,
                        "title": title,
                        "content": summary,
                        "source": _source_from_title_or_domain(title, domain),
                        "source_url": link,
                        "author": entry.get("author", "Web Source"),
                        "published_date": entry.get("published", datetime.utcnow().strftime("%d %B %Y")),
                        "credibility_score": _credibility_from_domain(domain),
                        "source_logo": "🌐",
                        "source_type": "Web Article",
                        "keywords": keywords[1:],
                        "is_realtime": True,
                    }
                )
        except Exception:
            pass

    return filter_old_articles(matches)
