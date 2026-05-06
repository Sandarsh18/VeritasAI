import numpy as np

from rag import retriever


def test_retrieve_evidence_falls_back_to_local_dataset(monkeypatch):
    local_row = {
        "title": "India 6G research initiative expands",
        "source": "LocalDataset",
        "content": "India is accelerating 6G telecom research with new spectrum trials.",
        "url": "https://example.com/fallback",
        "source_url": "https://example.com/fallback",
        "published_date": "",
        "credibility_score": 0.82,
        "evidence_source": "local_fallback",
    }

    monkeypatch.setattr(
        retriever,
        "_understand_claim",
        lambda claim, keywords=None: {
            "entities": ["India", "6G"],
            "intent": "verify factual claim",
            "keywords": ["india", "6g", "telecom"],
            "domain": "technology",
        },
    )
    monkeypatch.setattr(
        retriever,
        "_generate_query_variants",
        lambda claim, understanding, max_queries=5: [claim],
    )
    monkeypatch.setattr(
        retriever,
        "_search_serpapi",
        lambda query, top_n=10: ([], {"ok": False, "count": 0}),
    )
    monkeypatch.setattr(
        retriever,
        "_search_newsapi",
        lambda query, top_n=10: ([], {"ok": False, "count": 0}),
    )
    monkeypatch.setattr(
        retriever,
        "_load_local_fallback",
        lambda claim, keywords=None: [dict(local_row)],
    )
    monkeypatch.setattr(
        retriever,
        "_enrich_full_content",
        lambda articles, max_fetch=10: articles,
    )
    monkeypatch.setattr(
        retriever,
        "_compute_article_similarity",
        lambda claim, articles: ([{**articles[0], "similarity_score": 0.86}], np.zeros((1, 1)), 0.01),
    )

    class _DummyStore:
        def __init__(self, dimension):
            self.dimension = dimension

        def add_documents(self, vectors, documents):
            return None

        def search(self, vector, k=5):
            return []

    monkeypatch.setattr(retriever, "embed_texts", lambda texts: np.zeros((len(texts), 4)))
    monkeypatch.setattr(retriever, "FaissStore", _DummyStore)

    evidence, meta = retriever.retrieve_evidence(
        claim="Is India developing 6G?",
        keywords=["India", "6G"],
        domain="technology",
        top_k=5,
        max_retries=1,
    )

    assert len(evidence) == 1
    assert evidence[0]["source"] == "LocalDataset"
    assert meta.get("fallback_used") is True
    assert meta.get("insufficient_data") is not True
