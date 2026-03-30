"""
backend/rag/evidence_retriever.py
Combines: Knowledge Base + RSS + NewsAPI + SerpAPI
Blocks subject's own website from appearing as evidence.
"""

import feedparser
from datetime import datetime
from rag.knowledge_base import KNOWLEDGE_BASE
from rag.search_client import (
    search_all, get_credibility, get_domain
)

RSS_FEEDS = {
    "Reuters":
        "https://feeds.reuters.com/reuters/topNews",
    "BBC":
        "http://feeds.bbci.co.uk/news/rss.xml",
    "NDTV":
        "https://feeds.feedburner.com/ndtvnews-top-stories",
    "The Hindu":
        "https://www.thehindu.com/news/feeder/default.rss",
    "Indian Express":
        "https://indianexpress.com/feed/",
    "Economic Times":
        "https://economictimes.indiatimes.com/"
        "rssfeedsdefault.cms",
    "Live Mint":
        "https://www.livemint.com/rss/news",
}

RSS_STOPWORDS = {
    "the", "and", "for", "with", "from", "that",
    "this", "have", "has", "had", "into", "over",
    "under", "about", "after", "before", "today",
    "latest", "news", "right", "now", "person",
    "his", "her", "can"
}


def _rss_terms(keywords: list) -> list:
    terms = []
    for keyword in keywords or []:
        value = (keyword or "").strip().lower()
        if len(value) < 4 or value in RSS_STOPWORDS:
            continue
        if value not in terms:
            terms.append(value)
    return terms

def search_rss(keywords: list, claim: str = "") -> list:
    articles = []
    kw_lower = _rss_terms(keywords)
    claim_lower = (claim or "").lower()
    blood_query = "blood" in claim_lower and "group" in claim_lower

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:25]:
                title = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                haystack = f"{title} {summary}"
                matches = sum(
                    1 for kw in kw_lower
                    if kw in haystack
                )
                if matches < 2:
                    continue

                if blood_query and not any(
                    token in haystack
                    for token in [
                        "blood", "transfusion",
                        "donor", "recipient", "rh"
                    ]
                ):
                    continue

                link = entry.get("link", "")
                cred = (get_credibility(link)
                        or 0.88)
                relevance = min(0.95, 0.45 + (0.12 * matches))
                articles.append({
                    "title": entry.get("title", ""),
                    "content":
                        entry.get("summary","")[:300],
                    "source": source_name,
                    "source_url": link,
                    "author": "Staff",
                    "published_date":
                        datetime.now().strftime(
                            "%d %B %Y"),
                    "credibility_score": cred,
                    "source_logo": "📡",
                    "source_type": "RSS Feed",
                    "relevance_score": relevance,
                    "is_realtime": True,
                    "evidence_source": "rss",
                    "combined_score": (cred * 0.5) +
                                      (relevance * 0.5)
                })
        except Exception as e:
            print(f"[RSS:{source_name}] Error: {e}")

    print(f"[RSS] Found {len(articles)} matching articles")
    return articles

def search_knowledge_base(claim: str) -> list:
    articles = []
    claim_lower = claim.lower()
    for key, fact in KNOWLEDGE_BASE.items():
        if key in claim_lower:
            articles.append({
                "title": f"Verified Fact: {key.title()}",
                "content": fact,
                "source": "VeritasAI Knowledge Base",
                "source_url": "",
                "author": "Verified",
                "published_date": "2026",
                "credibility_score": 0.99,
                "source_logo": "✅",
                "source_type": "Knowledge Base",
                "relevance_score": 1.0,
                "is_realtime": False,
                "evidence_source": "knowledge_base",
                "combined_score": 0.99
            })
    print(f"[KB] Found {len(articles)} knowledge base hits")
    return articles


def _build_search_query(claim: str, keywords: list, domain: str) -> str:
    claim_text = (claim or "").strip()
    lower_claim = claim_text.lower()

    if "blood" in lower_claim and "group" in lower_claim:
        return (
            f'{claim_text} ABO Rh blood transfusion '
            f'donor recipient compatibility chart'
        )

    keyword_tail = " ".join((keywords or [])[:4]).strip()
    if keyword_tail:
        return f"{claim_text} {keyword_tail}".strip()
    return claim_text

def retrieve(
    claim: str,
    keywords: list,
    domain: str,
    entities: list = []
) -> list:
    print(f"\n{'='*50}")
    print(f"[Evidence] Claim: '{claim}'")
    print(f"[Evidence] Keywords: {keywords}")
    print(f"[Evidence] Entities: {entities}")
    print(f"{'='*50}")

    blocked = []
    for entity in entities:
        blocked.append(entity.lower().replace(" ", ""))
    if blocked:
        print(f"[Evidence] Blocking domains with: "
              f"{blocked}")

    search_query = _build_search_query(claim, keywords, domain)
    all_articles = []

    kb = search_knowledge_base(claim)
    all_articles.extend(kb)

    live = search_all(search_query, blocked)
    all_articles.extend(live)

    rss = search_rss(keywords[:6], claim)
    all_articles.extend(rss)

    if not all_articles:
        print("[Evidence] ⚠️  No articles found")
        return []

    seen_urls = set()
    unique = []
    for a in all_articles:
        url = a.get("source_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(a)
        elif not url:
            unique.append(a)

    ranked = sorted(
        unique,
        key=lambda x: x.get("combined_score", 0),
        reverse=True
    )[:5]

    print(f"\n[Evidence] FINAL TOP {len(ranked)} SOURCES:")
    for i, a in enumerate(ranked, 1):
        print(f"  {i}. [{a['source']}] "
              f"{a['title'][:55]}")
        print(f"     cred={a['credibility_score']:.2f} | "
              f"score={a['combined_score']:.2f} | "
              f"via={a['evidence_source']}")

    return ranked
