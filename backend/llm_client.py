"""
llm_client.py
Priority order for Judge:
  1. Gemini (with response_mime_type=application/json)
  2. DeepSeek API
  3. Ollama local fallback
Prosecutor/Defender use Ollama only.
"""

import json
import os
import re
import time

import requests
from dotenv import load_dotenv

# Load backend/.env directly to avoid stdin/find_dotenv edge cases.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Config
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Gemini client
gemini_model = None
if GEMINI_KEY:
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_KEY)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL)
        print(f"[LLM] Gemini ready: {GEMINI_MODEL}")
    except Exception as exc:
        print(f"[LLM] Gemini init failed: {exc}")

# DeepSeek client
deepseek_client = None
if DEEPSEEK_KEY:
    try:
        from openai import OpenAI

        deepseek_client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_URL)
        print(f"[LLM] DeepSeek ready: {DEEPSEEK_MODEL}")
    except Exception as exc:
        print(f"[LLM] DeepSeek init failed: {exc}")


# GEMINI CALL

def call_gemini(prompt: str, max_tokens: int = 800, agent_name: str = "Judge", temperature: float = 0.1) -> str:
    if not gemini_model:
        return ""

    print(f"\n[{agent_name}] -> Gemini ({GEMINI_MODEL})")
    start = time.time()

    for attempt in range(3):
        try:
            resp = gemini_model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )

            finish_name = ""
            if getattr(resp, "candidates", None):
                candidate = resp.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", "")
                finish_name = getattr(finish_reason, "name", str(finish_reason))
                print(f"[{agent_name}] finish_reason: {finish_name}")
                if "SAFETY" in finish_name or "RECITATION" in finish_name:
                    print(f"[{agent_name}] Gemini blocked by policy/recitation")
                    continue

            text = ""
            try:
                text = (resp.text or "").strip()
            except Exception:
                text = ""

            if not text and getattr(resp, "candidates", None):
                parts = []
                for part in getattr(resp.candidates[0].content, "parts", []) or []:
                    part_text = getattr(part, "text", "")
                    if part_text:
                        parts.append(part_text)
                text = "".join(parts).strip()

            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] Gemini raw ({elapsed}s): '{text[:150]}'")

            if text and len(text) > 10:
                return text

            print(f"[{agent_name}] Gemini returned empty, attempt {attempt + 1}/3")
            time.sleep(1)

        except Exception as exc:
            print(f"[{agent_name}] Gemini attempt {attempt + 1} error: {exc}")
            # Quota failures are terminal for this request, skip to fallback quickly.
            if "quota" in str(exc).lower() or "429" in str(exc):
                break
            time.sleep(1.5)

    print(f"[{agent_name}] All Gemini attempts failed")
    return ""


# DEEPSEEK CALL

def call_deepseek(prompt: str, max_tokens: int = 800, agent_name: str = "Judge") -> str:
    if not deepseek_client:
        return ""

    print(f"\n[{agent_name}] -> DeepSeek ({DEEPSEEK_MODEL})")
    start = time.time()

    for attempt in range(2):
        try:
            try:
                resp = deepseek_client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert fact-checking judge. "
                                "Always respond with valid JSON only. "
                                "Never include markdown code blocks. "
                                "Never include text before or after JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
            except Exception:
                # Some deployments ignore/deny response_format.
                resp = deepseek_client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert fact-checking judge. "
                                "Always respond with valid JSON only. "
                                "Never include markdown code blocks. "
                                "Never include text before or after JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.1,
                )

            text = ((resp.choices[0].message.content) or "").strip()
            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] DeepSeek raw ({elapsed}s): '{text[:150]}'")
            if text and len(text) > 10:
                return text
        except Exception as exc:
            print(f"[{agent_name}] DeepSeek attempt {attempt + 1} error: {exc}")
            # Billing issues cannot be retried away.
            if "insufficient balance" in str(exc).lower() or "402" in str(exc):
                break
            time.sleep(1)

    return ""


