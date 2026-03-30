from typing import Dict, List



def track_false_claim_sources(claim: str, evidence: List[Dict]) -> Dict:
    low_confidence_sources = []
    for article in evidence:
        if float(article.get("credibility_score", 0.0)) < 0.75:
            low_confidence_sources.append(article.get("source", "Unknown"))

    return {
        "claim": claim,
        "suspicious_sources": sorted(set(low_confidence_sources)),
        "note": "Tracked likely weak sources for manual moderation.",
    }
