"""
llm_client.py - VeritasAI LLM Client - Gemini + Ollama ONLY

Architecture:
  Claim Analyzer     -> Ollama (llama3.2:1b, fast local)
  Prosecutor/Defender -> Gemini (reasoning) -> Ollama fallback
  Judge              -> Gemini (verdict synthesis) -> Ollama fallback
  Retrieval          -> Always local (no LLM calls)
"""

import json
import logging
import os
import re
import time
import traceback

import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger("veritas.llm")

# ============================================================
# GEMINI CONFIGURATION
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

gemini_available = bool(GEMINI_API_KEY and GEMINI_API_KEY != "DISABLED")

# ============================================================
# OLLAMA CONFIGURATION (PRIMARY LOCAL FALLBACK)
# ============================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_ANALYZER_MODEL = os.getenv("OLLAMA_ANALYZER_MODEL", "llama3.2:1b")
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_ENABLED = os.getenv("VERITAS_DISABLE_OLLAMA", "0") != "1"

# Backward-compatible aliases used by legacy modules.
OLLAMA_ANALYZER = OLLAMA_ANALYZER_MODEL
OLLAMA_MODEL = OLLAMA_REASONING_MODEL

# ============================================================
# INIT MESSAGE
# ============================================================
print(f"[LLM] Gemini: {'ready' if gemini_available else 'DISABLED'}")
print(f"[LLM] Ollama: {OLLAMA_BASE_URL} (reasoning={OLLAMA_REASONING_MODEL})")
print(f"[LLM] Stack: Gemini={'yes' if gemini_available else 'no'} | Ollama=yes")


# ============================================================
# OLLAMA FUNCTION (UNIVERSAL FALLBACK)
# ============================================================
def call_ollama(
    prompt: str,
    *args,
    temperature: float = 0.2,
    max_tokens: int = 400,
    model: str = None,
    agent_name: str = "Agent",
    timeout_seconds: int = 20,
    num_predict: int | None = None,
    num_ctx: int | None = None,
    **kwargs,
) -> str:
    """Call Ollama locally."""
    # Preserve the old positional signature used by the legacy agents.
    legacy_args = list(args)
    if legacy_args:
        if len(legacy_args) >= 1:
            temperature = legacy_args[0]
        if len(legacy_args) >= 2:
            max_tokens = legacy_args[1]
        if len(legacy_args) >= 3:
            timeout_seconds = legacy_args[2]
        if len(legacy_args) >= 4:
            model = legacy_args[3]
        if len(legacy_args) >= 5:
            agent_name = legacy_args[4]
        if len(legacy_args) >= 6:
            timeout_seconds = legacy_args[5]

    if kwargs.get("num_predict") is not None:
        num_predict = kwargs["num_predict"]
    if kwargs.get("num_ctx") is not None:
        num_ctx = kwargs["num_ctx"]

    use_model = model or OLLAMA_ANALYZER_MODEL
    token_budget = num_predict if num_predict is not None else max_tokens
    print(f"\n[{agent_name}] -> Ollama ({use_model})")
    start_time = time.time()

    try:
        if not OLLAMA_ENABLED:
            LOGGER.warning("[%s] Ollama fallback disabled", agent_name)
            return ""

        response = http_requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": use_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": token_budget,
                    "num_ctx": num_ctx or 2048,
                    "repeat_penalty": 1.1,
                },
                "keep_alive": "10m",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        elapsed = round(time.time() - start_time, 1)
        print(f"[{agent_name}] Ollama OK {elapsed}s")
        return text
    except http_requests.exceptions.Timeout:
        print(f"[{agent_name}] Ollama timeout after {timeout_seconds}s")
        LOGGER.warning("[%s] Ollama timeout after %ss", agent_name, timeout_seconds)
        return ""
    except Exception as exc:
        print(f"[{agent_name}] Ollama error: {exc}")
        LOGGER.exception("[%s] FULL ERROR TRACE", agent_name)
        return ""


# ============================================================
# GEMINI FUNCTION (PRIMARY FOR REASONING)
# ============================================================
def call_gemini(
    prompt: str,
    max_tokens: int = 600,
    temperature: float = 0.3,
    agent_name: str = "Agent",
    timeout_seconds: int = 30,
) -> str:
    """Call Google Gemini API."""
    if not gemini_available:
        print(f"[{agent_name}] Gemini not available, skipping")
        return ""

    print(f"\n[{agent_name}] -> Gemini ({GEMINI_MODEL})")
    start_time = time.time()

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            },
            request_options={"timeout": timeout_seconds},
        )

        text = response.text.strip() if response.text else ""
        elapsed = round(time.time() - start_time, 1)
        print(f"[{agent_name}] Gemini OK {elapsed}s")
        return text

    except Exception as exc:
        elapsed = round(time.time() - start_time, 1)
        print(f"[{agent_name}] Gemini error ({elapsed}s): {str(exc)[:80]}")
        LOGGER.exception("[%s] FULL ERROR TRACE", agent_name)
        return ""


