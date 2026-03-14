import faiss
import numpy as np
import json
import os
from .embeddings import generate_embedding, batch_embed

INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss_index.bin')
ARTICLES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'news_articles.json')

_index = None
_articles = None

def load_articles():
    global _articles
    if _articles is None:
        with open(ARTICLES_PATH, 'r') as f:
            _articles = json.load(f)
    return _articles

def build_index():
    global _index, _articles
    articles = load_articles()
    texts = [f"{a['title']} {a['content']}" for a in articles]
    print(f"Building FAISS index for {len(texts)} articles...")
    embeddings = batch_embed(texts)
    dim = len(embeddings[0])
    index = faiss.IndexFlatIP(dim)
    matrix = np.array(embeddings).astype('float32')
    faiss.normalize_L2(matrix)
    index.add(matrix)
    faiss.write_index(index, INDEX_PATH)
    _index = index
    print(f"FAISS index built and saved to {INDEX_PATH}")
    return index

def get_index():
    global _index
    if _index is None:
        if os.path.exists(INDEX_PATH):
            _index = faiss.read_index(INDEX_PATH)
        else:
            _index = build_index()
    return _index

def search(query: str, top_k: int = 5) -> list[dict]:
    articles = load_articles()
    index = get_index()
    query_embedding = generate_embedding(query).astype('float32')
    query_embedding = query_embedding.reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    scores, indices = index.search(query_embedding, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(articles):
            article = articles[idx].copy()
            article['relevance_score'] = float(score)
            results.append(article)
    return results
