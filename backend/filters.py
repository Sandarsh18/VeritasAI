import re
from urllib.parse import urlparse
from typing import Dict, List

TRUSTED = ["reuters.com", "bbc.com", "who.int", "thehindu.com", "ndtv.com"]
LOW_QUALITY_HINTS = ["login", "ads", "forum", "forums", "pinterest", "youtube"]


def _extract_domains_from_claim(claim: str) -> List[str]:
    text = (claim or "").lower()
    domains = set()

    for match in re.findall(r"https?://([^\s/]+)", text):
        domains.add(match.replace("www.", "").strip())

    for match in re.findall(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", text):
        domains.add(match.replace("www.", "").strip())

    return [d for d in domains if d]


def _domain_from_url(url: str) -> str:
    try:
        netloc = urlparse(url or "").netloc.lower().replace("www.", "").strip()
        return netloc
    except Exception:
        return ""


def remove_self_source(results: List[Dict], claim: str) -> List[Dict]:
    claim_domains = _extract_domains_from_claim(claim)
    if not claim_domains:
        return results or []

    filtered = []
    for row in results or []:
        domain = _domain_from_url(row.get("link", ""))
        if any(domain == c or domain.endswith(f".{c}") for c in claim_domains):
            continue
        filtered.append(row)
    return filtered


def remove_low_quality(results: List[Dict]) -> List[Dict]:
    filtered = []
    for row in results or []:
        url = (row.get("link") or "").lower()
        if any(token in url for token in LOW_QUALITY_HINTS):
            continue
        filtered.append(row)
    return filtered


def prioritize_trusted(results: List[Dict]) -> List[Dict]:
    def sort_key(item: Dict):
        url = _domain_from_url(item.get("link", ""))
        trusted_rank = next((idx for idx, domain in enumerate(TRUSTED) if url == domain or url.endswith(f".{domain}")), None)
        is_trusted = trusted_rank is not None
        return (0 if is_trusted else 1, trusted_rank if trusted_rank is not None else 999, url)

    ranked = sorted(results or [], key=sort_key)
    return ranked[:5]
