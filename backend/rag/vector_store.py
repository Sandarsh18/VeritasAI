import json
import os
from pathlib import Path
from typing import Dict, List

import numpy as np

from rag.embeddings import get_embedder

try:
    import faiss
except Exception:
    faiss = None

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INDEX_PATH = DATA_DIR / "faiss_index.bin"
VECTORS_PATH = DATA_DIR / "faiss_vectors.npy"
ARTICLES_PATH = DATA_DIR / "news_articles.json"

_INDEX_CACHE = None
_VECTORS_CACHE = None


def load_articles() -> List[Dict]:
    with open(ARTICLES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def build_index(articles: List[Dict] | None = None):
    global _INDEX_CACHE, _VECTORS_CACHE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if articles is None:
        articles = load_articles()

    texts = [f"{a.get('title', '')} {a.get('content', '')}" for a in articles]
    vectors = get_embedder().encode(texts).astype(np.float32)
    np.save(VECTORS_PATH, vectors)
    _VECTORS_CACHE = vectors

    if faiss is not None:
        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(INDEX_PATH))
        _INDEX_CACHE = index
    else:
        with open(INDEX_PATH, "wb") as file:
            file.write(b"NO_FAISS_FALLBACK")


def _ensure_index_exists():
    if not INDEX_PATH.exists() or not VECTORS_PATH.exists():
        build_index()
        return

    try:
        vectors = np.load(VECTORS_PATH)
        article_count = len(load_articles())
        if vectors.shape[0] != article_count:
            build_index()
    except Exception:
        build_index()


def _load_index_and_vectors():
    global _INDEX_CACHE, _VECTORS_CACHE
    _ensure_index_exists()

    if _VECTORS_CACHE is None:
        _VECTORS_CACHE = np.load(VECTORS_PATH)

    if faiss is not None and _INDEX_CACHE is None:
        _INDEX_CACHE = faiss.read_index(str(INDEX_PATH))



def search(query: str, k: int = 20) -> List[Dict]:
    _load_index_and_vectors()
    query_vector = get_embedder().encode([query]).astype(np.float32)

    if _VECTORS_CACHE is None or len(_VECTORS_CACHE) == 0:
        return []

    results = []
    top_k = min(k, len(_VECTORS_CACHE))

    if faiss is not None and _INDEX_CACHE is not None:
        distances, indices = _INDEX_CACHE.search(query_vector, top_k)
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0:
                continue
            similarity = 1.0 / (1.0 + float(dist))
            if similarity >= 0.15:
                results.append(
                    {
                        "index": int(idx),
                        "distance": float(dist),
                        "similarity": float(similarity),
                    }
                )
    else:
        l2_distances = np.linalg.norm(_VECTORS_CACHE - query_vector[0], axis=1)
        sorted_indices = np.argsort(l2_distances)[:top_k]
        for idx in sorted_indices:
            dist = float(l2_distances[idx])
            similarity = 1.0 / (1.0 + dist)
            if similarity >= 0.15:
                results.append(
                    {
                        "index": int(idx),
                        "distance": dist,
                        "similarity": float(similarity),
                    }
                )

    return results
