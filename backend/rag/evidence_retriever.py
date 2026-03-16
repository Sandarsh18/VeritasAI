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
        print(f"FAISS loaded: {len(ARTICLES)} articles")
    except Exception as exc:
        print(f"FAISS load error: {exc}")


def compute_relevance(claim: str, article: dict) -> float:
    claim_words = set(claim.lower().split())
    stop_words = {
        "is", "are", "was", "were", "the", "a", "an",
        "in", "of", "to", "and", "or", "that", "this",
        "it", "for", "on", "with", "at", "by", "from",
        "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "than", "then",
    }
    claim_words -= stop_words

    if not claim_words:
        return 0.3

    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    keywords = article.get("keywords", [])
    keywords_text = " ".join([item.lower() for item in keywords])
    combined = f"{title} {content} {keywords_text}"

    matches = sum(1 for word in claim_words if word in combined and len(word) > 2)
    return matches / max(len(claim_words), 1)


def search_local(
    claim: str,
    top_k: int = 5,
    min_vector_sim: float = 0.15,
    min_keyword_match: float = 0.10,
) -> list:
    if INDEX is None:
        load_index()
    if INDEX is None or not ARTICLES:
        return []

    try:
        embedding = MODEL.encode([claim])
        k = min(top_k * 4, len(ARTICLES))
        distances, indices = INDEX.search(np.array(embedding).astype("float32"), k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(ARTICLES):
                continue

            vector_sim = float(1 / (1 + dist))
            if vector_sim < min_vector_sim:
                continue

            article = ARTICLES[idx].copy()

            keyword_score = compute_relevance(claim, article)
            if keyword_score < min_keyword_match:
                continue

            combined_score = (vector_sim * 0.5) + (keyword_score * 0.5)
            article["relevance_score"] = round(combined_score, 3)
            article["vector_similarity"] = round(vector_sim, 3)
            article["keyword_match"] = round(keyword_score, 3)
            article["is_realtime"] = False
            article["evidence_source"] = "archive"
            article["source_url"] = article.get("source_url", "")
            article["author"] = article.get("author", "Editorial Team")
            article["published_date"] = article.get("published_date", "2024")
            article["source_logo"] = article.get("source_logo", "📰")
            article["source_type"] = article.get("source_type", "News Archive")
            article["image_url"] = article.get("image_url", "")
            results.append(article)

        results.sort(key=lambda item: item["relevance_score"], reverse=True)
        print(f"[RAG Local] {len(results)} articles passed dual filter")
        return results[:top_k]
    except Exception as exc:
        print(f"Local search error: {exc}")
        return []


def retrieve_evidence(claim: str) -> dict:
    print(f"\n[RAG] Claim: '{claim[:60]}'")

    local_articles = search_local(claim, top_k=3, min_vector_sim=0.15, min_keyword_match=0.10)
    print(f"[RAG] Local: {len(local_articles)} relevant articles")

    realtime_articles = []
    try:
        realtime_articles = fetch_realtime_evidence(claim, max_results=7)
        print(f"[RAG] Real-time: {len(realtime_articles)} articles")
    except Exception as exc:
        print(f"[RAG] Real-time error: {exc}")

    filtered_realtime = []
    for article in realtime_articles:
        kw_score = compute_relevance(claim, article)
        if kw_score >= 0.05:
            article["relevance_score"] = round(kw_score, 3)
            filtered_realtime.append(article)

    print(f"[RAG] Real-time after filter: {len(filtered_realtime)}")

    all_articles = []
    seen_titles = set()

    for article in filtered_realtime:
        title = article.get("title", "").lower()[:40]
        if title not in seen_titles:
            seen_titles.add(title)
            all_articles.append(article)

    for article in local_articles:
        title = article.get("title", "").lower()[:40]
        if title not in seen_titles:
            seen_titles.add(title)
            all_articles.append(article)

    for article in all_articles:
        cred = float(article.get("credibility_score", 0.5))
        relev = float(article.get("relevance_score", 0.3))
        rt_bonus = 0.1 if article.get("is_realtime") else 0
        article["combined_score"] = round((cred * 0.4) + (relev * 0.4) + rt_bonus, 3)

    all_articles.sort(key=lambda item: item.get("combined_score", 0), reverse=True)
    final = all_articles[:5]

    print(f"[RAG] Final: {len(final)} articles")
    for article in final:
        rt = "🌐" if article.get("is_realtime") else "📁"
        print(
            f"  {rt} {article.get('source', '?'):15} | "
            f"kw={float(article.get('keyword_match', 0)):.2f} | "
            f"vec={float(article.get('vector_similarity', 0)):.2f} | "
            f"title={article.get('title', '')[:40]}"
        )

    if not final:
        return {
            "articles": [],
            "insufficient_evidence": True,
            "message": "No relevant articles found",
        }

    return {
        "articles": final,
        "insufficient_evidence": False,
        "realtime_count": sum(1 for article in final if article.get("is_realtime")),
        "archive_count": sum(1 for article in final if not article.get("is_realtime")),
    }


load_index()
