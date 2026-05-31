"""
tavily_client.py — VeritasAI Tavily search provider (PRIMARY).

Tavily is the primary web-search evidence provider in the retrieval chain
(Tavily -> SerpAPI -> NewsAPI -> local). It requests raw_content so agents get
richer evidence, then cleans and length-caps the text to control token usage.

Flow per result: raw_content -> clean -> (chunking handled downstream) ->
normalized standard-article dict.

Observability: every search emits
  TAVILY QUERY / TAVILY RESULTS COUNT / TAVILY SOURCES / TAVILY RESPONSE
and every discarded result logs a DISCARDED line with source/title/reason.

The module NEVER raises out of search_tavily(); on any failure it returns
([], meta) so the retrieval chain degrades gracefully to other providers.
"""

import logging
import os
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv

try:
    from credibility import score_source
except Exception:  # pragma: no cover - defensive import
    def score_source(url: str) -> float:
        return 0.5

LOGGER = logging.getLogger("veritas.tavily")

load_dotenv()

TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()
TAVILY_SEARCH_DEPTH = (os.getenv("TAVILY_SEARCH_DEPTH") or "advanced").strip()
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "10"))
TAVILY_INCLUDE_RAW_CONTENT = os.getenv("TAVILY_INCLUDE_RAW_CONTENT", "1") != "0"

# Length caps to control token usage downstream.
CONTENT_SNIPPET_LIMIT = 420
RAW_CONTENT_LIMIT = 1600

tavily_available = bool(TAVILY_API_KEY and TAVILY_API_KEY.upper() != "DISABLED")


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


LOGGER.info(
    "[Tavily] init available=%s key=%s depth=%s max_results=%s raw_content=%s",
    tavily_available,
    _mask_secret(TAVILY_API_KEY),
    TAVILY_SEARCH_DEPTH,
    TAVILY_MAX_RESULTS,
    TAVILY_INCLUDE_RAW_CONTENT,
)


def _domain(url: str) -> str:
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "").strip()
    except Exception:
        return ""


def _clean_text(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _normalize_result(raw: Dict) -> Dict | None:
    """Map a single Tavily result to the standard article shape.

    Returns None (and the caller logs DISCARDED) when there is no usable URL.
    """
    url = str(raw.get("url") or "").strip()
    if not url:
        return None

    title = str(raw.get("title") or "").strip()
    snippet = str(raw.get("content") or "").strip()
    raw_content = str(raw.get("raw_content") or "").strip()

    # Prefer the snippet for the short `content` field; keep cleaned raw_content
    # in `full_content` for richer agent reasoning (length-capped).
    content = _clean_text(snippet or raw_content, CONTENT_SNIPPET_LIMIT)
    full_content = _clean_text(raw_content or snippet, RAW_CONTENT_LIMIT)

    domain = _domain(url)
    try:
        credibility = float(score_source(url))
    except Exception:
        credibility = 0.5
    credibility = max(0.0, min(1.0, credibility))

    return {
        "title": _clean_text(title, 220) or (domain or "Untitled source"),
        "source": domain or "Unknown",
        "content": content,
        "url": url,
        "source_url": url,
        "published_date": str(raw.get("published_date") or "").strip(),
        "credibility_score": credibility,
        "evidence_source": "tavily",
        "source_type": "web",
        "full_content": full_content,
        "tavily_score": float(raw.get("score") or 0.0),
    }


def search_tavily(
    query: str,
    top_n: int = TAVILY_MAX_RESULTS,
    include_raw: bool = TAVILY_INCLUDE_RAW_CONTENT,
) -> Tuple[List[Dict], Dict]:
    """Query Tavily and return (normalized_articles, meta).

    Never raises: returns ([], meta) when the key is missing or the request
    fails, so the retrieval chain can fall through to other providers.
    """
    query = (query or "").strip()
    meta: Dict = {
        "provider": "tavily",
        "ok": False,
        "query": query,
        "count": 0,
        "error": None,
        "discarded": [],
    }

    LOGGER.info("TAVILY QUERY: %s", query)

    if not tavily_available:
        meta["error"] = "TAVILY_API_KEY missing or disabled"
        LOGGER.warning("[Tavily] skipped — %s", meta["error"])
        LOGGER.info("TAVILY RESULTS COUNT: 0 (skipped)")
        return [], meta

    if not query:
        meta["error"] = "empty query"
        LOGGER.info("TAVILY RESULTS COUNT: 0 (empty query)")
        return [], meta

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth=TAVILY_SEARCH_DEPTH,
            max_results=max(1, int(top_n)),
            include_raw_content=bool(include_raw),
            include_answer=False,
        )
    except Exception as exc:  # network, auth, quota, packaging — all non-fatal
        meta["error"] = str(exc)[:200]
        LOGGER.warning("[Tavily] search failed: %s", meta["error"])
        LOGGER.info("TAVILY RESULTS COUNT: 0 (error)")
        return [], meta

    raw_results = (response or {}).get("results") or []
    LOGGER.info("TAVILY RESULTS COUNT: %s", len(raw_results))

    articles: List[Dict] = []
    discarded: List[Dict] = []
    for raw in raw_results:
        normalized = _normalize_result(raw)
        if normalized is None:
            title = str((raw or {}).get("title") or "").strip() or "Untitled"
            src = _domain(str((raw or {}).get("url") or "")) or "unknown"
            discarded.append({"source": src, "title": title, "reason": "missing url"})
            LOGGER.info("DISCARDED: missing url | source=%s | title=%s", src, title[:80])
            continue
        articles.append(normalized)

    sources = [a["source"] for a in articles]
    LOGGER.info("TAVILY SOURCES: %s", sources)
    # Truncated response preview for debugging.
    preview = "; ".join(f"{a['source']}: {a['title'][:60]}" for a in articles[:5])
    LOGGER.info("TAVILY RESPONSE: %s", preview[:500])

    meta.update({"ok": True, "count": len(articles), "discarded": discarded, "sources": sources})
    return articles, meta
