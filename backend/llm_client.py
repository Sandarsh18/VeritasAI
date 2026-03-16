"""
Unified LLM client.
Uses Gemini Flash as primary (smarter, free).
Falls back to Ollama if Gemini fails.
"""

import json
import os
import time

import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() == "true"

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    print(f"✅ Gemini {GEMINI_MODEL} configured")
else:
    gemini_model = None
    print("⚠️  No Gemini key — using Ollama only")


def call_llm(
    prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.1,
    agent_name: str = "agent",
) -> str:
    if USE_GEMINI and gemini_model and GEMINI_KEY:
        try:
            print(f"[{agent_name}] Calling Gemini Flash...")
            start = time.time()
            response = gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            elapsed = round(time.time() - start, 1)
            text = response.text or ""
            print(f"[{agent_name}] Gemini done in {elapsed}s")
            return text
        except Exception as exc:
            print(f"[{agent_name}] Gemini failed: {exc}")
            print(f"[{agent_name}] Falling back to Ollama...")

    try:
        print(f"[{agent_name}] Calling Ollama...")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:1b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "num_ctx": 512,
                },
                "keep_alive": "10m",
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as exc:
        print(f"[{agent_name}] Ollama also failed: {exc}")
        return ""


def extract_json(text: str) -> dict:
    if not text:
        return {}

    cleaned = text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1

    if start >= 0 and end > start:
        candidate = cleaned[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            fixed = candidate.replace("\n", " ").replace("'", '"')
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                return {}
    return {}