# ============================================================
# UNIFIED REASONING CALL (Gemini with Ollama fallback)
# ============================================================
def call_reasoning(
    prompt: str,
    max_tokens: int = 700,
    agent_name: str = "Agent",
) -> str:
    """
    Call Gemini for reasoning tasks (prosecutor, defender, judge).
    Falls back to Ollama if Gemini fails or unavailable.
    """
    if gemini_available:
        result = call_gemini(
            prompt,
            max_tokens=max_tokens,
            temperature=0.2,
            agent_name=agent_name,
            timeout_seconds=30,
        )
        if result and len(result) > 20:
            return result
        print(f"[{agent_name}] Gemini failed or empty, trying Ollama fallback")

    print(f"[{agent_name}] Fallback -> Ollama ({OLLAMA_REASONING_MODEL})")
    return call_ollama(
        prompt,
        temperature=0.2,
        max_tokens=max_tokens,
        model=OLLAMA_REASONING_MODEL,
        agent_name=agent_name,
        timeout_seconds=25,
    )

# Legacy aliases for compatibility with old code
def call_deepseek(prompt: str, max_tokens: int = 1000, agent_name: str = "Prosecutor") -> str:
    """Deprecated: redirects to call_reasoning for Prosecutor."""
    return call_reasoning(prompt, max_tokens, agent_name)

def call_groq(prompt: str, model: str = None, max_tokens: int = 800, agent_name: str = "Agent") -> str:
    """Deprecated: redirects to call_reasoning for Defender/Judge."""
    return call_reasoning(prompt, max_tokens, agent_name)

def call_with_fallback(prompt: str, primary_model: str, max_tokens: int = 600, agent_name: str = "Agent") -> str:
    """Deprecated: redirects to call_reasoning."""
    return call_reasoning(prompt, max_tokens, agent_name)



# ============================================================
# JSON EXTRACTOR
# ============================================================
def extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown and reasoning blocks."""
    if not text:
        return {}

    # Remove markdown code blocks
    clean = re.sub(r"```(?:json)?\s*", "", text)
    clean = clean.replace("```", "").strip()

    # Remove thinking tags
    clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL).strip()

    # Try direct JSON parse
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Try extracting JSON object
    depth = 0
    start = -1
    for idx, char in enumerate(clean):
        if char == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = clean[start : idx + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    try:
                        # Fix trailing commas
                        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
                        return json.loads(fixed)
                    except Exception:
                        pass

    # Extract fields manually as last resort
    result = {}
    for verdict in ["FALSE", "TRUE", "MISLEADING", "UNVERIFIED"]:
        if f'"{verdict}"' in text or f": {verdict}" in text:
            result["verdict"] = verdict
            break

    nums = re.findall(r'"confidence"\s*:\s*(\d+)', text)
    if nums:
        result["confidence"] = int(nums[0])

    return result


# ============================================================
# HEALTH CHECK
# ============================================================
def test_all_connections() -> dict:
    """Test all available LLM connections."""
    status = {
        "gemini": {
            "status": "ready" if gemini_available else "disabled",
            "model": GEMINI_MODEL if gemini_available else "N/A",
        },
        "ollama": {
            "status": "unknown",
            "model": OLLAMA_REASONING_MODEL,
        },
        "newsapi": {
            "status": "configured" if os.getenv("NEWSAPI_KEY") else "missing"
        },
        "serpapi": {"status": "configured" if os.getenv("SERPAPI_KEY") else "missing"},
    }

    # Test Gemini
    if gemini_available:
        test_result = call_gemini(
            'Respond with valid JSON only: {"status":"ok"}',
            max_tokens=30,
            agent_name="HealthCheck",
        )
        if test_result:
            status["gemini"]["status"] = "ready"
        else:
            status["gemini"]["status"] = "unreachable"

    # Test Ollama
    test_result = call_ollama(
        'Respond with: {"status":"ok"}',
        max_tokens=30,
        agent_name="HealthCheck",
    )
    status["ollama"]["status"] = "ready" if test_result else "unreachable"

    return status
