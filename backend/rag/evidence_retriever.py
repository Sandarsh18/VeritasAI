import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from rag.realtime_fetcher import fetch_realtime_evidence

MODEL = SentenceTransformer("all-MiniLM-L6-v2")
INDEX = None
ARTICLES = []


def load_index():
    global INDEX, ARTICLES
    try:
        INDEX = faiss.read_index("faiss_index.bin")
        with open("data/news_articles.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        ARTICLES = data if isinstance(data, list) else data.get("articles", [])
        print(f"FAISS: {len(ARTICLES)} local articles")
    except Exception as exc:
        print(f"FAISS load error: {exc}")


def search_local(claim: str, top_k: int = 5) -> list:
    if INDEX is None:
        load_index()
    if INDEX is None or not ARTICLES:
        return []

    try:
        embedding = MODEL.encode([claim])
        distances, indices = INDEX.search(np.array(embedding).astype("float32"), top_k * 2)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(ARTICLES):
                continue

            similarity = float(1 / (1 + dist))
            if similarity < 0.20:
                continue

            article = ARTICLES[idx].copy()
            article["relevance_score"] = round(similarity, 3)
            article["is_realtime"] = False
            article["source_url"] = article.get("source_url", "")
            article["author"] = article.get("author", "Editorial Team")
            article["published_date"] = article.get("published_date", "2024")
            article["source_logo"] = article.get("source_logo", "📰")
            article["source_type"] = article.get("source_type", "News Archive")
            article["image_url"] = article.get("image_url", "")
            results.append(article)

        results.sort(key=lambda item: item["relevance_score"], reverse=True)
        return results[:top_k]
    except Exception as exc:
        print(f"Local search error: {exc}")
        return []


def retrieve_evidence(claim: str) -> dict:
    print(f"\n[RAG] Retrieving evidence for: {claim[:60]}")

    local_articles = search_local(claim, top_k=3)
    print(f"[RAG] Local: {len(local_articles)} articles")

    realtime_articles = fetch_realtime_evidence(claim, max_results=7)
    print(f"[RAG] Real-time: {len(realtime_articles)} articles")

    all_articles = []
    seen_titles = set()

    for article in realtime_articles:
        title = article.get("title", "").lower()[:50]
        if title and title not in seen_titles:
            seen_titles.add(title)
            article["evidence_source"] = "real-time"
            all_articles.append(article)

    for article in local_articles:
        title = article.get("title", "").lower()[:50]
        if title and title not in seen_titles:
            seen_titles.add(title)
            article["evidence_source"] = "archive"
            all_articles.append(article)

    for article in all_articles:
        cred = float(article.get("credibility_score", 0.5))
        relev = float(article.get("relevance_score", 0.3))
        rt_bonus = 0.1 if article.get("is_realtime") else 0
        article["combined_score"] = round((cred * 0.4) + (relev * 0.4) + rt_bonus, 3)

    all_articles.sort(key=lambda item: item.get("combined_score", 0), reverse=True)
    final = all_articles[:5]

    if not final:
        return {
            "articles": [],
            "insufficient_evidence": True,
            "message": "No relevant articles found",
        }

    print(f"[RAG] Final: {len(final)} combined articles")
    for article in final:
        marker = "🌐 LIVE" if article.get("is_realtime") else "📁 ARCHIVE"
        print(f"  {marker} | {article.get('source', '?')} | score={article.get('combined_score', '?')}")

    return {
        "articles": final,
        "insufficient_evidence": False,
        "realtime_count": sum(1 for article in final if article.get("is_realtime")),
        "archive_count": sum(1 for article in final if not article.get("is_realtime")),
    }


load_index()
