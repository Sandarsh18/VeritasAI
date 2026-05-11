"""
credibility.py - Compatibility wrapper for VeritasAI evidence ranking.

score_source() is intentionally kept as a 0-1 return value because ranking,
judge, and legacy modules already consume that API.
"""

from services.credibility_service import calculate_credibility


def score_source(url: str) -> float:
    try:
        return round(calculate_credibility({"url": url}) / 100, 4)
    except Exception:
        return 0.5
