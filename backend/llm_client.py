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
_gemini_disabled_until = 0.0


def _gemini_finish_reason(response) -> str:
    """Best-effort extraction of the first candidate's finish_reason."""
    try:
        return str(response.candidates[0].finish_reason)
    except Exception:
        return "unknown"


def _safe_gemini_text(response) -> str:
    """Safely extract text from a Gemini response.

    The SDK's ``response.text`` quick-accessor raises a ValueError when the
    candidate contains no Part (e.g. finish_reason=MAX_TOKENS/SAFETY). We walk
    the candidate parts manually so a thinking-only or blocked response degrades
    to an empty string instead of throwing.
    """
    try:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            collected = []
            for part in parts:
                value = getattr(part, "text", "") or ""
                if value:
                    collected.append(value)
            if collected:
                return "".join(collected).strip()
    except Exception:
        pass
    return ""

# ============================================================
# GROQ CONFIGURATION (PRIMARY CLOUD REASONING)
# ============================================================
# Groq offers a fast, reliable free tier and is used as the primary reasoning
# provider for prosecutor/defender/judge. Gemini and Ollama are fallbacks.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_JUDGE_MODEL", "llama-3.3-70b-versatile").strip()
groq_available = bool(GROQ_API_KEY and GROQ_API_KEY != "DISABLED")
_groq_disabled_until = 0.0

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
print(f"[LLM] Groq: {'ready (' + GROQ_MODEL + ')' if groq_available else 'DISABLED'}")
print(f"[LLM] Gemini: {'ready' if gemini_available else 'DISABLED'}")
print(f"[LLM] Ollama: {OLLAMA_BASE_URL} (reasoning={OLLAMA_REASONING_MODEL})")
print(f"[LLM] Stack: Groq={'yes' if groq_available else 'no'} | Gemini={'yes' if gemini_available else 'no'} | Ollama=yes")


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

    def _post_generate(target_model: str) -> http_requests.Response:
        return http_requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": target_model,
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

    try:
        if not OLLAMA_ENABLED:
            LOGGER.warning("[%s] Ollama fallback disabled", agent_name)
            return ""

        response = _post_generate(use_model)
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        elapsed = round(time.time() - start_time, 1)
        print(f"[{agent_name}] Ollama OK {elapsed}s")
        return text
    except http_requests.exceptions.HTTPError as exc:
        response = exc.response
        body = (response.text if response is not None else "")[:300]
        status = response.status_code if response is not None else "n/a"
        missing_model = status == 404 and "not found" in body.lower() and "model" in body.lower()
        fallback_model = OLLAMA_REASONING_MODEL

        if missing_model and fallback_model and use_model != fallback_model:
            LOGGER.warning(
                "[%s] Ollama model '%s' missing; retrying with '%s'",
                agent_name,
                use_model,
                fallback_model,
            )
            try:
                retry_response = _post_generate(fallback_model)
                retry_response.raise_for_status()
                text = retry_response.json().get("response", "").strip()
                elapsed = round(time.time() - start_time, 1)
                print(f"[{agent_name}] Ollama OK {elapsed}s (fallback model={fallback_model})")
                return text
            except Exception:
                LOGGER.exception("[%s] Ollama fallback model call failed", agent_name)

        print(f"[{agent_name}] Ollama error: HTTP {status} {body}")
        LOGGER.exception("[%s] FULL ERROR TRACE", agent_name)
        return ""
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
    global _gemini_disabled_until
    if not gemini_available:
        print(f"[{agent_name}] Gemini not available, skipping")
        return ""

    if time.time() < _gemini_disabled_until:
        LOGGER.warning("[%s] Gemini temporarily disabled after recent quota/rate-limit failure", agent_name)
        return ""

    print(f"\n[{agent_name}] -> Gemini ({GEMINI_MODEL})")
    start_time = time.time()

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        # gemini-2.5-* models spend part of the output-token budget on internal
        # "thinking". With a small budget they can hit MAX_TOKENS (finish_reason=2)
        # before emitting any answer, which surfaces as an empty response. We pad
        # the budget so reasoning agents always have room for real output.
        effective_tokens = max(int(max_tokens), 1024)

        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": effective_tokens,
                "temperature": temperature,
            },
            request_options={"timeout": timeout_seconds},
        )

        text = _safe_gemini_text(response)
        elapsed = round(time.time() - start_time, 1)
        if not text:
            finish = _gemini_finish_reason(response)
            print(f"[{agent_name}] Gemini empty (finish={finish}) in {elapsed}s")
            return ""
        print(f"[{agent_name}] Gemini OK {elapsed}s")
        return text

    except Exception as exc:
        elapsed = round(time.time() - start_time, 1)
        print(f"[{agent_name}] Gemini error ({elapsed}s): {str(exc)[:80]}")
        error_text = str(exc).lower()
        if "quota" in error_text or "resourceexhausted" in error_text or "429" in error_text:
            _gemini_disabled_until = time.time() + int(os.getenv("GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", "3600"))
            LOGGER.warning("[%s] Gemini disabled temporarily because quota/rate limit was hit", agent_name)
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
    Reasoning provider chain for prosecutor/defender/judge:
      1. Groq   (fast, reliable free tier) — primary
      2. Gemini (good reasoning, but free tier rate-limits quickly)
      3. Ollama (local, slow, last resort)
    Returns the first non-empty response.
    """
    if groq_available:
        result = call_groq(prompt, max_tokens=max_tokens, agent_name=agent_name)
        if result and len(result) > 20:
            return result
        print(f"[{agent_name}] Groq failed or empty, trying Gemini")

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
    """Call Groq chat completions. Fast, reliable primary reasoning provider."""
    global _groq_disabled_until
    if not groq_available:
        return ""
    if time.time() < _groq_disabled_until:
        LOGGER.warning("[%s] Groq temporarily disabled after recent rate-limit failure", agent_name)
        return ""

    target_model = model or GROQ_MODEL
    print(f"\n[{agent_name}] -> Groq ({target_model})")
    start_time = time.time()
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        text = (response.choices[0].message.content or "").strip()
        elapsed = round(time.time() - start_time, 1)
        if not text:
            print(f"[{agent_name}] Groq empty in {elapsed}s")
            return ""
        print(f"[{agent_name}] Groq OK {elapsed}s")
        return text
    except Exception as exc:
        elapsed = round(time.time() - start_time, 1)
        print(f"[{agent_name}] Groq error ({elapsed}s): {str(exc)[:80]}")
        error_text = str(exc).lower()
        if "rate" in error_text or "quota" in error_text or "429" in error_text:
            _groq_disabled_until = time.time() + int(os.getenv("GROQ_RATE_LIMIT_COOLDOWN_SECONDS", "120"))
            LOGGER.warning("[%s] Groq disabled temporarily after rate limit", agent_name)
        return ""

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
    """Return cheap provider readiness without generating model output."""
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

    try:
        response = http_requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        status["ollama"]["status"] = "ready" if response.status_code == 200 else "unreachable"
        if response.status_code == 200:
            models = response.json().get("models", [])
            names = [str(item.get("name", "")) for item in models if isinstance(item, dict)]
            status["ollama"]["installed_models"] = [name for name in names if name]
            if OLLAMA_REASONING_MODEL not in status["ollama"]["installed_models"]:
                status["ollama"]["status"] = "model_missing"
    except Exception:
        status["ollama"]["status"] = "unreachable"

    return status
