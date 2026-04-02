import hashlib
import re
from typing import Dict, List

import faiss
import numpy as np
from credibility import score_source


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _hash_vector(text: str, dim: int = 256) -> np.ndarray:
    vec = np.zeros(dim, dtype="float32")
    for token in _tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        vec[idx] += 1.0

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def rank_with_faiss(claim: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
    if not results:
        return []

    vectors = []
    for row in results:
        combined = f"{row.get('title', '')} {row.get('snippet', '')}"
        vectors.append(_hash_vector(combined))

    matrix = np.vstack(vectors).astype("float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    query_vec = _hash_vector(claim).reshape(1, -1).astype("float32")
    k = min(max(1, top_k), len(results))
    distances, indices = index.search(query_vec, k)

    ranked = []
    for i, idx in enumerate(indices[0].tolist()):
        row = dict(results[idx])
        similarity = float(distances[0][i])
        url = row.get("link") or row.get("source_url") or ""
        credibility = score_source(url)

        weighted_score = similarity * (0.5 + 0.5 * credibility)

        row["similarity"] = similarity
        row["credibility_score"] = credibility
        row["weighted_score"] = weighted_score
        ranked.append(row)

    # Re-sort by the new weighted score
    ranked.sort(key=lambda x: x["weighted_score"], reverse=True)

    return ranked


def build_context(results: List[Dict]) -> str:
    chunks = []
    for item in results or []:
        source = item.get("source", "Unknown")
        url = item.get("link", "")
        snippet = item.get("snippet", "").strip()
        if not snippet:
            continue
        chunks.append(f"[Source: {source} | URL: {url}]\n{snippet}")
    return "\n\n".join(chunks)
