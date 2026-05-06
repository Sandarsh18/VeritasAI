from __future__ import annotations

import logging
from typing import Any, Dict

LOGGER = logging.getLogger("veritas.metrics")


def build_pipeline_metrics(
    retrieval_time: float,
    embedding_time: float,
    agent_time: float,
    total_time: float,
    cache_hit: bool,
    **extra: Any,
) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "retrieval_time": round(float(retrieval_time or 0.0), 4),
        "embedding_time": round(float(embedding_time or 0.0), 4),
        "agent_time": round(float(agent_time or 0.0), 4),
        "total_time": round(float(total_time or 0.0), 4),
        "cache_hit": bool(cache_hit),
    }
    for key, value in extra.items():
        if value is not None:
            metrics[key] = value
    return metrics


def log_pipeline_metrics(label: str, metrics: Dict[str, Any]) -> None:
    LOGGER.info("[%s] metrics=%s", label, metrics)


def log_latency_comparison(label: str, baseline_seconds: float, optimized_seconds: float) -> str:
    baseline = float(baseline_seconds or 0.0)
    optimized = float(optimized_seconds or 0.0)
    if baseline <= 0 or optimized <= 0:
        return ""

    improvement = max(0.0, ((baseline - optimized) / baseline) * 100.0)
    message = f"Latency reduced from {baseline:.1f}s -> {optimized:.1f}s ({improvement:.0f}% improvement)"
    LOGGER.info("[%s] %s", label, message)
    return message
