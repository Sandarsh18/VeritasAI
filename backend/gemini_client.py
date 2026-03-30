import json
import os
import re
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def gemini_complete(prompt: str, temperature: float = 0.2, max_output_tokens: int = 1024) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }

    response = requests.post(endpoint, json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")

    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    if not parts:
        raise RuntimeError("Gemini returned empty content")

    text = parts[0].get("text", "").strip()
    if not text:
        raise RuntimeError("Gemini returned blank text")
    return text


def _extract_json_block(raw: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1)

    first_obj = re.search(r"\{.*\}", raw, re.DOTALL)
    if first_obj:
        return first_obj.group(0)

    return raw.strip()


def gemini_complete_json(prompt: str) -> Dict[str, Any]:
    raw = gemini_complete(prompt)
    body = _extract_json_block(raw)
    try:
        return json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Gemini JSON parse failed: {exc}") from exc
