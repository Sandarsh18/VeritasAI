"""
llm_client.py - VeritasAI LLM Client
Architecture:
  Claim Analyzer -> Ollama (llama3.2:1b, fast local)
  Prosecutor     -> DeepSeek-Reasoner (deep reasoning)
  Defender       -> Groq llama-3.1-8b-instant (fast)
  Judge          -> Groq llama-3.3-70b-versatile (smart)
  Fallback chain -> Groq -> Ollama mistral -> logic
"""

import json
import os
import re
import time

import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_DEFENDER_MODEL = os.getenv("GROQ_DEFENDER_MODEL", "llama-3.1-8b-instant")
GROQ_JUDGE_MODEL = os.getenv("GROQ_JUDGE_MODEL", "llama-3.3-70b-versatile")

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_ANALYZER = os.getenv("OLLAMA_ANALYZER_MODEL", "llama3.2:1b")
OLLAMA_FALLBACK = os.getenv("OLLAMA_MODEL", "mistral:latest")

# Init DeepSeek
deepseek_client = None
if DEEPSEEK_KEY and DEEPSEEK_KEY != "DISABLED":
    try:
        from openai import OpenAI

        deepseek_client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_URL)
        print(f"[LLM] DeepSeek ready: {DEEPSEEK_MODEL}")
    except Exception as exc:
        print(f"[LLM] DeepSeek init failed: {exc}")

# Init Groq
groq_client = None
if GROQ_KEY and GROQ_KEY != "DISABLED":
    try:
        from groq import Groq

        groq_client = Groq(api_key=GROQ_KEY)
        print(
            "[LLM] Groq ready: "
            f"defender={GROQ_DEFENDER_MODEL} "
            f"judge={GROQ_JUDGE_MODEL}"
        )
    except Exception as exc:
        print(f"[LLM] Groq init failed: {exc}")

print(
    "LLM Stack: "
    f"DeepSeek={'yes' if deepseek_client else 'no'} | "
    f"Groq={'yes' if groq_client else 'no'} | "
    "Ollama=yes"
)


# OLLAMA - for Claim Analyzer (fast, local)
def call_ollama(
    prompt: str,
    temperature: float = 0,
    num_predict: int = 400,
    num_ctx: int = 512,
    model: str = None,
    agent_name: str = "Analyzer",
    timeout_seconds: int = 20,
) -> str:
    use_model = model or OLLAMA_ANALYZER
    print(f"\n[{agent_name}] -> Ollama ({use_model})")
    start = time.time()

    try:
        response = http_requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": use_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict,
                    "num_ctx": num_ctx,
                    "repeat_penalty": 1.1,
                },
                "keep_alive": "10m",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        elapsed = round(time.time() - start, 1)
        print(f"[{agent_name}] Ollama done {elapsed}s: '{text[:100]}'")
        return text
    except Exception as exc:
        print(f"[{agent_name}] Ollama error: {exc}")
        return ""


# DEEPSEEK - for Prosecutor (deep reasoning)
def call_deepseek(
    prompt: str,
    max_tokens: int = 1000,
    agent_name: str = "Prosecutor",
) -> str:
    if not deepseek_client:
        print(f"[{agent_name}] DeepSeek not available")
        return ""

    print(f"\n[{agent_name}] -> DeepSeek ({DEEPSEEK_MODEL})")
    start = time.time()

    for attempt in range(2):
        try:
            response = deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert fact-checker. "
                            "Respond with valid JSON only. "
                            "No markdown. No explanation outside JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            message = response.choices[0].message
            text = (message.content or "").strip()
            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] DeepSeek done {elapsed}s: '{text[:120]}'")
            if text:
                return text
        except Exception as exc:
            print(f"[{agent_name}] DeepSeek attempt {attempt + 1} error: {exc}")
            if attempt < 1:
                time.sleep(2)

    return ""


