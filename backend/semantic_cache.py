import copy
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from rag.embeddings import embed_query

LOGGER = logging.getLogger("veritas.semantic_cache")

DEFAULT_TTL_SECONDS = int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", "86400"))
DEFAULT_MAX_ITEMS = int(os.getenv("SEMANTIC_CACHE_MAX_ITEMS", "200"))
DEFAULT_SIMILARITY = float(os.getenv("SEMANTIC_CACHE_SIMILARITY", "0.9"))


@dataclass
class CacheEntry:
    query: str
    vector: np.ndarray
    payload: Dict
    created_at: float


class SemanticCache:
    def __init__(
        self,
        max_items: int = DEFAULT_MAX_ITEMS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        similarity_threshold: float = DEFAULT_SIMILARITY,
    ):
        self._max_items = max(1, int(max_items))
        self._ttl_seconds = max(0, int(ttl_seconds))
        self._similarity_threshold = max(0.0, min(1.0, float(similarity_threshold)))
        self._entries: list[CacheEntry] = []
        self._lock = threading.Lock()

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def _prune_expired(self, now: float):
        if self._ttl_seconds <= 0:
            return
        cutoff = now - self._ttl_seconds
        self._entries = [entry for entry in self._entries if entry.created_at >= cutoff]

    def get(self, query: str) -> Tuple[Dict | None, float]:
        if not self._entries:
            return None, 0.0

        query_text = str(query or "").strip()
        if not query_text:
            return None, 0.0

        query_vec = self._normalize(embed_query(query_text))
        now = time.time()

        with self._lock:
            self._prune_expired(now)
            if not self._entries:
                return None, 0.0

            best_score = -1.0
            best_payload = None
            for entry in self._entries:
                score = float(np.dot(entry.vector, query_vec))
                if score > best_score:
                    best_score = score
                    best_payload = entry.payload

            if best_score >= self._similarity_threshold and best_payload is not None:
                LOGGER.info("[SemanticCache] Hit score=%.3f query='%s'", best_score, query_text[:120])
                return copy.deepcopy(best_payload), best_score

        return None, best_score

    def put(self, query: str, payload: Dict):
        query_text = str(query or "").strip()
        if not query_text or not isinstance(payload, dict):
            return

        vector = self._normalize(embed_query(query_text))
        entry = CacheEntry(
            query=query_text,
            vector=vector,
            payload=copy.deepcopy(payload),
            created_at=time.time(),
        )

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_items:
                self._entries = self._entries[-self._max_items :]
