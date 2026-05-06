from __future__ import annotations

import hashlib
from typing import Any, Dict


def claim_hash_for(claim: str) -> str:
    return hashlib.sha256((claim or "").strip().lower().encode()).hexdigest()


def cache_state(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"cache_hit": False, "cache_source": None}
    return {
        "cache_hit": bool(payload.get("cache_hit")),
        "cache_source": payload.get("cache_source"),
    }
