import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from credibility import score_source
from rag.embeddings import embed_query, embed_texts
from rag.faiss_store import FaissStore

LOGGER = logging.getLogger("veritas.retriever")

BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "").strip()

FALLBACK_DATASET = BASE_DIR / "data" / "news_articles.json"

LOW_QUALITY_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "reddit.com",
    "quora.com",
    "pinterest.com",
    "consent.yahoo.com",
}

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


def _domain(url: str) -> str:
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "").strip()
    except Exception:
        return ""


def _is_low_quality(url: str) -> bool:
    domain = _domain(url)
    if not domain:
        return True
    return any(domain == bad or domain.endswith(f".{bad}") for bad in LOW_QUALITY_DOMAINS)


def _clean_text(value: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _query_terms(claim: str, keywords: List[str] | None = None) -> List[str]:
    terms = []
    for token in re.findall(r"[a-z0-9]+", (claim or "").lower()):
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token not in terms:
            terms.append(token)

    for token in keywords or []:
        norm = re.sub(r"[^a-z0-9]+", "", str(token or "").lower())
        if len(norm) < 3 or norm in STOPWORDS:
            continue
        if norm not in terms:
            terms.append(norm)

    return terms


def _build_query(claim: str, keywords: List[str] | None = None) -> str:
    terms = _query_terms(claim, keywords)
    if terms:
        return " ".join(terms[:10])
    return (claim or "").strip()


def _relevance_score(claim: str, article: Dict, keywords: List[str] | None = None) -> float:
    terms = _query_terms(claim, keywords)
    if not terms:
        return 0.5

    haystack = (
        f"{article.get('title', '')} "
        f"{article.get('content', '')} "
        f"{article.get('source', '')}"
    ).lower()

    matches = sum(1 for t in terms if t in haystack)
    score = matches / max(1, len(terms))

    phrases = [f"{terms[i]} {terms[i + 1]}" for i in range(len(terms) - 1)]
    phrase_hits = sum(1 for p in phrases if p in haystack)
    if phrase_hits:
        score += min(0.4, phrase_hits * 0.2)

    if len(terms) >= 3 and matches <= 1:
        score *= 0.45

    return max(0.0, min(1.0, round(score, 3)))


def _standard_article(
    title: str,
    source: str,
    content: str,
    url: str,
    published_date: str,
    evidence_source: str,
) -> Dict:
    credibility = float(score_source(url))
    return {
        "title": _clean_text(title, 220),
        "source": source or _domain(url) or "Unknown",
        "content": _clean_text(content, 420),
        "url": url,
        "source_url": url,
        "published_date": published_date or "",
        "credibility_score": credibility,
        "evidence_source": evidence_source,
    }


def _search_serpapi(query: str) -> Tuple[List[Dict], Dict]:
    meta = {"ok": False, "status_code": None, "error": None, "count": 0}
    if not SERPAPI_KEY:
        meta["error"] = "SERPAPI_KEY missing"
        LOGGER.warning("[Retriever][SerpAPI] %s", meta["error"])
        return [], meta

    params = {
        "engine": "google",
        "tbm": "nws",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 12,
        "hl": "en",
        "gl": "in",
    }

    LOGGER.info("[Retriever][SerpAPI] Request query='%s'", query)
    try:
        response = requests.get("https://serpapi.com/search.json", params=params, timeout=25)
        meta["status_code"] = response.status_code
        LOGGER.info("[Retriever][SerpAPI] Response status=%s", response.status_code)

        if response.status_code >= 400:
            meta["error"] = f"HTTP {response.status_code}: {_clean_text(response.text, 240)}"
            LOGGER.warning("[Retriever][SerpAPI] Failure: %s", meta["error"])
            return [], meta

        payload = response.json()
        items = payload.get("news_results") or payload.get("organic_results") or []

        articles: List[Dict] = []
        for item in items:
            link = item.get("link", "")
            if not link or _is_low_quality(link):
                continue
            articles.append(
                _standard_article(
                    title=item.get("title", ""),
                    source=item.get("source", ""),
                    content=item.get("snippet", ""),
                    url=link,
                    published_date=item.get("date", ""),
                    evidence_source="serpapi",
                )
            )

        meta["ok"] = True
        meta["count"] = len(articles)
        return articles, meta
    except Exception as exc:
        meta["error"] = str(exc)
        LOGGER.exception("[Retriever][SerpAPI] Exception while searching")
        return [], meta


def _search_newsapi(query: str) -> Tuple[List[Dict], Dict]:
    meta = {"ok": False, "status_code": None, "error": None, "count": 0}
    if not NEWSAPI_KEY:
        meta["error"] = "NEWSAPI_KEY missing"
        LOGGER.warning("[Retriever][NewsAPI] %s", meta["error"])
        return [], meta

    params = {
        "q": query,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 20,
        "apiKey": NEWSAPI_KEY,
    }

    LOGGER.info("[Retriever][NewsAPI] Request query='%s'", query)
    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params, timeout=25)
        meta["status_code"] = response.status_code
        LOGGER.info("[Retriever][NewsAPI] Response status=%s", response.status_code)

        if response.status_code >= 400:
            meta["error"] = f"HTTP {response.status_code}: {_clean_text(response.text, 240)}"
            LOGGER.warning("[Retriever][NewsAPI] Failure: %s", meta["error"])
            return [], meta

        payload = response.json()
        if payload.get("status") != "ok":
            meta["error"] = payload.get("message", "Unknown NewsAPI error")
            LOGGER.warning("[Retriever][NewsAPI] Failure: %s", meta["error"])
            return [], meta

        articles: List[Dict] = []
        for item in payload.get("articles", []):
            link = item.get("url", "")
            if not link or _is_low_quality(link):
                continue

            content = item.get("description") or item.get("content") or ""
            source_name = (item.get("source") or {}).get("name", "")
            articles.append(
                _standard_article(
                    title=item.get("title", ""),
                    source=source_name,
                    content=content,
                    url=link,
                    published_date=item.get("publishedAt", ""),
                    evidence_source="newsapi",
                )
            )

        meta["ok"] = True
        meta["count"] = len(articles)
        return articles, meta
    except Exception as exc:
        meta["error"] = str(exc)
        LOGGER.exception("[Retriever][NewsAPI] Exception while searching")
        return [], meta


