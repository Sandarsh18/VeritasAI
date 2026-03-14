from .vector_store import search

def retrieve_evidence(claim: str, top_k: int = 5) -> list[dict]:
    """Retrieve top relevant articles for a claim."""
    results = search(claim, top_k=top_k)
    evidence = []
    for article in results:
        content = article.get('content', '')[:300]
        evidence.append({
            'id': article.get('id'),
            'title': article.get('title'),
            'content': content,
            'source': article.get('source'),
            'credibility_score': article.get('credibility_score', 0.5),
            'category': article.get('category'),
            'verdict': article.get('verdict'),
            'date': article.get('date'),
            'relevance_score': article.get('relevance_score', 0.0)
        })
    return evidence
