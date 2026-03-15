import json
import re

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:1b"
REQUEST_TIMEOUT = 120
MAX_RETRIES = 2


def call_ollama(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    retries: int = MAX_RETRIES,
    num_predict: int = 250,
    temperature: float = 0,
    num_ctx: int = 1024,
) -> str:
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {
                        "num_predict": num_predict,
                        "temperature": temperature,
                        "num_ctx": num_ctx,
                        "num_thread": 4,
                        "repeat_penalty": 1.0,
                    },
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.Timeout:
            if attempt == retries - 1:
                return ""
        except Exception as exc:
            if attempt == retries - 1:
                print(f"Ollama fallback: {exc}")
                return ""
    return ""


def extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None
