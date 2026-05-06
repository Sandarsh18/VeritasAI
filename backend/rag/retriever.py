import copy
import json
import logging
import os
import re
import time
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import numpy as np
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from credibility import score_source
from llm_client import OLLAMA_ANALYZER, call_ollama, extract_json
from rag.embeddings import embed_query, embed_texts
from rag.faiss_store import FaissStore
from services.ranking_service import compare_retrieval_modes, extract_keywords, rank_articles

LOGGER = logging.getLogger("veritas.retriever")

BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)

SERPAPI_KEY = (os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY") or "").strip()
NEWSAPI_KEY = (os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY") or "").strip()


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


LOGGER.info(
    "[Retriever] API key presence serpapi=%s newsapi=%s",
    _mask_secret(os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")),
    _mask_secret(os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")),
)

FALLBACK_DATASET = BASE_DIR / "data" / "news_articles.json"

SIMILARITY_THRESHOLD = 0.42  # Lowered from 0.65 for more inclusive retrieval
SIMILARITY_THRESHOLD_STRICT = 0.50  # Stricter threshold for second-pass filtering
KEYWORD_OVERLAP_THRESHOLD = 0.30
MIN_CREDIBILITY = 0.55
HYBRID_SCORE_WEIGHT_EMBEDDING = 0.6  # Weight for embedding similarity in hybrid scoring
HYBRID_SCORE_WEIGHT_KEYWORD = 0.4  # Weight for BM25 keyword score in hybrid scoring

API_MAX_RETRIES = 2
API_RETRY_BACKOFF_BASE = 1.0  # seconds

BLACKLIST_TERMS = ["quora", "reddit", "blogspot"]

LOW_QUALITY_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "reddit.com",
    "quora.com",
    "blogspot.com",
    "pinterest.com",
    "consent.yahoo.com",
    "espn.com",
    "tmz.com",
    "buzzfeed.com",
    "dailymail.co.uk",
}

TRUSTED_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
    "bloomberg.com",
    "economist.com",
    "ft.com",
    "thehindu.com",
    "indianexpress.com",
    "ndtv.com",
    "theprint.in",
    "livemint.com",
    "business-standard.com",
    "economictimes.indiatimes.com",
    "hindustantimes.com",
    "timesofindia.com",
    "moneycontrol.com",
    "altnews.in",
    "boomlive.in",
    "factcheck.org",
    "snopes.com",
    "who.int",
    "cdc.gov",
    "nih.gov",
    "un.org",
    "worldbank.org",
}

NEWSAPI_TRUSTED_DOMAINS = ",".join(
    [
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "theguardian.com",
        "nytimes.com",
        "washingtonpost.com",
        "bloomberg.com",
        "thehindu.com",
        "indianexpress.com",
        "ndtv.com",
        "theprint.in",
        "livemint.com",
        "business-standard.com",
        "economictimes.indiatimes.com",
        "hindustantimes.com",
        "timesofindia.com",
        "moneycontrol.com",
        "altnews.in",
        "boomlive.in",
    ]
)

CLICKBAIT_TERMS = {
    "you won't believe",
    "shocking",
    "viral",
    "watch",
    "exclusive",
    "celeb",
    "celebrity",
    "gossip",
    "rumor",
    "rumour",
    "fan war",
    "hot take",
    "trending now",
    "click here",
}

OFFTOPIC_TERMS = {
    "box office",
    "movie release",
    "music video",
    "celebrity",
    "fashion",
    "makeup",
    "cricket fantasy",
    "dream11",
}

# Misinformation-aware query expansion patterns
MISINFO_EXPANSION = {
    "5g": ["5G conspiracy debunked", "WHO 5G safety", "5G health myth fact check"],
    "covid": ["COVID misinformation", "WHO myth fact check", "pandemic hoax debunked"],
    "vaccine": ["vaccine safety CDC", "vaccine myth debunked", "WHO vaccine facts"],
    "flat earth": ["flat earth debunked", "NASA earth shape evidence"],
    "climate": ["climate change evidence IPCC", "global warming scientific consensus"],
    "gmo": ["GMO safety scientific consensus", "GMO myth fact check"],
    "chemtrail": ["chemtrail conspiracy debunked", "contrails scientific explanation"],
}

NAV_GARBAGE_PATTERNS = [
    r"cookie", r"dropdown", r"nav-menu", r"sidebar", r"footer",
    r"subscribe", r"sign.?up", r"log.?in", r"newsletter",
    r"advertisement", r"sponsored", r"related articles",
]


def _retry_request(url: str, params: dict, timeout: int = 15, max_retries: int = API_MAX_RETRIES) -> requests.Response:
    """HTTP GET with exponential backoff retry."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            attempt_timeout = timeout + (attempt * 5)
            response = requests.get(url, params=params, timeout=attempt_timeout)
            if response.status_code == 429 and attempt < max_retries:
                wait = API_RETRY_BACKOFF_BASE * (2 ** attempt)
                LOGGER.warning("[SEARCH] Rate limited (429), retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
                continue
            return response
        except requests.exceptions.Timeout as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = API_RETRY_BACKOFF_BASE * (2 ** attempt)
                LOGGER.warning("[SEARCH] Timeout, retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                LOGGER.error("[SEARCH] All %d retry attempts timed out", max_retries + 1)
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = API_RETRY_BACKOFF_BASE * (2 ** attempt)
                LOGGER.warning("[SEARCH] Request error: %s, retrying in %.1fs", str(exc)[:80], wait)
                time.sleep(wait)
            else:
                LOGGER.error("[SEARCH] All retry attempts failed: %s", str(exc)[:120])
    raise last_exc or RuntimeError("All retry attempts exhausted")


def _expand_misinfo_queries(claim: str, base_variants: List[str]) -> List[str]:
    """Add misinformation-specific query variants when applicable."""
    claim_lower = (claim or "").lower()
    extra = []
    for trigger, expansions in MISINFO_EXPANSION.items():
        if trigger in claim_lower:
            extra.extend(expansions)
    # Deduplicate while preserving order
    seen = {v.lower().strip() for v in base_variants}
    for q in extra:
        norm = q.lower().strip()
        if norm not in seen:
            seen.add(norm)
            base_variants.append(q)
    return base_variants[:8]  # cap total variants

DOMAIN_HINTS = {
    "technology": [
        "ai",
        "artificial intelligence",
        "software",
        "app",
        "mobile",
        "phone",
        "internet",
        "chip",
        "robot",
        "5g",
        "6g",
        "telecom",
        "network",
    ],
    "politics": [
        "election",
        "minister",
        "parliament",
        "government",
        "policy",
        "vote",
        "party",
        "bjp",
        "congress",
        "diplomacy",
    ],
    "health": [
        "health",
        "covid",
        "vaccine",
        "virus",
        "disease",
        "hospital",
        "medical",
        "doctor",
        "treatment",
    ],
    "science": [
        "research",
        "study",
        "experiment",
        "climate",
        "physics",
        "chemistry",
        "biology",
        "nasa",
        "space",
    ],
    "sports": [
        "cricket",
        "ipl",
        "football",
        "tournament",
        "match",
        "world cup",
        "t20",
    ],
    "economy": [
        "economy",
        "gdp",
        "inflation",
        "market",
        "stock",
        "rupee",
        "tax",
        "budget",
    ],
    "religion": [
        "religion",
        "hindu",
        "islam",
        "christian",
        "temple",
        "mosque",
        "church",
        "bible",
        "quran",
    ],
}

GENERIC_ENTITY_TOKENS = {
    "claim",
    "country",
    "corrupt",
    "corruption",
    "ranking",
    "rank",
    "history",
    "origin",
    "timeline",
    "older",
    "newer",
    "language",
    "religion",
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

MAX_AGE_DAYS = int(os.getenv("RAG_MAX_AGE_DAYS", "120"))
API_CACHE_TTL_SECONDS = int(os.getenv("RAG_API_CACHE_TTL_SECONDS", "900"))
API_CACHE_MAX_ITEMS = int(os.getenv("RAG_API_CACHE_MAX_ITEMS", "256"))
DISABLE_ADVANCED_CACHE = os.getenv("VERITAS_DISABLE_ADVANCED_CACHE", "1") != "0"
USE_ADVANCED_RAG = os.getenv("VERITAS_USE_ADVANCED_RAG", "0") == "1"

_API_CACHE: "OrderedDict[tuple, dict]" = OrderedDict()


def _domain(url: str) -> str:
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "").strip()
    except Exception:
        return ""


def _is_blacklisted_url(url: str) -> bool:
    lowered = (url or "").lower()
    return any(term in lowered for term in BLACKLIST_TERMS)


def _is_low_quality(url: str) -> bool:
    domain = _domain(url)
    if not domain:
        return True
    if _is_blacklisted_url(url):
        return True
    return any(domain == bad or domain.endswith(f".{bad}") for bad in LOW_QUALITY_DOMAINS)


def _is_trusted_domain(url: str) -> bool:
    domain = _domain(url)
    if not domain:
        return False
    if any(domain == d or domain.endswith(f".{d}") for d in TRUSTED_DOMAINS):
        return True
    return float(score_source(url)) >= 0.72


def _clean_text(value: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _get_api_cache(key: tuple) -> dict | None:
    if DISABLE_ADVANCED_CACHE:
        return None
    if API_CACHE_TTL_SECONDS <= 0:
        return None
    now = time.time()
    entry = _API_CACHE.get(key)
    if not entry:
        return None
    if entry["expires_at"] <= now:
        _API_CACHE.pop(key, None)
        return None
    _API_CACHE.move_to_end(key)
    return copy.deepcopy(entry["payload"])


def _set_api_cache(key: tuple, payload: dict):
    if DISABLE_ADVANCED_CACHE:
        return
    if API_CACHE_TTL_SECONDS <= 0:
        return
    now = time.time()
    _API_CACHE[key] = {
        "payload": copy.deepcopy(payload),
        "expires_at": now + API_CACHE_TTL_SECONDS,
    }
    _API_CACHE.move_to_end(key)
    while len(_API_CACHE) > API_CACHE_MAX_ITEMS:
        _API_CACHE.popitem(last=False)


def _parse_published_date(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=None)
    except Exception:
        pass

    for fmt in [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d %B %Y",
        "%d %b %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]:
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue

    return None


def _metadata_prefilter(articles: List[Dict]) -> Tuple[List[Dict], Dict]:
    stats = {
        "input": len(articles),
        "dropped_old": 0,
        "dropped_non_news": 0,
        "dropped_credibility": 0,
        "relaxed": 0,
    }

    if not articles:
        return [], stats

    cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
    filtered: List[Dict] = []

    for article in articles:
        url = article.get("url") or article.get("source_url") or ""
        source_type = str(article.get("source_type") or "news").lower()
        if source_type != "news" and not _is_trusted_domain(url):
            stats["dropped_non_news"] += 1
            continue

        credibility = float(article.get("credibility_score", 0.0) or 0.0)
        if credibility < MIN_CREDIBILITY and not _is_trusted_domain(url):
            stats["dropped_credibility"] += 1
            continue

        published = _parse_published_date(article.get("published_date") or article.get("date"))
        if published and published < cutoff:
            stats["dropped_old"] += 1
            continue

        filtered.append(article)

    min_keep = 5 if len(articles) >= 8 else max(2, len(articles) // 2)
    if len(filtered) < min_keep:
        stats["relaxed"] = 1
        return articles, stats

    return filtered, stats


def _query_terms(claim: str, keywords: List[str] | None = None) -> List[str]:
    return extract_keywords(claim, keywords)


def _normalize_domain(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"tech", "technology"}:
        return "technology"
    if raw in {"politics", "political"}:
        return "politics"
    if raw in {"health", "medical", "medicine"}:
        return "health"
    if raw in {"science", "scientific"}:
        return "science"
    if raw in {"economy", "economic"}:
        return "economy"
    if raw in {"sports", "sport"}:
        return "sports"
    if raw in {"religion", "religious"}:
        return "religion"
    return raw or "general"


def _infer_domain(text: str) -> str:
    lowered = (text or "").lower()
    scores = {domain: 0 for domain in DOMAIN_HINTS}
    for domain, hints in DOMAIN_HINTS.items():
        for hint in hints:
            if hint in lowered:
                scores[domain] += 1

    best_domain = max(scores, key=scores.get)
    if scores[best_domain] > 0:
        return best_domain
    return "general"


def _keyword_overlap_ratio(claim: str, article: Dict, keywords: List[str] | None = None) -> float:
    terms = _query_terms(claim, keywords)
    if not terms:
        return 0.0

    haystack = (
        f"{article.get('title', '')} "
        f"{article.get('content', '')} "
        f"{article.get('full_content', '')} "
        f"{article.get('source', '')}"
    ).lower()

    matches = sum(1 for term in terms if term in haystack)
    return max(0.0, min(1.0, matches / max(1, len(terms))))


def _domain_match(required_domain: str, article: Dict, claim: str, keywords: List[str] | None = None) -> bool:
    normalized = _normalize_domain(required_domain)
    if normalized in {"", "general"}:
        return True

    text = (
        f"{article.get('title', '')} "
        f"{article.get('content', '')} "
        f"{article.get('full_content', '')} "
        f"{article.get('source', '')} "
        f"{claim} "
        f"{' '.join(keywords or [])}"
    )
    inferred = _infer_domain(text)
    return inferred == normalized


def _fallback_claim_understanding(claim: str, keywords: List[str] | None = None) -> Dict:
    text = (claim or "").strip()
    lower = text.lower()
    tokens = _query_terms(claim, keywords)
    domain = _infer_domain(text)

    entities: List[str] = []
    split_parts = re.split(r"\b(?:vs|versus|than|or)\b", text, flags=re.IGNORECASE)
    for part in split_parts:
        cleaned = re.sub(
            r"\b(?:is|are|was|were|which|what|who|when|where|why|how|older|newer|better|worse|more|less)\b",
            " ",
            part,
            flags=re.IGNORECASE,
        )
        candidate = " ".join([w for w in cleaned.split() if len(w) > 1]).strip(" ?.,")
        if candidate and candidate.lower() not in [e.lower() for e in entities]:
            entities.append(candidate)

    if not entities and tokens:
        if any(term in lower for term in ["vs", "versus", "than", "compare", "older", "newer"]):
            entities = tokens[:2]
        else:
            entities = tokens[:1]

    intent = "verify factual claim"
    if any(term in lower for term in ["older", "newer", "ancient", "age"]):
        intent = "compare age"
    elif any(term in lower for term in ["vs", "versus", "compare", "better", "worse", "than"]):
        intent = "compare claims"
    elif lower.startswith("is ") or lower.startswith("are "):
        intent = "fact verification"

    derived_keywords = list(tokens[:6])
    if intent == "compare age":
        for token in ["origin", "history", "timeline", "which is older"]:
            if token not in derived_keywords:
                derived_keywords.append(token)

    return {
        "entities": entities[:4],
        "intent": intent,
        "keywords": derived_keywords[:8],
        "domain": domain,
    }


def _normalize_understanding(data: Dict, claim: str, keywords: List[str] | None = None) -> Dict:
    fallback = _fallback_claim_understanding(claim, keywords)
    if not isinstance(data, dict):
        return fallback

    raw_entities = data.get("entities") if isinstance(data.get("entities"), list) else []
    entities: List[str] = []
    claim_lower = (claim or "").lower()
    comparison_claim = any(token in claim_lower for token in [" vs ", " versus ", " older ", " newer ", " than ", " compare "])
    for value in raw_entities:
        normalized = " ".join(str(value or "").strip().split())
        if len(normalized) < 2:
            continue
        normalized_lower = normalized.lower()
        tokens = [token for token in re.findall(r"[a-z0-9]+", normalized_lower) if token]
        if tokens and all(token in GENERIC_ENTITY_TOKENS for token in tokens):
            continue
        if len(normalized.split()) > 4:
            continue
        if any(token in normalized_lower for token in [" older ", " newer ", " than ", " versus ", " compare "]):
            continue
        if normalized.lower() in [e.lower() for e in entities]:
            continue
        entities.append(normalized)

    raw_keywords = data.get("keywords") if isinstance(data.get("keywords"), list) else []
    normalized_keywords: List[str] = []
    for value in raw_keywords:
        token = " ".join(str(value or "").strip().split()).lower()
        if len(token) < 2:
            continue
        if token in normalized_keywords:
            continue
        normalized_keywords.append(token)

    intent = " ".join(str(data.get("intent") or "").split()).strip().lower()
    if not intent or intent in {"is", "are", "short", "fact", "verify", "verification"}:
        intent = fallback["intent"]

    domain = _normalize_domain(data.get("domain"))
    if domain in {"", "general"}:
        domain = fallback.get("domain", "general")

    if not entities:
        entities = fallback["entities"]

    if comparison_claim and len(entities) < 2:
        entities = fallback["entities"][:2]

    if not normalized_keywords:
        normalized_keywords = fallback["keywords"]
    if comparison_claim and len(normalized_keywords) < 4:
        for token in fallback["keywords"]:
            if token not in normalized_keywords:
                normalized_keywords.append(token)

    return {
        "entities": entities[:4],
        "intent": intent,
        "keywords": normalized_keywords[:8],
        "domain": domain,
    }


def _understand_claim(claim: str, keywords: List[str] | None = None) -> Dict:
    fallback = _fallback_claim_understanding(claim, keywords)

    prompt = f"""Extract structured retrieval intent from this claim.

Claim: \"{claim}\"

Return ONLY JSON with this schema:
{{
  \"entities\": [\"entity1\", \"entity2\"],
  \"intent\": \"short intent\",
    \"keywords\": [\"keyword1\", \"keyword2\", \"keyword3\"],
    \"domain\": \"technology|politics|health|science|sports|economy|religion|general\"
}}

Rules:
- entities: key subjects in the claim
- intent: short retrieval objective
- keywords: retrieval terms for evidence search
- domain: best-fit category for the claim
- no markdown, no commentary
"""

    raw = call_ollama(
        prompt,
        temperature=0,
        num_predict=220,
        num_ctx=768,
        model=OLLAMA_ANALYZER,
        agent_name="RAG-ClaimPlanner",
        timeout_seconds=15,
    )
    parsed = extract_json(raw)
    understood = _normalize_understanding(parsed, claim, keywords)

    # Ensure user-provided keyword hints are represented.
    for key in keywords or []:
        normalized = " ".join(str(key or "").strip().split()).lower()
        if len(normalized) < 2:
            continue
        if normalized not in understood["keywords"]:
            understood["keywords"].append(normalized)

    understood["keywords"] = understood["keywords"][:10]
    if not understood["entities"] and fallback["entities"]:
        understood["entities"] = fallback["entities"]

    return understood


def _generate_query_variants(claim: str, understanding: Dict, max_queries: int = 5) -> List[str]:
    claim_text = " ".join((claim or "").split())
    if not claim_text:
        return []

    variants = [
        claim_text,
        f"{claim_text} fact check",
    ]

    entities = [str(e).strip() for e in (understanding.get("entities") or []) if str(e).strip()]
    keywords = [str(x).strip() for x in (understanding.get("keywords") or []) if str(x).strip()]

    if entities:
        base_entities = " ".join(entities[:3])
        variants.append(f"{base_entities} evidence")
        variants.append(f"{base_entities} official report")
        if keywords:
            variants.append(f"{base_entities} {' '.join(keywords[:2])}")

    keyword_query = " ".join(keywords[:6]).strip()
    if keyword_query:
        variants.append(keyword_query)

    # Deduplicate while preserving order.
    unique: List[str] = []
    seen = set()
    for query in variants:
        normalized = " ".join(query.lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(query)
    # Add misinformation-specific expansions when applicable
    unique = _expand_misinfo_queries(claim, unique)

    return unique[: max(1, max_queries)]


def _relevance_score(claim: str, article: Dict, keywords: List[str] | None = None) -> float:
    terms = _query_terms(claim, keywords)
    if not terms:
        return 0.5

    haystack = (
        f"{article.get('title', '')} "
        f"{article.get('content', '')} "
        f"{article.get('full_content', '')} "
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
    source_type: str = "news",
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
        "source_type": source_type,
        "full_content": "",
    }


def _extract_full_content(url: str) -> str:
    """Extract clean article text using BeautifulSoup, stripping nav garbage."""
    if not url:
        return ""

    try:
        response = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        if response.status_code >= 400:
            return ""
        html = response.text
    except Exception:
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script, style, nav, footer, aside, and cookie/dropdown elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
            tag.decompose()
        # Remove elements matching navigation garbage patterns
        for pattern in NAV_GARBAGE_PATTERNS:
            for el in soup.find_all(attrs={"class": re.compile(pattern, re.IGNORECASE)}):
                el.decompose()
            for el in soup.find_all(attrs={"id": re.compile(pattern, re.IGNORECASE)}):
                el.decompose()

        # Extract article content from <article> or <p> tags
        article_tag = soup.find("article")
        if article_tag:
            paragraphs = article_tag.find_all("p")
        else:
            paragraphs = soup.find_all("p")

        extracted: List[str] = []
        for p in paragraphs:
            text = p.get_text(separator=" ", strip=True)
            text = _clean_text(text, limit=650)
            if len(text) >= 70:
                extracted.append(text)
            if len(extracted) >= 8:
                break

        return _clean_text(" ".join(extracted), limit=1600)
    except Exception:
        LOGGER.debug("[Retriever] BeautifulSoup extraction failed for %s, using regex fallback", url[:60])
        # Regex fallback
        html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
        paragraphs_raw = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
        extracted = []
        for block in paragraphs_raw:
            plain = re.sub(r"<[^>]+>", " ", block)
            plain = _clean_text(plain, limit=650)
            if len(plain) >= 70:
                extracted.append(plain)
            if len(extracted) >= 6:
                break
        return _clean_text(" ".join(extracted), limit=1600)


def _search_serpapi(query: str, top_n: int = 10) -> Tuple[List[Dict], Dict]:
    cache_key = ("serpapi", query, int(top_n))
    cached = _get_api_cache(cache_key)
    if cached:
        meta = dict(cached.get("meta") or {})
        meta["cached"] = True
        LOGGER.info("[SEARCH] SerpAPI cache hit for query='%s'", query)
        return list(cached.get("results") or []), meta

    meta = {"ok": False, "status_code": None, "error": None, "count": 0, "api_calls": []}
    if not SERPAPI_KEY:
        meta["error"] = "SERPAPI_KEY missing"
        LOGGER.error("[SEARCH] SerpAPI key missing - cannot proceed")
        return [], meta

    LOGGER.info("[SEARCH] Query sent to SerpAPI: '%s'", query)

    trusted_sites_hint = " OR ".join(
        [
            "site:reuters.com",
            "site:apnews.com",
            "site:bbc.com",
            "site:thehindu.com",
            "site:indianexpress.com",
            "site:bloomberg.com",
            "site:theguardian.com",
        ]
    )

    candidate_queries = [query, f"{query} ({trusted_sites_hint})"]
    seen_urls = set()
    collected: List[Dict] = []

    for run_query in candidate_queries:
        for mode in ["web", "nws"]:
            params = {
                "engine": "google",
                "q": run_query,
                "api_key": SERPAPI_KEY,
                "num": top_n,
                "hl": "en",
                "gl": "in",
            }
            if mode == "nws":
                params["tbm"] = "nws"
            source_type = "news" if mode == "nws" else "web"
            evidence_source = "serpapi_news" if mode == "nws" else "serpapi_web"

            LOGGER.info("[SEARCH] SerpAPI request: query='%s' mode=%s", run_query, mode)
            api_call_meta = {"query": run_query, "mode": mode, "status": None, "raw_count": 0, "parsed_count": 0}
            
            try:
                response = _retry_request("https://serpapi.com/search.json", params=params, timeout=15)
                meta["status_code"] = response.status_code
                api_call_meta["status"] = response.status_code

                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {_clean_text(response.text, 240)}"
                    meta["error"] = error_msg
                    LOGGER.error("[SEARCH] SerpAPI error: %s", error_msg)
                    api_call_meta["error"] = error_msg
                    meta["api_calls"].append(api_call_meta)
                    continue

                payload = response.json()
                items = (payload.get("news_results") or payload.get("organic_results") or [])[:top_n]
                api_call_meta["raw_count"] = len(items)
                LOGGER.info("[SEARCH] Number of results returned by SerpAPI: %s", len(items))
                
                parsed_urls = 0
                for item in items:
                    link = item.get("link", "")
                    if not link or _is_low_quality(link):
                        continue

                    key = link.strip().lower()
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)
                    parsed_urls += 1

                    article = _standard_article(
                        title=item.get("title", ""),
                        source=item.get("source", ""),
                        content=item.get("snippet", ""),
                        url=link,
                        published_date=item.get("date", ""),
                        evidence_source=evidence_source,
                        source_type=source_type,
                    )
                    article["relevance_score"] = _relevance_score(run_query, article)
                    collected.append(article)
                
                api_call_meta["parsed_count"] = parsed_urls
                LOGGER.info("[SEARCH] Parsed URLs count (SerpAPI): %s", parsed_urls)
                meta["api_calls"].append(api_call_meta)
                
            except Exception as exc:
                error_msg = str(exc)
                meta["error"] = error_msg
                api_call_meta["error"] = error_msg
                LOGGER.error("[SEARCH] SerpAPI exception: %s", error_msg)
                meta["api_calls"].append(api_call_meta)

            if len(collected) >= top_n:
                break

        if len(collected) >= top_n:
            break

    output = list(collected)
    for article in output:
        article["relevance_score"] = _relevance_score(query, article)
        article["trust_bonus"] = 0.08 if _is_trusted_domain(article.get("url", "")) else 0.0
    output.sort(
        key=lambda article: (
            float(article.get("relevance_score", 0.0)) + float(article.get("trust_bonus", 0.0)),
            float(article.get("credibility_score", 0.5) or 0.5),
        ),
        reverse=True,
    )

    meta["ok"] = bool(output)
    meta["count"] = len(output[:top_n])
    meta["cached"] = False
    LOGGER.info("[SEARCH] SerpAPI final result: %s articles returned", meta["count"])
    _set_api_cache(cache_key, {"results": output[:top_n], "meta": meta})
    return output[:top_n], meta


def _search_newsapi(query: str, top_n: int = 10) -> Tuple[List[Dict], Dict]:
    cache_key = ("newsapi", query, int(top_n))
    cached = _get_api_cache(cache_key)
    if cached:
        meta = dict(cached.get("meta") or {})
        meta["cached"] = True
        LOGGER.info("[SEARCH] NewsAPI cache hit for query='%s'", query)
        return list(cached.get("results") or []), meta

    meta = {"ok": False, "status_code": None, "error": None, "count": 0, "api_calls": []}
    if not NEWSAPI_KEY:
        meta["error"] = "NEWSAPI_KEY missing"
        LOGGER.error("[SEARCH] NewsAPI key missing - cannot proceed")
        return [], meta

    LOGGER.info("[SEARCH] Query sent to NewsAPI: '%s'", query)

    for use_domain_filter in [True, False]:
        params = {
            "q": query,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": top_n,
            "apiKey": NEWSAPI_KEY,
        }
        if use_domain_filter:
            params["domains"] = NEWSAPI_TRUSTED_DOMAINS

        filter_mode = "trusted_domains" if use_domain_filter else "any_domain"
        LOGGER.info("[SEARCH] NewsAPI request: query='%s' filter_mode=%s", query, filter_mode)
        api_call_meta = {"query": query, "filter_mode": filter_mode, "status": None, "raw_count": 0, "parsed_count": 0}
        
        try:
            response = _retry_request("https://newsapi.org/v2/everything", params=params, timeout=15)
            meta["status_code"] = response.status_code
            api_call_meta["status"] = response.status_code
            
            LOGGER.info("[SEARCH] NewsAPI response status: %s", response.status_code)

            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {_clean_text(response.text, 240)}"
                meta["error"] = error_msg
                LOGGER.error("[SEARCH] NewsAPI error: %s", error_msg)
                api_call_meta["error"] = error_msg
                meta["api_calls"].append(api_call_meta)
                continue

            payload = response.json()
            if payload.get("status") != "ok":
                error_msg = payload.get("message", "Unknown NewsAPI error")
                meta["error"] = error_msg
                LOGGER.error("[SEARCH] NewsAPI status not ok: %s", error_msg)
                api_call_meta["error"] = error_msg
                meta["api_calls"].append(api_call_meta)
                continue

            articles: List[Dict] = []
            items = payload.get("articles", [])[:top_n]
            api_call_meta["raw_count"] = len(items)
            LOGGER.info("[SEARCH] Number of results returned by NewsAPI: %s", len(items))
            
            parsed_urls = 0
            for item in items:
                link = item.get("url", "")
                if not link or _is_low_quality(link):
                    continue

                parsed_urls += 1
                content = item.get("description") or item.get("content") or ""
                source_name = (item.get("source") or {}).get("name", "")
                article = _standard_article(
                    title=item.get("title", ""),
                    source=source_name,
                    content=content,
                    url=link,
                    published_date=item.get("publishedAt", ""),
                    evidence_source="newsapi",
                    source_type="news",
                )
                article["relevance_score"] = _relevance_score(query, article)
                articles.append(article)

            api_call_meta["parsed_count"] = parsed_urls
            LOGGER.info("[SEARCH] Parsed URLs count (NewsAPI): %s", parsed_urls)

            trusted = [article for article in articles if _is_trusted_domain(article.get("url", ""))]
            output = trusted if trusted else articles
            if output:
                meta["ok"] = True
                meta["count"] = len(output[:top_n])
                meta["cached"] = False
                api_call_meta["success"] = True
                meta["api_calls"].append(api_call_meta)
                LOGGER.info("[SEARCH] NewsAPI final result: %s articles returned", meta["count"])
                _set_api_cache(cache_key, {"results": output[:top_n], "meta": meta})
                return output[:top_n], meta
            
            meta["api_calls"].append(api_call_meta)
        except Exception as exc:
            error_msg = str(exc)
            meta["error"] = error_msg
            api_call_meta["error"] = error_msg
            LOGGER.error("[SEARCH] NewsAPI exception: %s", error_msg)
            meta["api_calls"].append(api_call_meta)

    if meta.get("error"):
        LOGGER.error("[SEARCH] NewsAPI final failure: %s", meta["error"])
    meta["cached"] = False
    _set_api_cache(cache_key, {"results": [], "meta": meta})
    return [], meta


def serp_search(query: str, top_n: int = 10) -> List[Dict]:
    results, meta = _search_serpapi(query, top_n=top_n)
    LOGGER.info("[Retriever][serp_search] Generated queries: %s", [query])
    LOGGER.info("[Retriever][serp_search] Raw API sample: %s", results[:2])
    LOGGER.info("[Retriever][serp_search] meta=%s count=%s", meta, len(results))
    return results


def news_search(query: str, top_n: int = 10) -> List[Dict]:
    results, meta = _search_newsapi(query, top_n=top_n)
    LOGGER.info("[Retriever][news_search] Generated queries: %s", [query])
    LOGGER.info("[Retriever][news_search] Raw API sample: %s", results[:2])
    LOGGER.info("[Retriever][news_search] meta=%s count=%s", meta, len(results))
    return results


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


def _top_raw_fallback(claim: str, articles: List[Dict], limit: int = 5) -> List[Dict]:
    if not articles:
        return []

    claim_terms = _query_terms(claim)

    cleaned: List[Dict] = []
    for row in articles:
        url = row.get("url") or row.get("source_url") or ""
        if _is_low_quality(url):
            continue

        text = f"{row.get('title', '')} {row.get('content', '')} {row.get('full_content', '')}".lower()
        if any(token in text for token in OFFTOPIC_TERMS):
            claim_lower = (claim or "").lower()
            if not any(token in claim_lower for token in ["movie", "celebrity", "music", "box office"]):
                continue

        if claim_terms:
            term_hits = sum(1 for term in claim_terms if term in text)
            if term_hits == 0:
                continue

        cleaned.append(row)

    source_rows = cleaned if cleaned else list(articles)

    ordered = sorted(
        source_rows,
        key=lambda row: (
            float(row.get("relevance_score", 0.0) or 0.0),
            float(row.get("credibility_score", 0.5) or 0.5),
        ),
        reverse=True,
    )

    fallback_rows: List[Dict] = []
    for row in ordered[: max(1, limit)]:
        item = dict(row)
        base_sim = float(item.get("similarity_score", item.get("relevance_score", 0.0)) or 0.0)
        cred = float(item.get("credibility_score", 0.5) or 0.5)
        item["similarity_score"] = round(base_sim, 4)
        item["rag_score"] = round((0.65 * base_sim) + (0.35 * cred), 4)
        fallback_rows.append(item)

    return fallback_rows


def _entity_present(text: str, entity: str) -> bool:
    normalized = (text or "").lower()
    tokens = [token for token in re.findall(r"[a-z0-9]+", (entity or "").lower()) if len(token) > 1]
    if not tokens:
        return False
    return all(re.search(rf"\\b{re.escape(token)}\\b", normalized) for token in tokens)


def _contains_required_entities(text: str, entities: List[str], require_both_entities: bool = False) -> bool:
    required = [e.strip() for e in entities if e and len(e.strip()) > 1][:2]
    if len(required) < 2:
        return True

    if require_both_entities:
        return all(_entity_present(text, entity) for entity in required)

    return any(_entity_present(text, entity) for entity in required)


def _is_clickbait(article: Dict) -> bool:
    target = f"{article.get('title', '')} {article.get('url', '')}".lower()
    return any(token in target for token in CLICKBAIT_TERMS)


def _is_offtopic(article: Dict, understanding: Dict, claim: str) -> bool:
    text = (
        f"{article.get('title', '')} "
        f"{article.get('content', '')} "
        f"{article.get('full_content', '')}"
    ).lower()

    if any(token in text for token in OFFTOPIC_TERMS):
        claim_lower = (claim or "").lower()
        if not any(token in claim_lower for token in ["movie", "celebrity", "actor", "music"]):
            return True

    keywords = [str(token).lower() for token in (understanding.get("keywords") or []) if str(token).strip()]
    entities = [str(token).lower() for token in (understanding.get("entities") or []) if str(token).strip()]
    important = []
    for token in entities + keywords:
        norm = token.strip()
        if len(norm) < 3:
            continue
        if norm not in important:
            important.append(norm)

    if not important:
        return False

    # Relaxed anti-overfiltering: drop only when zero claim signal is present.
    match_count = sum(1 for token in important if token in text)
    return match_count == 0


def _chunk_text(text: str, words_per_chunk: int = 120, max_chunks: int = 6) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []

    max_chars = max(420, words_per_chunk * 6)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
    if not paragraphs:
        paragraphs = [re.sub(r"\s+", " ", raw).strip()]

    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        if not sentences:
            sentences = [paragraph]

        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) > max_chars and current:
                if len(current) >= 80:
                    chunks.append(current.strip())
                current = sentence
            else:
                current = candidate

            if len(chunks) >= max_chunks:
                return [c for c in chunks if len(c) >= 60][:max_chunks]

        if len(current) >= max_chars:
            chunks.append(current.strip())
            current = ""
        if len(chunks) >= max_chunks:
            break

    if current and len(chunks) < max_chunks:
        chunks.append(current.strip())

    return [c for c in chunks if len(c) >= 60][:max_chunks]


def _normalize_vectors(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _compute_article_similarity(
    claim: str,
    articles: List[Dict],
) -> Tuple[List[Dict], np.ndarray, float]:
    if not articles:
        return [], np.zeros((0, 1), dtype=np.float32)

    emb_start = time.perf_counter()
    claim_vector = embed_query(claim).astype(np.float32)
    claim_matrix = _normalize_vectors(claim_vector.reshape(1, -1))
    claim_norm = claim_matrix[0]

    chunk_texts: List[str] = []
    chunk_to_article: List[int] = []

    for idx, article in enumerate(articles):
        combined = " ".join(
            [
                article.get("title", ""),
                article.get("content", ""),
                article.get("full_content", ""),
            ]
        ).strip()
        chunks = _chunk_text(combined)
        if not chunks:
            chunks = [combined[:800]] if combined else []

        for chunk in chunks:
            if not chunk:
                continue
            chunk_texts.append(chunk)
            chunk_to_article.append(idx)

    if not chunk_texts:
        return [], claim_vector.reshape(1, -1)

    chunk_vectors = embed_texts(chunk_texts).astype(np.float32)
    emb_time = time.perf_counter() - emb_start
    chunk_vectors = _normalize_vectors(chunk_vectors)

    best_similarity = {i: -1.0 for i in range(len(articles))}
    best_vector = {i: None for i in range(len(articles))}

    for vec_idx, article_idx in enumerate(chunk_to_article):
        similarity = float(np.dot(chunk_vectors[vec_idx], claim_norm))
        if similarity > best_similarity[article_idx]:
            best_similarity[article_idx] = similarity
            best_vector[article_idx] = chunk_vectors[vec_idx]

    scored: List[Dict] = []
    vectors: List[np.ndarray] = []
    for idx, article in enumerate(articles):
        similarity = float(best_similarity.get(idx, -1.0))
        vector = best_vector.get(idx)
        if vector is None:
            continue

        enriched = dict(article)
        enriched["similarity_score"] = round(similarity, 4)
        scored.append(enriched)
        vectors.append(vector)

    if not vectors:
        return [], claim_vector.reshape(1, -1)

    return scored, claim_vector.reshape(1, -1), emb_time


def _apply_rule_filters(claim: str, understanding: Dict, articles: List[Dict]) -> Tuple[List[Dict], Dict]:
    filtered: List[Dict] = []
    stats = {
        "input": len(articles),
        "dropped_low_quality": 0,
        "dropped_credibility": 0,
        "dropped_clickbait": 0,
        "dropped_entities": 0,
        "dropped_offtopic": 0,
        "entity_relaxed": 0,
    }

    entities = understanding.get("entities") or []
    intent = str(understanding.get("intent") or "").lower()
    require_both_entities = len(entities) >= 2 and any(
        cue in intent for cue in ["compare", "versus", "older", "newer", "difference"]
    )
    for article in articles:
        url = article.get("url", "")
        text_blob = (
            f"{article.get('title', '')} "
            f"{article.get('content', '')} "
            f"{article.get('full_content', '')}"
        )

        if _is_low_quality(url):
            stats["dropped_low_quality"] += 1
            continue

        if float(article.get("credibility_score", 0.0) or 0.0) < MIN_CREDIBILITY and not _is_trusted_domain(url):
            stats["dropped_credibility"] += 1
            continue

        if _is_clickbait(article):
            stats["dropped_clickbait"] += 1
            continue

        if not _contains_required_entities(text_blob, entities, require_both_entities=require_both_entities):
            stats["dropped_entities"] += 1
            continue

        if _is_offtopic(article, understanding, claim):
            stats["dropped_offtopic"] += 1
            continue

        filtered.append(article)

    if not filtered and require_both_entities:
        LOGGER.warning("[Retriever] Both-entity filter removed all docs; relaxing to any-entity mode")
        stats["entity_relaxed"] = 1
        for article in articles:
            url = article.get("url", "")
            text_blob = (
                f"{article.get('title', '')} "
                f"{article.get('content', '')} "
                f"{article.get('full_content', '')}"
            )

            if _is_low_quality(url):
                continue
            if float(article.get("credibility_score", 0.0) or 0.0) < MIN_CREDIBILITY and not _is_trusted_domain(url):
                continue
            if _is_clickbait(article):
                continue
            if _is_offtopic(article, understanding, claim):
                continue
            if not _contains_required_entities(text_blob, entities, require_both_entities=False):
                continue

            filtered.append(article)

    return filtered, stats


def _enrich_full_content(articles: List[Dict], max_fetch: int = 10) -> List[Dict]:
    enriched: List[Dict] = []
    fetched = 0
    for article in articles:
        row = dict(article)
        raw_content = str(row.get("content", "") or "").strip()
        if fetched < max_fetch and len(raw_content) < 160:
            full = _extract_full_content(row.get("url", ""))
            if full:
                row["full_content"] = full
                row["content"] = _clean_text(full, 420)
                fetched += 1
        enriched.append(row)
    return enriched


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
            source_type="news",
        )
        article["relevance_score"] = _relevance_score(claim, article, keywords)
        candidate_articles.append(article)

    candidate_articles.sort(key=lambda a: a.get("relevance_score", 0.0), reverse=True)
    LOGGER.warning("[Retriever] Using local fallback dataset with %s candidates", len(candidate_articles))
    return candidate_articles


def retrieve_evidence_minimal(
    claim: str,
    keywords: List[str] | None = None,
    domain: str = "general",
    top_k: int = 5,
    max_retries: int = 1,
) -> Tuple[List[Dict], Dict]:
    """Minimal recovery retriever: external APIs, light filtering, no embeddings/FAISS."""
    retrieval_start = time.perf_counter()
    claim = (claim or "").strip()
    if not claim:
        return [], {
            "success": False,
            "stage": "retrieval",
            "error": "Empty claim",
            "trace": "",
            "retrieved_count": 0,
            "retrieval_time": 0.0,
        }

    LOGGER.info("[PIPELINE] Retrieval started")
    LOGGER.info(
        "[Retriever] Minimal retrieval claim='%s' domain=%s keywords=%s",
        claim,
        domain,
        keywords or [],
    )

    try:
        top_n = max(10, int(top_k or 5))
        base_queries = [claim]
        if "fact check" not in claim.lower():
            base_queries.append(f"{claim} fact check")
        terms = extract_keywords(claim, keywords, limit=6)
        if terms:
            base_queries.append(" ".join(terms))

        query_variants: List[str] = []
        seen_queries = set()
        for query in base_queries:
            normalized = re.sub(r"\s+", " ", query).strip()
            key = normalized.lower()
            if normalized and key not in seen_queries:
                seen_queries.add(key)
                query_variants.append(normalized)

        combined_articles: List[Dict] = []
        api_runs = []
        attempts = max(1, int(max_retries or 0) + 1)
        for attempt in range(attempts):
            attempt_meta = {"attempt": attempt + 1, "queries": []}
            for run_query in query_variants[:3]:
                LOGGER.info("[Retriever] Minimal search attempt=%s query='%s'", attempt + 1, run_query)
                serp_articles, serp_meta = _search_serpapi(run_query, top_n=top_n)
                news_articles, news_meta = _search_newsapi(run_query, top_n=top_n)
                parsed_for_query = _dedupe(serp_articles + news_articles)
                combined_articles.extend(parsed_for_query)
                attempt_meta["queries"].append(
                    {
                        "query": run_query,
                        "serpapi": serp_meta,
                        "newsapi": news_meta,
                        "raw_count": len(serp_articles) + len(news_articles),
                        "parsed_count": len(parsed_for_query),
                    }
                )
            api_runs.append(attempt_meta)
            combined_articles = _dedupe(combined_articles)
            if combined_articles:
                break

        raw_count = len(combined_articles)
        if not combined_articles:
            combined_articles = _load_local_fallback(claim, keywords)

        parsed_articles = []
        for article in combined_articles:
            row = dict(article)
            row["relevance_score"] = _relevance_score(claim, row, keywords)
            row["keyword_score"] = _keyword_overlap_ratio(claim, row, keywords)
            try:
                credibility = float(row.get("credibility_score", score_source(row.get("url", ""))))
            except Exception:
                credibility = 0.5
            row["credibility_score"] = max(0.0, min(1.0, credibility))
            row["rag_score"] = round(
                (0.55 * float(row.get("relevance_score", 0.0)))
                + (0.25 * float(row.get("keyword_score", 0.0)))
                + (0.20 * float(row.get("credibility_score", 0.5))),
                4,
            )
            parsed_articles.append(row)

        filtered = [
            row
            for row in parsed_articles
            if row.get("relevance_score", 0.0) >= 0.05 or row.get("keyword_score", 0.0) >= 0.10
        ]
        if len(filtered) < min(5, top_n):
            filtered = parsed_articles

        filtered.sort(key=lambda row: row.get("rag_score", 0.0), reverse=True)
        final_ranked = filtered[: max(5, int(top_k or 5))]

        LOGGER.info("[PIPELINE] Retrieval completed")
        LOGGER.info(
            "[Retriever] Minimal retrieval counts raw=%s parsed=%s filtered=%s final=%s",
            raw_count,
            len(parsed_articles),
            len(filtered),
            len(final_ranked),
        )
        for index, item in enumerate(final_ranked[:5], start=1):
            LOGGER.info(
                "[Retriever] Minimal Top-%s score=%.4f source=%s title=%s",
                index,
                float(item.get("rag_score", 0.0)),
                item.get("source", "Unknown"),
                item.get("title", "")[:90],
            )

        return final_ranked, {
            "success": True,
            "mode": "minimal",
            "claim_understanding": {"domain": domain, "keywords": terms},
            "queries": query_variants,
            "api_runs": api_runs,
            "raw_count": raw_count,
            "parsed_count": len(parsed_articles),
            "filtered_count": len(filtered),
            "retrieved_count": len(final_ranked),
            "top_k": [
                {
                    "title": row.get("title", "")[:120],
                    "source": row.get("source", ""),
                    "url": row.get("url", ""),
                    "rag_score": round(float(row.get("rag_score", 0.0)), 4),
                }
                for row in final_ranked
            ],
            "fallback_used": raw_count == 0 and bool(final_ranked),
            "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
            "embedding_time": 0.0,
        }
    except Exception as exc:
        trace = traceback.format_exc()
        LOGGER.exception("[Retriever] FULL ERROR TRACE")
        return [], {
            "success": False,
            "stage": "retrieval",
            "error": str(exc),
            "trace": trace,
            "retrieved_count": 0,
            "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
            "embedding_time": 0.0,
        }


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
    if not USE_ADVANCED_RAG:
        return retrieve_evidence_minimal(
            claim=claim,
            keywords=keywords,
            domain=domain,
            top_k=top_k,
            max_retries=max_retries,
        )

    claim = (claim or "").strip()
    if not claim:
        return [], {
            "error": "Empty claim",
            "error_flag": True,
            "fallback_used": False,
            "retrieval_time": 0.0,
            "embedding_time": 0.0,
        }

    desired_top_k = max(6, min(15, int(top_k)))

    retrieval_start = time.perf_counter()
    total_embedding_time = 0.0

    understanding = _understand_claim(claim, keywords)
    query_variants = _generate_query_variants(claim, understanding, max_queries=5)

    LOGGER.info(
        "[Retriever] Starting retrieval claim='%s' domain=%s understanding=%s",
        claim,
        domain,
        understanding,
    )
    LOGGER.info("[Retriever] Generated queries: %s", query_variants)

    combined_articles: List[Dict] = []
    api_runs = []

    attempts = max(1, max_retries + 1)
    for attempt in range(attempts):
        attempt_queries = query_variants if attempt == 0 else [claim]
        collected_this_attempt: List[Dict] = []
        attempt_meta = {"attempt": attempt + 1, "queries": []}

        for run_query in attempt_queries:
            LOGGER.info("[Retriever] Search attempt=%s query='%s'", attempt + 1, run_query)
            serp_articles, serp_meta = _search_serpapi(run_query, top_n=10)
            news_articles, news_meta = _search_newsapi(run_query, top_n=10)
            merged_for_query = _dedupe(serp_articles + news_articles)
            LOGGER.info(
                "[Retriever] Raw API results query='%s' serp=%s news=%s merged=%s",
                run_query,
                len(serp_articles),
                len(news_articles),
                len(merged_for_query),
            )
            collected_this_attempt.extend(merged_for_query)
            attempt_meta["queries"].append(
                {
                    "query": run_query,
                    "serpapi": serp_meta,
                    "newsapi": news_meta,
                    "merged_count": len(merged_for_query),
                }
            )

        api_runs.append(attempt_meta)
        combined_articles = _dedupe(collected_this_attempt)
        LOGGER.info("[Retriever] Attempt %s combined deduped count=%s", attempt + 1, len(combined_articles))

        if combined_articles:
            break

    fallback_used = False
    if not combined_articles:
        combined_articles = _load_local_fallback(claim, understanding.get("keywords"))
        fallback_used = True

    LOGGER.info("[Retriever] Raw results count: %s", len(combined_articles))

    combined_articles, prefilter_stats = _metadata_prefilter(combined_articles)
    LOGGER.info(
        "[Retriever] Metadata prefilter count=%s stats=%s",
        len(combined_articles),
        prefilter_stats,
    )

    combined_articles = _enrich_full_content(combined_articles, max_fetch=10)

    for article in combined_articles:
        article["relevance_score"] = _relevance_score(claim, article, understanding.get("keywords"))

    prefiltered, rule_stats = _apply_rule_filters(claim, understanding, combined_articles)
    LOGGER.info("[Retriever] Filtered candidate count: %s", len(prefiltered))

    if not prefiltered:
        return [], {
            "claim_understanding": understanding,
            "queries": query_variants,
            "api_runs": api_runs,
            "fallback_used": fallback_used,
            "prefilter_stats": prefilter_stats,
            "error": "INSUFFICIENT_DATA",
            "error_flag": True,
            "insufficient_data": True,
            "filter_stats": {
                **rule_stats,
                "dropped_similarity": 0,
                "dropped_keyword": 0,
                "dropped_domain": 0,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "keyword_overlap_threshold": KEYWORD_OVERLAP_THRESHOLD,
            },
            "retrieved_count": 0,
            "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
            "embedding_time": round(total_embedding_time, 4),
        }

    try:
        scored_articles, claim_vector, emb_time_1 = _compute_article_similarity(claim, prefiltered)
        total_embedding_time += float(emb_time_1 or 0.0)
    except Exception:
        LOGGER.exception("[Retriever] Embedding similarity failed")
        return [], {
            "claim_understanding": understanding,
            "queries": query_variants,
            "api_runs": api_runs,
            "fallback_used": True,
            "prefilter_stats": prefilter_stats,
            "error": "Embedding generation failed",
            "error_flag": True,
            "retrieved_count": 0,
            "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
            "embedding_time": round(total_embedding_time, 4),
        }

    semantic_filtered: List[Dict] = []
    dropped_similarity = 0
    dropped_keyword = 0
    dropped_domain = 0
    keyword_terms = understanding.get("keywords") or _query_terms(claim, keywords)
    required_domain = _normalize_domain(domain)
    if required_domain in {"", "general"}:
        required_domain = _normalize_domain(understanding.get("domain"))

    # Hybrid relevance scoring: combine embedding similarity with keyword overlap
    scored_for_ranking: List[Dict] = []
    
    for article in scored_articles:
        similarity = float(article.get("similarity_score", 0.0))
        keyword_score = _keyword_overlap_ratio(claim, article, keyword_terms)
        
        # Hybrid score: weighted combination of embedding similarity and keyword match
        hybrid_score = (HYBRID_SCORE_WEIGHT_EMBEDDING * similarity + 
                       HYBRID_SCORE_WEIGHT_KEYWORD * keyword_score)
        
        article["keyword_score"] = round(keyword_score, 4)
        article["hybrid_score"] = round(hybrid_score, 4)
        
        # Keep articles if hybrid score is acceptable OR if either component is strong
        if hybrid_score >= 0.25 or similarity >= 0.35 or keyword_score >= 0.25:
            if _domain_match(required_domain, article, claim, keyword_terms):
                enriched = dict(article)
                enriched["domain_match"] = True
                scored_for_ranking.append(enriched)
        else:
            if similarity < 0.40:
                dropped_similarity += 1
            if keyword_score < 0.30:
                dropped_keyword += 1
            if not _domain_match(required_domain, article, claim, keyword_terms):
                dropped_domain += 1

    # Sort by hybrid score to get best candidates first
    semantic_filtered = sorted(scored_for_ranking, 
                              key=lambda x: x.get("hybrid_score", 0.0), 
                              reverse=True)

    if not semantic_filtered:
        LOGGER.warning(
            "[Retriever] Hybrid relevance filters removed all docs (hybrid>=0.25 or sim>=0.35 or kw>=0.25, domain=%s)",
            required_domain,
        )
        return [], {
            "claim_understanding": understanding,
            "queries": query_variants,
            "api_runs": api_runs,
            "fallback_used": fallback_used,
            "prefilter_stats": prefilter_stats,
            "error": "INSUFFICIENT_DATA",
            "error_flag": True,
            "insufficient_data": True,
            "filter_stats": {
                **rule_stats,
                "dropped_similarity": dropped_similarity,
                "dropped_keyword": dropped_keyword,
                "dropped_domain": dropped_domain,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "keyword_overlap_threshold": KEYWORD_OVERLAP_THRESHOLD,
                "required_domain": required_domain,
                "hybrid_score_used": True,
            },
            "retrieved_count": 0,
            "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
            "embedding_time": round(total_embedding_time, 4),
        }

    try:
        texts = [f"{a.get('title', '')} {a.get('content', '')} {a.get('full_content', '')}" for a in semantic_filtered]
        emb_start_2 = time.perf_counter()
        vectors = embed_texts(texts).astype(np.float32)
        emb_time_2 = time.perf_counter() - emb_start_2
        total_embedding_time += float(emb_time_2 or 0.0)
        store = FaissStore(dimension=vectors.shape[1])
        store.add_documents(vectors, semantic_filtered)
        faiss_hits = store.search(claim_vector, k=min(len(semantic_filtered), max(10, desired_top_k)))
    except Exception:
        LOGGER.exception("[Retriever] Secondary embedding/ranking failed")
        faiss_hits = []

    ranked: List[Dict] = []
    if faiss_hits:
        for hit in faiss_hits:
            article = dict(hit["document"])
            faiss_similarity = float(hit["similarity"])
            semantic_similarity = float(article.get("similarity_score", 0.0))
            article["similarity_score"] = round(max(faiss_similarity, semantic_similarity), 4)
            ranked.append(article)
    else:
        ranked = list(semantic_filtered)

    final_ranked, ranking_comparison = rank_articles(claim, ranked, keyword_terms, top_k=desired_top_k)

    if not final_ranked:
        return [], {
            "claim_understanding": understanding,
            "queries": query_variants,
            "api_runs": api_runs,
            "fallback_used": fallback_used,
            "prefilter_stats": prefilter_stats,
            "filter_stats": {
                **rule_stats,
                "dropped_similarity": dropped_similarity,
                "dropped_keyword": dropped_keyword,
                "dropped_domain": dropped_domain,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "keyword_overlap_threshold": KEYWORD_OVERLAP_THRESHOLD,
                "required_domain": required_domain,
            },
            "retrieved_count": 0,
            "error": "INSUFFICIENT_DATA",
            "error_flag": True,
            "insufficient_data": True,
            "ranking_comparison": ranking_comparison,
            "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
            "embedding_time": round(total_embedding_time, 4),
        }

    top_log = [
        {
            "title": item.get("title", "")[:120],
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "similarity": round(float(item.get("similarity_score", 0.0)), 4),
            "credibility": round(float(item.get("credibility_score", 0.5)), 3),
            "rag_score": round(float(item.get("rag_score", 0.0)), 4),
        }
        for item in final_ranked
    ]

    LOGGER.info("[Retriever] Retrieved sources count=%s", len(final_ranked))
    for i, item in enumerate(final_ranked, start=1):
        LOGGER.info(
            "[Retriever] Top-%s sim=%.4f rag=%.4f source=%s title=%s",
            i,
            float(item.get("similarity_score", 0.0)),
            float(item.get("rag_score", 0.0)),
            item.get("source", "Unknown"),
            item.get("title", "")[:90],
        )

    return final_ranked, {
        "claim_understanding": understanding,
        "queries": query_variants,
        "api_runs": api_runs,
        "fallback_used": fallback_used,
        "prefilter_stats": prefilter_stats,
        "filter_stats": {
            **rule_stats,
            "dropped_similarity": dropped_similarity,
            "dropped_keyword": dropped_keyword,
            "dropped_domain": dropped_domain,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "keyword_overlap_threshold": KEYWORD_OVERLAP_THRESHOLD,
            "required_domain": required_domain,
        },
        "retrieved_count": len(final_ranked),
        "top_k": top_log,
        "ranking_comparison": ranking_comparison,
        "retrieval_time": round(time.perf_counter() - retrieval_start, 4),
        "embedding_time": round(total_embedding_time, 4),
    }
