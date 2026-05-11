"""
Dynamic credibility scoring for VeritasAI evidence sources.

The public function returns an integer 0-100 score. Existing backend callers
that expect 0-1 scores should divide by 100 or use credibility.score_source().
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse


HIGH_TRUST_DOMAINS = {
    "reuters.com": 95,
    "apnews.com": 95,
    "ap.org": 95,
    "bbc.com": 92,
    "bbc.co.uk": 92,
    "who.int": 96,
    "cdc.gov": 96,
    "nih.gov": 96,
    "nature.com": 95,
    "science.org": 95,
    "un.org": 93,
    "worldbank.org": 93,
    "gov.in": 96,
    "pib.gov.in": 96,
    "isro.gov.in": 96,
    "nta.ac.in": 94,
    "olympics.com": 92,
}

NEWS_DOMAINS = {
    "theguardian.com": 88,
    "nytimes.com": 88,
    "washingtonpost.com": 88,
    "bloomberg.com": 90,
    "economist.com": 90,
    "ft.com": 89,
    "thehindu.com": 84,
    "indianexpress.com": 82,
    "ndtv.com": 80,
    "hindustantimes.com": 78,
    "timesofindia.com": 76,
    "business-standard.com": 84,
    "economictimes.indiatimes.com": 82,
    "livemint.com": 80,
    "moneycontrol.com": 80,
    "aljazeera.com": 82,
    "snopes.com": 88,
    "factcheck.org": 90,
    "politifact.com": 86,
    "altnews.in": 86,
    "boomlive.in": 85,
}

LOW_TRUST_DOMAINS = {
    "medium.com": 55,
    "substack.com": 58,
    "blogspot.com": 35,
    "wordpress.com": 42,
    "quora.com": 35,
    "reddit.com": 40,
    "facebook.com": 30,
    "instagram.com": 30,
    "tiktok.com": 30,
    "youtube.com": 45,
}


def _domain_from_source(source: Any) -> str:
    if isinstance(source, str):
        value = source
    elif isinstance(source, dict):
        value = (
            source.get("url")
            or source.get("source_url")
            or source.get("link")
            or source.get("domain")
            or source.get("source")
            or ""
        )
    else:
        value = ""

    value = str(value or "").strip()
    if not value:
        return ""
    if "://" not in value and "." in value and "/" not in value:
        return value.lower().replace("www.", "")

    try:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return value.lower().replace("www.", "")


def _base_domain_score(domain: str) -> int:
    if not domain:
        return 50
    if domain in HIGH_TRUST_DOMAINS:
        return HIGH_TRUST_DOMAINS[domain]
    if domain in NEWS_DOMAINS:
        return NEWS_DOMAINS[domain]
    if domain in LOW_TRUST_DOMAINS:
        return LOW_TRUST_DOMAINS[domain]
    if domain.endswith(".gov.in"):
        return 96
    if domain.endswith(".gov") or ".gov." in domain:
        return 94
    if domain.endswith(".edu") or ".edu." in domain:
        return 88
    if domain.endswith(".ac.in") or domain.endswith(".edu.in"):
        return 88
    if domain.endswith(".org"):
        return 72
    if any(token in domain for token in ["blog", "rumor", "viral", "gossip"]):
        return 38
    return 60


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        candidates = [
            text,
            text.replace("Z", "+00:00"),
        ]
        dt = None
        for candidate in candidates:
            try:
                dt = datetime.fromisoformat(candidate)
                break
            except Exception:
                pass
        if dt is None:
            try:
                dt = parsedate_to_datetime(text)
            except Exception:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _freshness_bonus(source: Dict[str, Any]) -> int:
    dt = _parse_date(
        source.get("published_date")
        or source.get("date")
        or source.get("publishedAt")
        or source.get("timestamp")
    )
    if dt is None:
        return 0
    age_days = max(0, (datetime.now(timezone.utc) - dt).days)
    if age_days <= 30:
        return 6
    if age_days <= 180:
        return 3
    if age_days <= 730:
        return 0
    return -4


def _specificity_bonus(source: Dict[str, Any]) -> int:
    text = " ".join(
        str(source.get(key) or "")
        for key in ("title", "content", "snippet", "description", "summary")
    )
    if not text.strip():
        return 0
    score = 0
    if len(text) >= 140:
        score += 4
    if re.search(r"\b\d{4}\b|\b\d+(?:\.\d+)?%", text):
        score += 3
    if any(cue in text.lower() for cue in ["according to", "statement", "study", "report", "data", "official"]):
        score += 3
    if any(cue in text.lower() for cue in ["rumor", "unconfirmed", "viral claim", "anonymous"]):
        score -= 6
    return score


def _consistency_bonus(source: Dict[str, Any], peers: Optional[Iterable[Dict[str, Any]]]) -> int:
    if not peers:
        return 0
    title_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", str(source.get("title") or "").lower())
        if len(token) > 3
    }
    if not title_tokens:
        return 0

    agreement = 0
    domains = set()
    own_domain = _domain_from_source(source)
    for peer in peers:
        domain = _domain_from_source(peer)
        if not domain or domain == own_domain or domain in domains:
            continue
        domains.add(domain)
        peer_text = f"{peer.get('title', '')} {peer.get('content', '')} {peer.get('snippet', '')}".lower()
        overlap = sum(1 for token in title_tokens if token in peer_text)
        if overlap >= max(1, min(3, len(title_tokens) // 4)):
            agreement += 1

    if agreement >= 3:
        return 7
    if agreement == 2:
        return 5
    if agreement == 1:
        return 3
    return -2


def calculate_credibility(source: Any, peers: Optional[Iterable[Dict[str, Any]]] = None) -> int:
    """Return a dynamic 0-100 credibility score for a source-like dict or URL."""
    source_dict: Dict[str, Any] = source if isinstance(source, dict) else {"url": source}
    domain = _domain_from_source(source_dict)
    score = _base_domain_score(domain)

    score += _freshness_bonus(source_dict)
    score += _specificity_bonus(source_dict)
    score += _consistency_bonus(source_dict, peers)

    existing = source_dict.get("credibility_score")
    if existing not in (None, ""):
        try:
            existing_score = float(existing)
            if existing_score <= 1:
                existing_score *= 100
            score = int(round((score * 0.75) + (existing_score * 0.25)))
        except Exception:
            pass

    return max(0, min(100, int(round(score))))
