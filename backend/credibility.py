"""
credibility.py - Domain trust scoring for VeritasAI evidence ranking.
"""

DOMAIN_TRUST = {
    "reuters.com": 0.95, "apnews.com": 0.95, "bbc.com": 0.90,
    "theguardian.com": 0.88, "nytimes.com": 0.87, "washingtonpost.com": 0.87,
    "economist.com": 0.90, "nature.com": 0.95, "science.org": 0.95,
    "who.int": 0.95, "cdc.gov": 0.95, "nih.gov": 0.95,
    "snopes.com": 0.85, "factcheck.org": 0.88, "politifact.com": 0.85,
    "thehindu.com": 0.82, "ndtv.com": 0.78, "timesofindia.com": 0.78,
    "aljazeera.com": 0.82, "bloomberg.com": 0.88,
    "espncricinfo.com": 0.88, "cricbuzz.com": 0.86,
    "iplt20.com": 0.92, "icc-cricket.com": 0.92,
    "sportstar.thehindu.com": 0.86, "wisden.com": 0.84,
    "mykhel.com": 0.72, "crictracker.com": 0.72
}

from urllib.parse import urlparse


def score_source(url: str) -> float:
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        return DOMAIN_TRUST.get(domain, 0.5)
    except Exception:
        return 0.5