# OLLAMA CALL

def call_ollama(
    prompt: str,
    temperature: float = 0,
    num_predict: int = 500,
    num_ctx: int = 768,
    agent_name: str = "Agent",
    timeout_seconds: int = 30,
) -> str:
    start = time.time()
    model_candidates = []
    for model_name in [OLLAMA_MODEL, "phi3:latest"]:
        if model_name and model_name not in model_candidates:
            model_candidates.append(model_name)

    for model_name in model_candidates:
        print(f"\n[{agent_name}] -> Ollama ({model_name})")
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": num_predict,
                        "num_ctx": num_ctx,
                        "repeat_penalty": 1.0,
                    },
                    "keep_alive": "10m",
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            text = response.json().get("response", "").strip()
            elapsed = round(time.time() - start, 1)
            print(f"[{agent_name}] Ollama raw ({elapsed}s): '{text[:150]}'")
            if text:
                return text
        except Exception as exc:
            print(f"[{agent_name}] Ollama model {model_name} error: {exc}")

    return ""


# JUDGE CALL

def call_judge_llm(prompt: str, agent_name: str = "Judge") -> str:
    """
    Try Gemini first. If fails or empty -> DeepSeek.
    If DeepSeek fails -> Ollama.
    """
    result = call_gemini(prompt, 800, agent_name)
    if result and _has_verdict(result):
        print(f"[{agent_name}] Using Gemini result")
        return result

    if deepseek_client:
        print(f"[{agent_name}] Gemini failed -> trying DeepSeek")
        result = call_deepseek(prompt, 800, agent_name)
        if result and _has_verdict(result):
            print(f"[{agent_name}] Using DeepSeek result")
            return result

    print(f"[{agent_name}] DeepSeek failed -> trying Ollama")
    result = call_ollama(prompt, 0.1, 180, 768, agent_name, timeout_seconds=20)
    if result:
        print(f"[{agent_name}] Using Ollama result")
        return result

    print(f"[{agent_name}] ALL LLMs failed")
    return ""


def _has_verdict(text: str) -> bool:
    parsed = extract_json(text)
    verdict = str(parsed.get("verdict", "")).upper()
    return verdict in {"TRUE", "FALSE", "MISLEADING", "UNVERIFIED"}


# JSON EXTRACTOR

def extract_json(text: str) -> dict:
    if not text:
        return {}

    clean = re.sub(r"```(?:json)?\s*", "", text)
    clean = clean.replace("```", "").strip()

    try:
        return json.loads(clean)
    except Exception:
        pass

    depth = 0
    start = -1
    for idx, ch in enumerate(clean):
        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}":
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
    text_upper = text.upper()
    for value in ["FALSE", "TRUE", "MISLEADING", "UNVERIFIED"]:
        if f'"{value}"' in text_upper:
            result["verdict"] = value
            break

    nums = re.findall(r'"confidence"\s*:\s*(\d+)', text, flags=re.IGNORECASE)
    if nums:
        result["confidence"] = int(nums[0])

    reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', text, flags=re.IGNORECASE)
    if reasoning_match:
        result["reasoning"] = reasoning_match.group(1)

    return result


# COMPATIBILITY HELPERS

def call_agent_json(prompt: str, context: str = "agent", temperature: float = 0, num_predict: int = 500) -> dict:
    raw = call_ollama(
        prompt=prompt,
        temperature=temperature,
        num_predict=num_predict,
        num_ctx=1024,
        agent_name=context,
    )
    parsed = extract_json(raw)
    if parsed:
        return parsed

    defaults = {
        "claim_analyzer": {
            "claim_type": "factual_claim",
            "domain": "general",
            "key_keywords": [],
            "key_entities": [],
        },
        "prosecutor": {
            "arguments": ["No specific contradicting evidence found"],
            "strongest_point": "No contradictions identified",
            "prosecution_strength": "none",
        },
        "defender": {
            "arguments": ["No specific supporting evidence found"],
            "strongest_point": "No support identified",
            "defense_strength": "none",
        },
    }
    return defaults.get(context, {})


