"""Unit tests for the Tavily client (graceful degradation + normalization)."""

import importlib
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _reload_with_key(monkeypatch, key_value):
    monkeypatch.setenv("TAVILY_API_KEY", key_value)
    import rag.tavily_client as tc
    importlib.reload(tc)
    return tc


def test_degrades_gracefully_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False, raising=False)
    import rag.tavily_client as tc
    importlib.reload(tc)
    assert tc.tavily_available is False
    articles, meta = tc.search_tavily("any claim")
    assert articles == []
    assert meta["ok"] is False
    assert meta["count"] == 0


def test_normalization_shape(monkeypatch):
    tc = _reload_with_key(monkeypatch, "tvly-test-key")

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def search(self, **kwargs):
            return {
                "results": [
                    {
                        "url": "https://www.britannica.com/x",
                        "title": "Which Religion Is the Oldest?",
                        "content": "Short snippet about religions.",
                        "raw_content": "A much longer body of cleaned content " * 20,
                        "score": 0.91,
                        "published_date": "2024-01-01",
                    },
                    {"title": "No URL row", "content": "x"},  # should be discarded
                ]
            }

    import tavily
    monkeypatch.setattr(tavily, "TavilyClient", _FakeClient, raising=False)

    articles, meta = tc.search_tavily("Is Islam older than Hinduism?", top_n=5)
    assert meta["ok"] is True
    assert len(articles) == 1  # one discarded for missing url
    a = articles[0]
    for key in (
        "title", "source", "content", "url", "source_url",
        "published_date", "credibility_score", "evidence_source", "full_content",
    ):
        assert key in a
    assert a["evidence_source"] == "tavily"
    assert 0.0 <= a["credibility_score"] <= 1.0
    assert len(a["full_content"]) <= 1600
    assert len(meta["discarded"]) == 1


def test_emits_observability_logs(monkeypatch, caplog):
    tc = _reload_with_key(monkeypatch, "tvly-test-key")

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def search(self, **kwargs):
            return {"results": [{"url": "https://x.com/a", "title": "T", "content": "c"}]}

    import tavily
    monkeypatch.setattr(tavily, "TavilyClient", _FakeClient, raising=False)

    with caplog.at_level(logging.INFO, logger="veritas.tavily"):
        tc.search_tavily("hello world")
    text = "\n".join(caplog.messages)
    assert "TAVILY QUERY" in text
    assert "TAVILY RESULTS COUNT" in text
    assert "TAVILY SOURCES" in text
    assert "TAVILY RESPONSE" in text
