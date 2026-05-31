#!/usr/bin/env python3
"""Wait for Ollama to be reachable before starting backend."""
import os
import sys
import time
from urllib.parse import urljoin

import requests


def is_ollama_ready(base_url: str) -> bool:
    tags_url = urljoin(base_url, "/api/tags")
    try:
        resp = requests.get(tags_url, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def list_models(base_url: str) -> set[str]:
    tags_url = urljoin(base_url, "/api/tags")
    try:
        resp = requests.get(tags_url, timeout=10)
        resp.raise_for_status()
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        models = data.get("models") or []
        names = {str(item.get("name", "")).strip() for item in models if isinstance(item, dict)}
        return {name for name in names if name}
    except Exception:
        return set()


def ensure_model(base_url: str, model_name: str, timeout: int = 1200) -> bool:
    if not model_name:
        return True

    existing = list_models(base_url)
    if model_name in existing:
        print(f"Ollama model present: {model_name}")
        return True

    pull_url = urljoin(base_url, "/api/pull")
    print(f"Pulling Ollama model: {model_name}")
    try:
        resp = requests.post(
            pull_url,
            json={"name": model_name, "stream": False},
            timeout=timeout,
        )
        if resp.status_code >= 400:
            print(f"Model pull failed ({model_name}) status={resp.status_code} body={resp.text[:240]}")
            return False
    except Exception as exc:
        print(f"Model pull failed ({model_name}): {exc}")
        return False

    refreshed = list_models(base_url)
    if model_name in refreshed:
        print(f"Ollama model ready: {model_name}")
        return True

    print(f"Model not visible after pull: {model_name}")
    return False


def wait(base_url: str, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if is_ollama_ready(base_url):
                print(f"Ollama ready at {base_url}")
                return True
        except Exception:
            pass
        time.sleep(3)
        print("Waiting for Ollama...")
    print("Timeout waiting for Ollama")
    return False


if __name__ == "__main__":
    base = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    ok = wait(base, timeout=int(os.getenv("OLLAMA_WAIT_TIMEOUT", "180")))
    if not ok:
        print("Proceeding even though Ollama did not become ready (fallbacks may apply)")
        sys.exit(0)

    auto_pull = os.getenv("OLLAMA_AUTO_PULL_MODELS", "1").strip() not in {"0", "false", "False"}
    block_on_pull = os.getenv("OLLAMA_BLOCK_ON_MODEL_PULL", "0").strip() in {"1", "true", "True"}
    if auto_pull:
        configured = os.getenv("OLLAMA_BOOT_MODELS", "").strip()
        if configured:
            requested_models = [item.strip() for item in configured.split(",") if item.strip()]
        else:
            requested_models = [
                os.getenv("OLLAMA_ANALYZER_MODEL", "").strip(),
                os.getenv("OLLAMA_MODEL", "").strip(),
            ]

        seen = set()
        ordered_models = []
        for model in requested_models:
            if model and model not in seen:
                seen.add(model)
                ordered_models.append(model)

        for model in ordered_models:
            if block_on_pull:
                ensure_model(base, model)
            else:
                present = list_models(base)
                if model in present:
                    print(f"Ollama model present: {model}")
                else:
                    print(
                        f"Ollama model missing (non-blocking startup): {model}. "
                        "Pull it with 'docker compose exec -T ollama ollama pull <model>'."
                    )

    sys.exit(0)
