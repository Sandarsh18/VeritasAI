import logging
from typing import Dict, List

import numpy as np

try:
    import faiss
except Exception:
    faiss = None

LOGGER = logging.getLogger("veritas.rag.faiss")


class FaissStore:
    """In-memory FAISS cosine-similarity store for fetched evidence docs."""

    def __init__(self, dimension: int):
        self.dimension = int(dimension)
        self._documents: List[Dict] = []
        self._vectors: np.ndarray | None = None
        self._index = faiss.IndexFlatIP(self.dimension) if faiss is not None else None

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def add_documents(self, vectors: np.ndarray, documents: List[Dict]):
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if arr.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.dimension}, got {arr.shape[1]}"
            )

        if len(documents) != arr.shape[0]:
            raise ValueError("Vectors/documents length mismatch")

        arr = self._normalize(arr)

        if self._index is not None:
            self._index.add(arr)

        if self._vectors is None:
            self._vectors = arr
        else:
            self._vectors = np.vstack([self._vectors, arr]).astype(np.float32)

        self._documents.extend(documents)

    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Dict]:
        if not self._documents:
            return []

        q = np.asarray(query_vector, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)

        if q.shape[1] != self.dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.dimension}, got {q.shape[1]}"
            )

        q = self._normalize(q)
        top_k = min(max(1, int(k)), len(self._documents))

        if self._index is not None:
            similarities, indices = self._index.search(q, top_k)
            pairs = zip(indices[0].tolist(), similarities[0].tolist())
        else:
            LOGGER.warning("FAISS not available; using numpy cosine fallback")
            assert self._vectors is not None
            sims = np.dot(self._vectors, q[0])
            order = np.argsort(sims)[::-1][:top_k]
            pairs = ((int(i), float(sims[i])) for i in order)

        hits: List[Dict] = []
        for idx, similarity in pairs:
            if idx < 0 or idx >= len(self._documents):
                continue
            hits.append(
                {
                    "rank": len(hits) + 1,
                    "similarity": float(similarity),
                    "document": self._documents[idx],
                }
            )

        return hits
