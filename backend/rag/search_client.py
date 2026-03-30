"""
backend/rag/search_client.py
Dual search: SerpAPI + NewsAPI
Both return standardised article dicts.
Trusted-domain filtering on all results.
"""

import os, requests, re
from datetime import datetime
from newsapi import NewsApiClient
from serpapi import GoogleSearch
from dotenv import load_dotenv
load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

TRUSTED_SOURCES = {
    "reuters.com": 0.97,
    "apnews.com": 0.97,
    "afp.com": 0.95,

    "thehindu.com": 0.93,
    "thehindubusinessline.com": 0.91,
    "indianexpress.com": 0.91,
    "ndtv.com": 0.89,
    "theprint.in": 0.88,
    "scroll.in": 0.86,
    "thewire.in": 0.85,
    "livemint.com": 0.90,
    "business-standard.com": 0.90,
    "economictimes.indiatimes.com": 0.89,
    "hindustantimes.com": 0.87,
    "timesofindia.com": 0.86,
    "moneycontrol.com": 0.87,

    "bbc.com": 0.96,
    "bbc.co.uk": 0.96,
    "theguardian.com": 0.93,
    "nytimes.com": 0.93,
    "washingtonpost.com": 0.92,
    "bloomberg.com": 0.94,
    "ft.com": 0.93,
    "economist.com": 0.93,
    "aljazeera.com": 0.88,

    "mcxindia.com": 0.96,
    "ibja.co": 0.96,
    "goodreturns.in": 0.88,
    "gold.org": 0.96,
    "sebi.gov.in": 0.97,
    "rbi.org.in": 0.97,

    "pib.gov.in": 0.97,
    "india.gov.in": 0.97,
    "who.int": 0.97,
    "un.org": 0.96,
    "nato.int": 0.95,
    "worldbank.org": 0.95,

    "altnews.in": 0.96,
    "boomlive.in": 0.95,
    "factchecker.in": 0.95,
    "snopes.com": 0.94,
    "factcheck.org": 0.94,
    "vishvasnews.com": 0.90,
    "newschecker.in": 0.90,

    "redcrossblood.org": 0.97,
    "stanfordbloodcenter.org": 0.96,
    "nhs.uk": 0.96,
    "mayoclinic.org": 0.96,
    "cdc.gov": 0.97,
    "healthline.com": 0.86,

    "crunchbase.com": 0.88,
    "tracxn.com": 0.85,
    "inc42.com": 0.84,
    "techcrunch.com": 0.87,
    "forbes.com": 0.88,
}

TRUSTED_NEWSAPI_DOMAINS = ",".join([
    "reuters.com", "apnews.com", "bbc.com",
    "thehindu.com", "ndtv.com", "indianexpress.com",
    "bloomberg.com", "economictimes.indiatimes.com",
    "livemint.com", "business-standard.com",
    "theguardian.com", "altnews.in", "boomlive.in",
    "moneycontrol.com", "theprint.in",
    "timesofindia.com", "hindustantimes.com"
])

RELEVANCE_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "have",
    "has", "had", "into", "over", "under", "near", "about", "after",
    "before", "today", "latest", "news", "right", "now", "nearly"
}


def _extract_blood_groups(text: str) -> list:
    normalized = (text or "").lower()
    normalized = normalized.replace("0+", "o+")
    normalized = normalized.replace("0-", "o-")
    matches = re.findall(
        r"\b(?:ab|a|b|o)\s*[\+\-](?=\b|\s|$)",
        normalized
    )
    return [m.replace(" ", "") for m in matches]


def _is_blood_group_query(query: str) -> bool:
    lower = (query or "").lower()
    return (
        "blood" in lower and "group" in lower
    ) or bool(_extract_blood_groups(lower))


def _query_terms(query: str) -> list:
    tokens = re.findall(r"[a-z0-9]+", (query or "").lower())
    return [t for t in tokens if len(t) >= 3 and t not in RELEVANCE_STOPWORDS]


