"""
LLM Client — NVIDIA NIM API primary, Ollama fallback.
Uses OpenAI-compatible API from NVIDIA.
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

NVIDIA_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
USE_NVIDIA = bool(NVIDIA_KEY)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b").strip()

nvidia_client = None
if NVIDIA_KEY:
    try:
        nvidia_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_KEY)
        print(f"✅ NVIDIA API ready: {NVIDIA_MODEL}")
    except Exception as exc:
        print(f"❌ NVIDIA init failed: {exc}")


def call_nvidia(prompt: str, max_tokens: int = 600, temperature: float = 0.1) -> str:
    if not nvidia_client:
        return ""

    try:
        response = nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert fact-checker with deep knowledge of history, "
                        "science, politics, medicine, and current events. Always respond "
                        "with accurate, factual information and do not fabricate sources."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        text = response.choices[0].message.content
        return text.strip() if text else ""
    except Exception as exc:
        print(f"NVIDIA error: {exc}")
        return ""


def call_ollama(prompt: str, max_tokens: int = 400, temperature: float = 0.1) -> str:
    import requests as req

    try:
        response = req.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "num_ctx": 1024,
                },
                "keep_alive": "10m",
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as exc:
        print(f"Ollama error: {exc}")
        return ""


def call_llm(
    prompt: str,
    max_tokens: int = 600,
    temperature: float = 0.1,
    agent_name: str = "agent",
) -> str:
    start = time.time()
    print(f"[{agent_name}] Calling NVIDIA ({NVIDIA_MODEL})...")

    if USE_NVIDIA and nvidia_client:
        result = call_nvidia(prompt, max_tokens=max_tokens, temperature=temperature)
        if result:
            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] ✅ NVIDIA {elapsed}s")
            return result
        print(f"[{agent_name}] NVIDIA empty/failed, trying Ollama...")

    result = call_ollama(prompt, max_tokens=max_tokens, temperature=temperature)
    elapsed = round(time.time() - start, 1)
    print(f"[{agent_name}] Ollama {elapsed}s")
    return result


def extract_json(text: str) -> dict:
    if not text:
        return {}

    clean = re.sub(r"```(?:json)?\s*", "", text).strip()
    clean = clean.replace("```", "").strip()

    depth = 0
    start_index = -1
    for idx, char in enumerate(clean):
        if char == "{":
            if depth == 0:
                start_index = idx
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start_index >= 0:
                candidate = clean[start_index : idx + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    try:
                        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
                        return json.loads(fixed)
                    except Exception:
                        continue

    return {}


print(f"LLM: {'NVIDIA ✅' if USE_NVIDIA else 'Ollama only ⚠️'}")