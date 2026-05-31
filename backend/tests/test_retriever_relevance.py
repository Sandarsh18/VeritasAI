import numpy as np

from rag import retriever


class _DummyStore:
    def __init__(self, dimension):
        self.dimension = dimension

    def add_documents(self, vectors, documents):
        return None

    def search(self, vector, k=5):
        return []


def _patch_embeddings(monkeypatch):
    monkeypatch.setattr(retriever, "embed_texts", lambda texts: np.zeros((len(texts), 4)))
    monkeypatch.setattr(retriever, "FaissStore", _DummyStore)


def test_retrieve_evidence_filters_irrelevant_domain(monkeypatch):
    tech_doc = {
        "title": "India expands 6G telecom research",
        "source": "TechWire",
        "content": "India begins new 6G spectrum trials for telecom networks.",
        "url": "https://example.com/6g",
        "source_url": "https://example.com/6g",
        "published_date": "",
        "credibility_score": 0.86,
        "evidence_source": "newsapi",
    }
    sports_doc = {
        "title": "India vs Pakistan T20 cricket series preview",
        "source": "SportsDesk",
        "content": "India prepares for the cricket T20 series with Pakistan.",
        "url": "https://example.com/cricket",
        "source_url": "https://example.com/cricket",
        "published_date": "",
        "credibility_score": 0.82,
        "evidence_source": "newsapi",
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
        "search_tavily",
        lambda query, top_n=10: ([], {"ok": False, "count": 0, "provider": "tavily"}),
    )
    monkeypatch.setattr(
        retriever,
        "_search_serpapi",
        lambda query, top_n=10: ([dict(tech_doc), dict(sports_doc)], {"ok": True, "count": 2}),
    )
    monkeypatch.setattr(
        retriever,
        "_search_newsapi",
        lambda query, top_n=10: ([], {"ok": True, "count": 0}),
    )
    monkeypatch.setattr(
        retriever,
        "_enrich_full_content",
        lambda articles, max_fetch=10: articles,
    )
    monkeypatch.setattr(
        retriever,
        "_compute_article_similarity",
        lambda claim, articles: (
            [
                {**articles[0], "similarity_score": 0.84},
                {**articles[1], "similarity_score": 0.81},
            ],
            np.zeros((1, 1)),
            0.01,
        ),
    )
    _patch_embeddings(monkeypatch)

    evidence, meta = retriever.retrieve_evidence(
        claim="Is India developing 6G?",
        keywords=["India", "6G"],
        domain="technology",
        top_k=5,
        max_retries=1,
    )

    assert len(evidence) == 1
    assert "6G" in evidence[0]["title"]
    assert all("cricket" not in row["title"].lower() for row in evidence)
    assert meta.get("insufficient_data") is not True


def test_retrieve_evidence_returns_insufficient_data(monkeypatch):
    irrelevant_doc = {
        "title": "Local festival draws large crowds",
        "source": "CommunityNews",
        "content": "Celebrations continued late into the evening with music and food stalls.",
        "url": "https://example.com/festival",
        "source_url": "https://example.com/festival",
        "published_date": "",
        "credibility_score": 0.74,
        "evidence_source": "newsapi",
    }

    monkeypatch.setattr(
        retriever,
        "_understand_claim",
        lambda claim, keywords=None: {
            "entities": ["blorpy"],
            "intent": "verify factual claim",
            "keywords": ["blorpy", "nonsense"],
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
        "search_tavily",
        lambda query, top_n=10: ([], {"ok": False, "count": 0, "provider": "tavily"}),
    )
    monkeypatch.setattr(
        retriever,
        "_search_serpapi",
        lambda query, top_n=10: ([dict(irrelevant_doc)], {"ok": True, "count": 1}),
    )
    monkeypatch.setattr(
        retriever,
        "_search_newsapi",
        lambda query, top_n=10: ([], {"ok": True, "count": 0}),
    )
    monkeypatch.setattr(
        retriever,
        "_enrich_full_content",
        lambda articles, max_fetch=10: articles,
    )
    monkeypatch.setattr(
        retriever,
        "_compute_article_similarity",
        lambda claim, articles: ([{**articles[0], "similarity_score": 0.22}], np.zeros((1, 1)), 0.01),
    )
    _patch_embeddings(monkeypatch)

    evidence, meta = retriever.retrieve_evidence(
        claim="blorpy nonsense flarn",
        keywords=["blorpy"],
        domain="technology",
        top_k=5,
        max_retries=1,
    )

    assert evidence == []
    assert meta.get("error") == "INSUFFICIENT_DATA"
    assert meta.get("insufficient_data") is True