def _relevance_score(query: str, title: str, content: str = "") -> float:
    terms = _query_terms(query)
    if not terms:
        return 0.75

    haystack = f"{title or ''} {content or ''}".lower()
    matches = sum(1 for term in terms if term in haystack)
    base = matches / max(len(terms), 1)

    if _is_blood_group_query(query):
        query_groups = set(_extract_blood_groups(query))
        article_groups = set(_extract_blood_groups(haystack))
        if query_groups and article_groups and not query_groups.intersection(article_groups):
            base *= 0.4

    return max(0.35, min(0.99, base))


def _is_relevant_result(query: str, title: str, content: str = "") -> bool:
    terms = _query_terms(query)
    if not terms:
        return True

    haystack = f"{title or ''} {content or ''}".lower()
    matches = sum(1 for term in terms if term in haystack)

    if _is_blood_group_query(query):
        topic_terms = [
            "blood", "group", "transfusion",
            "donor", "recipient", "compatib"
        ]
        if not any(term in haystack for term in topic_terms):
            return False

        query_groups = set(_extract_blood_groups(query))
        article_groups = set(_extract_blood_groups(haystack))
        if query_groups and article_groups and not query_groups.intersection(article_groups):
            return False
        return matches >= 2

    if "gold" in terms:
        return "gold" in haystack and matches >= 2

    min_matches = 2 if len(terms) >= 4 else 1
    return matches >= min_matches

def get_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""

def get_credibility(url: str) -> float:
    domain = get_domain(url)
    for trusted, score in TRUSTED_SOURCES.items():
        if trusted in domain:
            return score
    return 0.0