def _dedupe(articles: List[Dict]) -> List[Dict]:
    deduped: List[Dict] = []
    seen = set()
    for article in articles:
        key = (article.get("url") or article.get("source_url") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


def _load_local_fallback(claim: str, keywords: List[str] | None = None) -> List[Dict]:
    if not FALLBACK_DATASET.exists():
        return []

    try:
        with open(FALLBACK_DATASET, "r", encoding="utf-8") as file:
            rows = json.load(file)
    except Exception:
        LOGGER.exception("[Retriever] Failed to load local fallback dataset")
        return []

    candidate_articles: List[Dict] = []
    for row in rows:
        article = _standard_article(
            title=row.get("title", ""),
            source=row.get("source", "local-dataset"),
            content=row.get("content", ""),
            url=row.get("link", ""),
            published_date=row.get("date", ""),
            evidence_source="local_fallback",
        )
        article["relevance_score"] = _relevance_score(claim, article, keywords)
        candidate_articles.append(article)

    candidate_articles.sort(key=lambda a: a.get("relevance_score", 0.0), reverse=True)
    LOGGER.warning("[Retriever] Using local fallback dataset with %s candidates", len(candidate_articles))
    return candidate_articles


def retrieve_evidence(
    claim: str,
    keywords: List[str] | None = None,
    domain: str = "general",
    top_k: int = 5,
    max_retries: int = 1,
) -> Tuple[List[Dict], Dict]:
    """
    Real RAG flow:
      claim -> SerpAPI+NewsAPI -> clean/filter -> embeddings -> FAISS cosine search -> top-k evidence
    """
    if not claim.strip():
        return [], {"error": "Empty claim", "fallback_used": False}

    query = _build_query(claim, keywords)
    LOGGER.info("[Retriever] Starting retrieval claim='%s' query='%s' domain=%s", claim, query, domain)

    combined_articles: List[Dict] = []
    api_runs = []

    attempts = max(1, max_retries + 1)
    for attempt in range(attempts):
        run_query = query if attempt == 0 else _build_query(claim)
        LOGGER.info("[Retriever] Search attempt %s query='%s'", attempt + 1, run_query)

        serp_articles, serp_meta = _search_serpapi(run_query)
        news_articles, news_meta = _search_newsapi(run_query)

        api_runs.append({"attempt": attempt + 1, "serpapi": serp_meta, "newsapi": news_meta})
        combined_articles = _dedupe(serp_articles + news_articles)

        if combined_articles:
            break

    for article in combined_articles:
        article["relevance_score"] = _relevance_score(claim, article, keywords)

    filtered = [a for a in combined_articles if a.get("relevance_score", 0.0) >= 0.15]
    if not filtered:
        filtered = sorted(combined_articles, key=lambda a: a.get("relevance_score", 0.0), reverse=True)[:12]

    fallback_used = False
    if not filtered:
        filtered = _load_local_fallback(claim, keywords)
        fallback_used = True

    if not filtered:
        LOGGER.warning("[Retriever] No evidence found after APIs and fallback")
        return [], {
            "query": query,
            "api_runs": api_runs,
            "fallback_used": fallback_used,
            "retrieved_count": 0,
            "top_k": [],
        }

    texts = [f"{a.get('title', '')} {a.get('content', '')}" for a in filtered]
    vectors = embed_texts(texts)
    query_vec = embed_query(claim).reshape(1, -1)

    store = FaissStore(dimension=vectors.shape[1])
    store.add_documents(vectors, filtered)
    hits = store.search(query_vec, k=min(top_k, len(filtered)))

    ranked: List[Dict] = []
    top_log = []
    for hit in hits:
        article = dict(hit["document"])
        similarity = float(hit["similarity"])
        article["similarity_score"] = round(similarity, 4)

        credibility = float(article.get("credibility_score", 0.5))
        article["rag_score"] = round((0.65 * similarity) + (0.35 * credibility), 4)
        ranked.append(article)

        top_log.append(
            {
                "title": article.get("title", "")[:120],
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "similarity": round(similarity, 4),
                "credibility": round(credibility, 3),
            }
        )

    ranked.sort(key=lambda a: a.get("rag_score", 0.0), reverse=True)

    LOGGER.info("[Retriever] Retrieved sources count=%s", len(ranked))
    for i, item in enumerate(ranked[:top_k], start=1):
        LOGGER.info(
            "[Retriever] Top-%s sim=%.4f rag=%.4f source=%s title=%s",
            i,
            float(item.get("similarity_score", 0.0)),
            float(item.get("rag_score", 0.0)),
            item.get("source", "Unknown"),
            item.get("title", "")[:90],
        )

    return ranked[:top_k], {
        "query": query,
        "api_runs": api_runs,
        "fallback_used": fallback_used,
        "retrieved_count": len(ranked[:top_k]),
        "top_k": top_log,
    }
