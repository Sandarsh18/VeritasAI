import faiss
import numpy as np
import json
import os
from .embeddings import generate_embedding, batch_embed

INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss_index.bin')
ARTICLES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'news_articles.json')
METADATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'articles_metadata.json')

_index = None
_articles = None


def _article_to_text(article: dict) -> str:
    keywords = " ".join(article.get('keywords', []))
    return f"{article.get('title', '')} {keywords} {article.get('content', '')[:500]}"

def load_articles():
    global _articles
    if _articles is None:
        source_path = METADATA_PATH if os.path.exists(METADATA_PATH) else ARTICLES_PATH
        with open(source_path, 'r') as f:
            _articles = json.load(f)
    return _articles

def build_index():
    global _index, _articles
    articles = load_articles()
    texts = [_article_to_text(article) for article in articles]
    print(f"Building FAISS index for {len(texts)} articles...")
    embeddings = batch_embed(texts)
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    matrix = np.array(embeddings).astype('float32')
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
    distances, indices = index.search(query_embedding, top_k)
    results = []
    for distance, idx in zip(distances[0], indices[0]):
        if idx < len(articles):
            article = articles[idx].copy()
            article['distance_score'] = float(distance)
            results.append(article)
    return results