def format_date(raw: str) -> str:
    for fmt in ["%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(raw[:19], fmt[:len(raw[:19])])
            return dt.strftime("%d %B %Y")
        except Exception:
            continue
    return raw[:10] if raw else datetime.now().strftime(
        "%d %B %Y")

def make_article(title, content, source_name,
                 url, author, date_raw,
                 cred, source_type, evidence_source,
                 logo="📰", relevance_score=0.85) -> dict:
    return {
        "title": title or "",
        "content": (content or "")[:300],
        "source": source_name or get_domain(url),
        "source_url": url or "",
        "author": author or "Staff",
        "published_date": format_date(date_raw or ""),
        "credibility_score": cred,
        "source_logo": logo,
        "source_type": source_type,
        "relevance_score": relevance_score,
        "is_realtime": True,
        "evidence_source": evidence_source,
        "combined_score": (cred * 0.5) + (relevance_score * 0.5)
    }

def search_newsapi(
    query: str,
    blocked_keywords: list = []
) -> list:
    if not NEWSAPI_KEY:
        print("[NewsAPI] No API key configured")
        return []

    try:
        print(f"[NewsAPI] Searching: '{query}'")
        client = NewsApiClient(api_key=NEWSAPI_KEY)

        # For finance/commodity queries, use finance-specific domains only
        finance_keywords = [
            "gold", "silver", "rupee", "mcx", 
            "rate", "price", "stock", "sensex",
            "nifty", "commodity", "crude"
        ]
        query_lower = query.lower()
        is_finance = any(
            fk in query_lower for fk in finance_keywords
        )
        
        if is_finance:
            # Use ONLY financial news domains
            domains = ",".join([
                "economictimes.indiatimes.com",
                "livemint.com",
                "business-standard.com",
                "moneycontrol.com",
                "thehindubusinessline.com",
                "financialexpress.com",
                "goodreturns.in",
                "ndtvprofit.com"
            ])
        else:
            domains = TRUSTED_NEWSAPI_DOMAINS

        response = client.get_everything(
            q=query,
            domains=domains,
            language="en",
            sort_by="relevancy",
            page_size=15
        )

        if response.get("status") != "ok":
            print(f"[NewsAPI] Error: "
                  f"{response.get('message')}")
            return []

        articles = []
        for item in response.get("articles", []):
            url = item.get("url", "")
            title = item.get("title", "")
            content = (item.get("description") or
                       item.get("content") or "")

            if not _is_relevant_result(query, title, content):
                continue

            if any(bk.lower() in url.lower()
                   for bk in blocked_keywords):
                continue

            cred = get_credibility(url)
            if cred == 0.0:
                cred = 0.78

            source_name = (item.get("source", {})
                              .get("name", ""))
            relevance = _relevance_score(query, title, content)

            articles.append(make_article(
                title=title,
                content=content,
                source_name=source_name,
                url=url,
                author=item.get("author"),
                date_raw=item.get("publishedAt", ""),
                cred=cred,
                source_type="News Article",
                evidence_source="newsapi",
                logo="📰",
                relevance_score=relevance
            ))

        print(f"[NewsAPI] Found {len(articles)} articles")
        return articles

    except Exception as e:
        print(f"[NewsAPI] Failed: {e}")
        return []

def search_serpapi(
    query: str,
    blocked_keywords: list = []
) -> list:
    if not SERPAPI_KEY:
        print("[SerpAPI] No API key configured")
        return []

    query_lower = (query or "").lower()
    
    # Detect finance/commodity queries
    finance_keywords = [
        "gold", "silver", "rupee", "mcx",
        "commodity", "price drop", "rate fell"
    ]
    is_finance = any(
        fk in query_lower for fk in finance_keywords
    )
    
    is_blood_group = _is_blood_group_query(query)

    if is_blood_group:
        search_query = (
            f"{query} "
            f"site:redcrossblood.org OR "
            f"site:stanfordbloodcenter.org OR "
            f"site:nhs.uk OR "
            f"site:mayoclinic.org OR "
            f"site:cdc.gov"
        )
    elif is_finance:
        search_query = (
            f"{query} "
            f"site:economictimes.indiatimes.com OR "
            f"site:livemint.com OR "
            f"site:moneycontrol.com OR "
            f"site:business-standard.com OR "
            f"site:goodreturns.in OR "
            f"site:thehindubusinessline.com"
        )
    else:
        search_query = (
            f"{query} "
            f"site:reuters.com OR site:bbc.com OR "
            f"site:thehindu.com OR site:ndtv.com OR "
            f"site:apnews.com OR site:indianexpress.com"
        )

    try:
        print(f"[SerpAPI] Searching: '{query}'")
        params = {
            "engine": "google",
            "q": search_query,
            "api_key": SERPAPI_KEY,
            "num": 10,
            "hl": "en",
            "gl": "in"
        }
        if not is_blood_group:
            params["tbm"] = "nws"

        search = GoogleSearch(params)
        results = search.get_dict()

        items = (results.get("news_results") or
                 results.get("organic_results") or [])

        articles = []
        for item in items:
            url = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            if not url or not title:
                continue

            if not _is_relevant_result(query, title, snippet):
                continue

            if any(bk.lower() in url.lower()
                   for bk in blocked_keywords):
                print(f"[SerpAPI] Blocked: {url}")
                continue

            cred = get_credibility(url)
            if cred == 0.0:
                print(f"[SerpAPI] Skipped untrusted: "
                      f"{url}")
                continue

            relevance = _relevance_score(query, title, snippet)

            articles.append(make_article(
                title=title,
                content=snippet,
                source_name=item.get("source", ""),
                url=url,
                author=None,
                date_raw=item.get("date", ""),
                cred=cred,
                source_type="Live Search",
                evidence_source="serpapi",
                logo="🔍",
                relevance_score=relevance
            ))

        print(f"[SerpAPI] Found {len(articles)} "
              f"trusted articles")
        return articles

    except Exception as e:
        print(f"[SerpAPI] Failed: {e}")
        return []

def search_all(
    query: str,
    blocked_keywords: list = []
) -> list:
    print(f"\n[Search] Running dual search for: '{query}'")

    all_articles = []

    news = search_newsapi(query, blocked_keywords)
    serp = search_serpapi(query, blocked_keywords)

    all_articles.extend(news)
    all_articles.extend(serp)

    seen = set()
    unique = []
    for a in all_articles:
        url = a.get("source_url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(a)

    ranked = sorted(
        unique,
        key=lambda x: x.get("combined_score", 0),
        reverse=True
    )

    print(f"[Search] Total unique trusted articles: "
          f"{len(ranked)}")
    for i, a in enumerate(ranked[:5], 1):
        print(f"  {i}. [{a['source']}] "
              f"{a['title'][:55]} "
              f"(cred={a['credibility_score']:.2f})")

    return ranked[:8]
