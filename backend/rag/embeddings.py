import hashlib
import logging
import re
from typing import List

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

LOGGER = logging.getLogger(__name__)


class EmbeddingModelSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
            cls._instance._dim = 384
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        if SentenceTransformer is None:
            LOGGER.warning("sentence-transformers not available. Using fallback embeddings.")
            return
        try:
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._dim = self._model.get_sentence_embedding_dimension()
        except Exception as exc:
            LOGGER.warning("Failed to load sentence transformer. Using fallback embeddings. Error: %s", exc)
            self._model = None
            self._dim = 384

    def _fallback_encode(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self._dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return vec if norm == 0 else vec / norm

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        if self._model is not None:
            vectors = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return vectors.astype(np.float32)
        return np.stack([self._fallback_encode(t or "") for t in texts]).astype(np.float32)


def get_embedder() -> EmbeddingModelSingleton:
    return EmbeddingModelSingleton()


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of texts with SentenceTransformer fallback support."""
    return get_embedder().encode(texts)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query and return a 1D float32 vector."""
    vectors = get_embedder().encode([query or ""])
    if vectors.shape[0] == 0:
        return np.zeros((get_embedder()._dim,), dtype=np.float32)
    return vectors[0]