# GROQ - for Defender and Judge
def call_groq(
    prompt: str,
    model: str = None,
    max_tokens: int = 800,
    agent_name: str = "Agent",
) -> str:
    if not groq_client:
        print(f"[{agent_name}] Groq not available")
        return ""

    use_model = model or GROQ_JUDGE_MODEL
    print(f"\n[{agent_name}] -> Groq ({use_model})")
    start = time.time()

    for attempt in range(3):
        try:
            response = groq_client.chat.completions.create(
                model=use_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert fact-checking AI. "
                            "Always return valid JSON only. "
                            "Never use markdown code blocks. "
                            "Start your response directly with { "
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            text = (response.choices[0].message.content or "").strip()
            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] Groq done {elapsed}s: '{text[:120]}'")
            if text and len(text) > 5:
                return text
        except Exception as exc:
            err_text = str(exc)
            print(f"[{agent_name}] Groq attempt {attempt + 1} error: {err_text[:100]}")
            if "rate_limit" in err_text.lower() or "429" in err_text:
                wait_seconds = (attempt + 1) * 3
                print(f"[{agent_name}] Rate limited, waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
            elif attempt < 2:
                time.sleep(1)

    return ""


# GROQ FALLBACK -> Ollama
def call_with_fallback(
    prompt: str,
    primary_model: str,
    max_tokens: int = 600,
    agent_name: str = "Agent",
) -> str:
    """
    Try Groq first. If it fails, use Ollama mistral fallback.
    Used for Defender and Judge.
    """
    result = call_groq(prompt, primary_model, max_tokens, agent_name)
    if result and len(result) > 10:
        return result

    print(f"[{agent_name}] Groq failed -> Ollama {OLLAMA_FALLBACK}")
    return call_ollama(
        prompt,
        0.1,
        min(max_tokens, 280),
        768,
        OLLAMA_FALLBACK,
        agent_name,
        timeout_seconds=20,
    )


# JSON EXTRACTOR
def extract_json(text: str) -> dict:
    if not text:
        return {}

    clean = re.sub(r"```(?:json)?\s*", "", text)
    clean = clean.replace("```", "").strip()

    clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL).strip()

    try:
        return json.loads(clean)
    except Exception:
        pass

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
                        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
                        return json.loads(fixed)
                    except Exception:
                        pass

    result = {}
    for verdict in ["FALSE", "TRUE", "MISLEADING", "UNVERIFIED"]:
        if f'"{verdict}"' in text or f': "{verdict}"' in text:
            result["verdict"] = verdict
            break

    nums = re.findall(r'"confidence"\s*:\s*(\d+)', text)
    if nums:
        result["confidence"] = int(nums[0])

    return result


# Compatibility helper kept for existing health check path.
def test_all_connections() -> dict:
    status = {
        "gemini": {"status": "disabled"},
        "deepseek": {"status": "missing"},
        "groq": {"status": "missing"},
        "grok": {"status": "missing"},
        "ollama": {"status": "missing"},
        "newsapi": {"status": "configured" if os.getenv("NEWSAPI_KEY") else "missing"},
        "serpapi": {"status": "configured" if os.getenv("SERPAPI_KEY") else "missing"},
    }

    if deepseek_client:
        raw = call_deepseek(
            'Return ONLY JSON: {"status":"ok"}',
            max_tokens=64,
            agent_name="Health",
        )
        data = extract_json(raw)
        status["deepseek"] = {
            "status": "ok" if data.get("status") == "ok" or bool(raw) else "error",
            "raw": (raw or "")[:80],
        }

    if groq_client:
        raw = call_groq(
            'Return ONLY JSON: {"status":"ok"}',
            model=GROQ_DEFENDER_MODEL,
            max_tokens=64,
            agent_name="Health",
        )
        data = extract_json(raw)
        groq_status = "ok" if data.get("status") == "ok" or bool(raw) else "error"
        status["groq"] = {"status": groq_status, "raw": (raw or "")[:80]}
        status["grok"] = {"status": groq_status, "raw": (raw or "")[:80]}

    try:
        tags = http_requests.get(f"{OLLAMA_URL}/api/tags", timeout=8)
        tags.raise_for_status()
        models = [m.get("name") for m in tags.json().get("models", [])]
        status["ollama"] = {"status": "ok", "models": models}
    except Exception as exc:
        status["ollama"] = {"status": "error", "message": str(exc)}

    return status
