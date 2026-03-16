import json
import os
import re
import time

import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() == "true" and bool(GEMINI_KEY)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b").strip()

_gemini_model_instance = None
_gemini_configured = False


def _configure_gemini() -> bool:
    global _gemini_configured

    if _gemini_configured:
        return True

    if not GEMINI_KEY:
        return False

    try:
        genai.configure(api_key=GEMINI_KEY)
        _gemini_configured = True
        return True
    except Exception as exc:
        print(f"Gemini configure failed: {exc}")
        return False


def _normalize_model_name(model_name: str) -> str:
    normalized = (model_name or "").strip()
    if normalized.startswith("models/"):
        return normalized.split("/", 1)[1]
    return normalized


def _list_generation_models() -> list[str]:
    if not _configure_gemini():
        return []

    try:
        available = []
        for model in genai.list_models():
            methods = set(model.supported_generation_methods or [])
            if "generateContent" in methods:
                available.append(_normalize_model_name(model.name))
        return available
    except Exception as exc:
        print(f"Gemini model listing failed: {exc}")
        return []


def _candidate_models() -> list[str]:
    configured = _normalize_model_name(GEMINI_MODEL)
    discovered = _list_generation_models()
    preferred = [
        configured,
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro",
        "gemini-pro-latest",
    ]

    seen = set()
    candidates = []
    for model_name in preferred + discovered:
        normalized = _normalize_model_name(model_name)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
    return candidates


def _find_working_gemini_model() -> str | None:
    if not USE_GEMINI or not _configure_gemini():
        return None

    for model_name in _candidate_models():
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                "Reply with one word: OK",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=5,
                    temperature=0,
                    candidate_count=1,
                ),
            )
            text = getattr(response, "text", "") or ""
            if text.strip():
                print(f"Gemini ready: {model_name}")
                return model_name
        except Exception as exc:
            err = str(exc).lower()
            if "api key" in err or "invalid" in err or "permission" in err:
                print(f"Gemini authentication failed: {exc}")
                return None
            print(f"Gemini model rejected ({model_name}): {str(exc)[:120]}")
    return None


def _get_gemini():
    global GEMINI_MODEL, _gemini_model_instance

    if _gemini_model_instance is not None:
        return _gemini_model_instance

    if not USE_GEMINI:
        print("LLM Client: Gemini disabled or key missing; Ollama fallback only")
        return None

    if not _configure_gemini():
        return None

    working_model = _find_working_gemini_model()
    if not working_model:
        print("LLM Client: no working Gemini model found")
        return None

    GEMINI_MODEL = working_model
    try:
        _gemini_model_instance = genai.GenerativeModel(GEMINI_MODEL)
        return _gemini_model_instance
    except Exception as exc:
        print(f"Gemini init failed: {exc}")
        return None


def call_gemini(prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
    model = _get_gemini()
    if not model:
        return ""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                candidate_count=1,
            ),
        )

        if not getattr(response, "candidates", None):
            print("Gemini response blocked or empty")
            return ""

        text = getattr(response, "text", "") or ""
        return text.strip()
    except Exception as exc:
        print(f"Gemini call error: {exc}")
        return ""


def call_ollama(prompt: str, max_tokens: int = 400, temperature: float = 0.1) -> str:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL,
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
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as exc:
        print(f"Ollama error: {exc}")
        return ""


def call_llm(
    prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.1,
    agent_name: str = "agent",
) -> str:
    start = time.time()

    if USE_GEMINI:
        print(f"[{agent_name}] -> Gemini ({GEMINI_MODEL or 'auto'})")
        result = call_gemini(prompt, max_tokens=max_tokens, temperature=temperature)
        if result:
            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] Gemini success in {elapsed}s")
            return result
        print(f"[{agent_name}] Gemini empty or failed")

    print(f"[{agent_name}] -> Ollama fallback ({OLLAMA_MODEL})")
    result = call_ollama(prompt, max_tokens=max_tokens, temperature=temperature)
    elapsed = round(time.time() - start, 1)
    print(f"[{agent_name}] Ollama finished in {elapsed}s")
    return result


def extract_json(text: str) -> dict:
    if not text:
        return {}

    cleaned = text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start < 0 or end <= start:
        return {}

    candidate = cleaned[start:end]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    try:
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        fixed = re.sub(r"(?<!\\)'([^']*)'(?=\s*:)", r'"\1"', fixed)
        fixed = fixed.replace("\n", " ")
        return json.loads(fixed)
    except Exception:
        return {}


if GEMINI_KEY:
    print("LLM Client: Gemini key loaded")
else:
    print("LLM Client: no Gemini key; Ollama only")