def call_judge_json(prompt: str, claim: str = "", hint: str = "") -> dict:
    raw = call_judge_llm(prompt, "Judge")
    result = extract_json(raw) if raw else {}

    verdict = str(result.get("verdict", "")).upper()
    if verdict in {"TRUE", "FALSE", "MISLEADING", "UNVERIFIED"}:
        confidence = int(result.get("confidence", 65))
        if confidence == 50:
            confidence = 63
        result["verdict"] = verdict
        result["confidence"] = max(36, min(95, confidence))
        return result

    reason = hint or f"Insufficient evidence to verify '{claim}'"
    return {
        "verdict": "UNVERIFIED",
        "confidence": 42,
        "reasoning": reason,
        "key_evidence": [],
        "prosecutor_strength": "none",
        "defender_strength": "none",
        "recommendation": "Search trusted sources for confirmation.",
    }


def call_ollama_json(prompt: str, temperature: float = 0, num_predict: int = 400, num_ctx: int = 512, context: str = "agent") -> dict:
    raw = call_ollama(prompt, temperature, num_predict, num_ctx, context)
    return extract_json(raw)


def call_gemini_json(prompt: str, temperature: float = 0.1, max_tokens: int = 1024, context: str = "judge") -> dict:
    raw = call_gemini(prompt, max_tokens=max_tokens, agent_name=context, temperature=temperature)
    return extract_json(raw)


def call_llm(prompt: str, max_tokens: int = 500, agent_name: str = "agent", temperature: float = 0.1) -> str:
    # Text compatibility API used by diagnostics and legacy callers.
    raw = call_gemini(prompt, max_tokens=max_tokens, agent_name=agent_name, temperature=temperature)
    if raw:
        return raw

    raw = call_deepseek(prompt, max_tokens=max_tokens, agent_name=agent_name)
    if raw:
        return raw

    return call_ollama(prompt, temperature=temperature, num_predict=max_tokens, num_ctx=768, agent_name=agent_name)


def test_all_connections() -> dict:
    results = {}

    # Gemini
    if gemini_model:
        try:
            raw = call_gemini('Return ONLY JSON: {"status":"ok"}', max_tokens=80, agent_name="Health")
            data = extract_json(raw)
            results["gemini"] = {
                "status": "ok" if data.get("status") == "ok" or raw else "unexpected",
                "raw": (raw or "")[:60],
            }
        except Exception as exc:
            results["gemini"] = {"status": "error", "message": str(exc)}
    else:
        results["gemini"] = {"status": "missing"}

    # Keep key for backward compatibility with existing /api/health logic.
    results["grok"] = {"status": "deprecated"}

    # DeepSeek
    if deepseek_client:
        try:
            raw = call_deepseek('Return ONLY JSON: {"status":"ok"}', max_tokens=80, agent_name="Health")
            data = extract_json(raw)
            results["deepseek"] = {
                "status": "ok" if data.get("status") == "ok" or raw else "unexpected",
                "raw": (raw or "")[:60],
            }
        except Exception as exc:
            results["deepseek"] = {"status": "error", "message": str(exc)}
    else:
        results["deepseek"] = {"status": "missing"}

    # Ollama
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=8)
        tags.raise_for_status()
        models = [m.get("name") for m in tags.json().get("models", [])]
        results["ollama"] = {"status": "ok", "models": models}
    except Exception as exc:
        results["ollama"] = {"status": "error", "message": str(exc)}

    results["newsapi"] = {"status": "configured" if os.getenv("NEWSAPI_KEY") else "missing"}
    results["serpapi"] = {"status": "configured" if os.getenv("SERPAPI_KEY") else "missing"}

    return results


print(
    "LLM stack: "
    f"Gemini={'yes' if gemini_model else 'no'} | "
    f"DeepSeek={'yes' if deepseek_client else 'no'} | "
    "Ollama=yes"
)
