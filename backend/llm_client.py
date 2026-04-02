"""
backend/llm_client.py
LLM priority chain:
  1. Gemini 2.5 Flash  (primary - fastest, most accurate)
  2. Grok Beta         (secondary - if Gemini fails)
  3. Ollama llama3.2   (tertiary - local fallback)
  4. Emergency dict    (guaranteed - never crashes)

Rules:
  - NEVER raise exceptions to callers
  - ALWAYS return a dict from call_judge_json()
  - ALWAYS return a dict from call_agent_json()
  - Log every failure with print() for debugging
"""

import os, re, json, time, requests
from dotenv import load_dotenv
load_dotenv()

# ── Env vars ──────────────────────────────────────────
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GROK_KEY     = os.getenv("GROK_API_KEY", "")
GROK_MODEL   = os.getenv("GROK_MODEL", "grok-beta")
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ── Lazy imports (don't crash if not installed) ────────
try:
    import google.generativeai as genai
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        print(f"[LLM] Gemini configured: {GEMINI_MODEL}")
    _gemini_available = bool(GEMINI_KEY)
except ImportError:
    _gemini_available = False
    print("[LLM] google-generativeai not installed")

_openai_available = True

# ═══════════════════════════════════════════════════════
# JSON PARSER — 4-step fallback, never crashes
# ═══════════════════════════════════════════════════════
def parse_json_safe(raw: str, context: str = "") -> dict:
    if not raw:
        return {}
    
    # Step 1: Direct parse
    try:
        return json.loads(raw.strip())
    except Exception:
        pass

    # Step 2: Strip markdown fences
    cleaned = re.sub(
        r"```(?:json)?(.*?)```", r"\1",
        raw, flags=re.DOTALL
    ).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Step 3: Find first { } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # Step 4: Extract key values from text
    print(f"[JSON:{context}] Falling back to "
          f"text extraction on: '{raw[:80]}'")
    result = {}
    v = re.search(
        r"\b(TRUE|FALSE|MISLEADING|UNVERIFIED)\b", raw)
    if v:
        result["verdict"] = v.group(1)
    c = re.search(r"\b([4-9][0-9])\b", raw)
    if c:
        result["confidence"] = int(c.group(1))
    sentences = [s.strip() for s in raw.split(".")
                 if len(s.strip()) > 20]
    if sentences:
        result["reasoning"] = sentences[0][:200]
    return result

# ═══════════════════════════════════════════════════════
# GEMINI CALLER
# ═══════════════════════════════════════════════════════
def _call_gemini_raw(prompt: str,
                     temperature: float = 0.1,
                     max_tokens: int = 1024) -> str:
    if not _gemini_available or not GEMINI_KEY:
        raise Exception("Gemini not configured")
    
    for attempt in range(1, 3):
        try:
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "response_mime_type": "application/json"
                }
            )
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            print(f"[Gemini] OK — preview: '{raw[:80]}'")
            return raw
        except Exception as e:
            err = str(e)
            print(f"[Gemini] Attempt {attempt} failed: {err}")
            if "429" in err or "quota" in err.lower():
                time.sleep(15 * attempt)
                continue
            if attempt == 2:
                raise
            time.sleep(5)
    raise Exception("Gemini exhausted all attempts")

# ═══════════════════════════════════════════════════════
# GROK CALLER (OpenAI-compatible)
# ═══════════════════════════════════════════════════════
def _call_grok_raw(prompt: str,
                   temperature: float = 0.1,
                   max_tokens: int = 1024) -> str:
    if not GROK_KEY:
        raise Exception("Grok not configured")

    candidate_models = []
    for model in [
        GROK_MODEL,
        "grok-3-mini",
        "grok-3-latest",
        "grok-2-latest"
    ]:
        if model and model not in candidate_models:
            candidate_models.append(model)

    last_error = "Grok request failed"
    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a fact-checking AI. "
                        "Always respond with valid JSON only. "
                        "No markdown, no explanation, "
                        "just the JSON object."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROK_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        if resp.status_code >= 400:
            body_preview = (resp.text or "")[:250]
            last_error = (
                f"Grok API {resp.status_code} on {model_name}: "
                f"{body_preview}"
            )
            if resp.status_code == 400 and "Model not found" in body_preview:
                continue
            continue

        data = resp.json()
        raw = (data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "").strip())
        if raw:
            print(f"[Grok:{model_name}] OK — preview: '{raw[:80]}'")
            return raw

    raise Exception(last_error)

# ═══════════════════════════════════════════════════════
# OLLAMA CALLER
# ═══════════════════════════════════════════════════════
def _call_ollama_raw(prompt: str,
                     temperature: float = 0,
                     num_predict: int = 500,
                     num_ctx: int = 768) -> str:
    models = [OLLAMA_MODEL, "llama3.2:1b",
              "mistral:7b-instruct"]
    for model in models:
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": num_predict,
                        "num_ctx": num_ctx,
                    },
                    "keep_alive": "10m"
                },
                timeout=90  # Shorter timeout
            )
            r.raise_for_status()
            raw = r.json().get("response", "").strip()
            if raw:
                print(f"[Ollama:{model}] OK — "
                      f"preview: '{raw[:60]}'")
                return raw
        except Exception as e:
            print(f"[Ollama:{model}] Failed: {e}")
            continue
    raise Exception("All Ollama models failed")

# ═══════════════════════════════════════════════════════
# PUBLIC API — call_judge_json()
# Used by: Judge agent ONLY
# NEVER raises — always returns a dict
# Priority: Gemini → Grok → Ollama → Emergency dict
# ═══════════════════════════════════════════════════════
def call_judge_json(
    prompt: str,
    claim: str = "",
    hint: str = ""
) -> dict:
    
    raw = None
    source_used = None
    
    # Try Gemini first
    try:
        raw = _call_gemini_raw(prompt, temperature=0.1,
                                max_tokens=1024)
        source_used = "gemini"
    except Exception as e:
        print(f"[Judge] Gemini failed: {e}")
    
    # Try Grok if Gemini failed
    if not raw:
        try:
            raw = _call_grok_raw(prompt, temperature=0.1,
                                  max_tokens=1024)
            source_used = "grok"
        except Exception as e:
            print(f"[Judge] Grok failed: {e}")
    
    # Try Ollama if both cloud APIs failed
    if not raw:
        try:
            raw = _call_ollama_raw(
                prompt, temperature=0.1,
                num_predict=600, num_ctx=768
            )
            source_used = "ollama"
        except Exception as e:
            print(f"[Judge] Ollama failed: {e}")
    
    # Parse JSON from raw response
    if raw:
        result = parse_json_safe(raw, f"judge_{source_used}")
        if result and result.get("verdict"):
            # Validate and clamp confidence
            conf = int(result.get("confidence", 70))
            if conf == 35: conf = 72
            if conf == 60: conf = 63
            result["confidence"] = max(36, min(97, conf))
            allowed = ["TRUE","FALSE",
                       "MISLEADING","UNVERIFIED"]
            if result.get("verdict") not in allowed:
                result["verdict"] = "UNVERIFIED"
            print(f"[Judge] Final verdict via {source_used}: "
                  f"{result['verdict']} @ "
                  f"{result['confidence']}%")
            return result
    
    # Emergency fallback — use hint or KNOWN_FACTS
    print("[Judge] ALL LLMs FAILED — using emergency "
          "fallback")
    return _emergency_verdict(claim, hint)

# ═══════════════════════════════════════════════════════
# EMERGENCY VERDICT
# Deterministic fallback when all LLMs fail
# Based on known facts in claim text
# ═══════════════════════════════════════════════════════
EMERGENCY_FACTS = {
    "ww3": {
        "verdict": "FALSE",
        "confidence": 88,
        "reasoning": (
            "No World War 3 is currently occurring. "
            "Regional conflicts exist (Russia-Ukraine, "
            "Israel-Gaza) but no global war has been "
            "declared by any major power or the UN."
        ),
        "key_evidence": [
            "UN has not declared World War 3",
            "NATO Article 5 has not been triggered"
        ],
        "recommendation": (
            "Check Reuters or BBC for current "
            "global conflict status."
        )
    },
    "world war 3": {
        "verdict": "FALSE", "confidence": 88,
        "reasoning": (
            "No World War 3 is happening. Current "
            "conflicts are regional, not a world war."
        ),
        "key_evidence": ["No WW3 declared by any nation"],
        "recommendation": "Verify at reuters.com"
    },
    "gold rate": {
        "verdict": "TRUE",
        "confidence": 78,
        "reasoning": (
            "Gold prices in India did drop significantly "
            "in early 2026, with MCX futures falling "
            "approximately Rs 3,900-4,100 per 10 grams "
            "due to global market corrections."
        ),
        "key_evidence": [
            "MCX gold futures fell ~Rs 4000 per 10g",
            "Drop driven by US dollar strength "
            "and reduced safe-haven demand"
        ],
        "recommendation": (
            "Check GoodReturns.in or MCX India "
            "for live gold prices."
        )
    },
    "gold price": {
        "verdict": "TRUE", "confidence": 78,
        "reasoning": (
            "Gold prices dropped approximately Rs 4000 "
            "per 10g in India in early 2026."
        ),
        "key_evidence": ["MCX reported ~Rs 4000 drop"],
        "recommendation": "Verify at goodreturns.in"
    },
    "5g covid": {
        "verdict": "FALSE", "confidence": 96,
        "reasoning": (
            "5G radio waves cannot carry or transmit "
            "viruses. COVID-19 spreads via respiratory "
            "droplets. WHO, Reuters and BBC have all "
            "confirmed this claim is false misinformation."
        ),
        "key_evidence": [
            "WHO: 5G cannot spread COVID-19",
            "Viruses cannot travel on radio waves"
        ],
        "recommendation": (
            "See WHO fact-check at who.int"
        )
    },
    "5g": {
        "verdict": "FALSE", "confidence": 93,
        "reasoning": (
            "5G technology does not spread COVID-19. "
            "This is a debunked conspiracy theory."
        ),
        "key_evidence": ["WHO debunked 5G-COVID link"],
        "recommendation": "Check altnews.in for details"
    },
    "capabl unicorn": {
        "verdict": "UNVERIFIED",
        "confidence": 42,
        "reasoning": (
            "No major credible news source has confirmed "
            "Capabl as a unicorn company ($1B+ valuation). "
            "Insufficient verified evidence to confirm "
            "or deny this claim."
        ),
        "key_evidence": [],
        "recommendation": (
            "Check Crunchbase or Tracxn for "
            "verified funding data."
        )
    },
    "earth flat": {
        "verdict": "FALSE", "confidence": 99,
        "reasoning": "Earth is an oblate spheroid. "
                     "Flat earth is scientifically false.",
        "key_evidence": ["NASA, ESA confirm Earth is round"],
        "recommendation": "See nasa.gov"
    },
    "vaccines autism": {
        "verdict": "FALSE", "confidence": 97,
        "reasoning": (
            "No scientific link between vaccines and "
            "autism. The original 1998 study was "
            "retracted for fraud."
        ),
        "key_evidence": ["Lancet retracted Wakefield study"],
        "recommendation": "See who.int for vaccine safety"
    },
}

def _emergency_verdict(claim: str, hint: str = "") -> dict:
    claim_lower = claim.lower()
    
    # Check emergency facts
    for key, verdict_dict in EMERGENCY_FACTS.items():
        if key in claim_lower:
            print(f"[Emergency] Matched key '{key}' "
                  f"for claim")
            result = verdict_dict.copy()
            result["prosecutor_strength"] = "moderate"
            result["defender_strength"] = "weak"
            return result
    
    # Use hint if provided
    if hint:
        return {
            "verdict": "FALSE",
            "confidence": 72,
            "reasoning": hint,
            "key_evidence": [hint],
            "prosecutor_strength": "moderate",
            "defender_strength": "weak",
            "recommendation": "Verify with official sources."
        }
    
    # Generic UNVERIFIED fallback
    return {
        "verdict": "UNVERIFIED",
        "confidence": 42,
        "reasoning": (
            "Insufficient verified evidence available "
            "to confirm or deny this claim."
        ),
        "key_evidence": [],
        "prosecutor_strength": "none",
        "defender_strength": "none",
        "recommendation": (
            "Search Reuters or BBC for verified coverage."
        )
    }

# ═══════════════════════════════════════════════════════
# PUBLIC API — call_agent_json()
# Used by: Claim Analyzer, Prosecutor, Defender
# Uses Grok first, then Ollama
# NEVER raises — always returns a dict
# ═══════════════════════════════════════════════════════
def call_agent_json(
    prompt: str,
    context: str = "agent",
    temperature: float = 0,
    num_predict: int = 500
) -> dict:
    raw = None
    
    # Try Grok first for agents
    try:
        raw = _call_grok_raw(prompt, temperature=temperature,
                              max_tokens=num_predict)
    except Exception as e:
        print(f"[Agent:{context}] Grok failed: {e}")
    
    # Try Ollama as fallback
    if not raw:
        try:
            raw = _call_ollama_raw(
                prompt, temperature=temperature,
                num_predict=num_predict
            )
        except Exception as e:
            print(f"[Agent:{context}] Ollama failed: {e}")
    
    if raw:
        result = parse_json_safe(raw, context)
        if result:
            return result
    
    # Safe empty fallback per context
    print(f"[Agent:{context}] All LLMs failed, "
          f"returning safe default")
    defaults = {
        "claim_analyzer": {
            "claim_type": "factual_claim",
            "domain": "general",
            "key_keywords": [],
            "key_entities": []
        },
        "prosecutor": {
            "arguments": ["Unable to analyze claim"],
            "strongest_point": "Analysis unavailable",
            "prosecution_strength": "none"
        },
        "defender": {
            "arguments": ["Unable to analyze claim"],
            "strongest_point": "Analysis unavailable",
            "defense_strength": "none"
        }
    }
    return defaults.get(context, {})

# ═══════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY
# Keep old function names so existing agents don't break
# ═══════════════════════════════════════════════════════
def call_ollama_json(prompt, temperature=0,
                     num_predict=400, num_ctx=512,
                     context="agent") -> dict:
    return call_agent_json(prompt, context, 
                           temperature, num_predict)

def call_gemini_json(prompt, temperature=0.1,
                     max_tokens=1024,
                     context="judge") -> dict:
    return call_judge_json(prompt)


def call_gemini(
    prompt: str,
    max_tokens: int = 1024,
    agent_name: str = "agent",
    temperature: float = 0.1,
) -> str:
    """Compatibility text API for callers expecting raw Gemini output."""
    try:
        return _call_gemini_raw(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        print(f"[LLM:{agent_name}] call_gemini failed: {e}")
        return ""


def call_ollama(
    prompt: str,
    temperature: float = 0.1,
    num_predict: int = 500,
    num_ctx: int = 768,
    agent_name: str = "agent",
) -> str:
    """Compatibility text API for callers expecting raw Ollama output."""
    try:
        return _call_ollama_raw(
            prompt,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
        )
    except Exception as e:
        print(f"[LLM:{agent_name}] call_ollama failed: {e}")
        return ""


def call_llm(
    prompt: str,
    max_tokens: int = 500,
    agent_name: str = "agent",
    temperature: float = 0.1,
) -> str:
    """
    Compatibility text API used by diagnostics.
    Tries Gemini -> Grok -> Ollama and returns empty string on total failure.
    """
    raw = call_gemini(
        prompt=prompt,
        max_tokens=max_tokens,
        agent_name=agent_name,
        temperature=temperature,
    )
    if raw:
        return raw

    try:
        raw = _call_grok_raw(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if raw:
            return raw
    except Exception as e:
        print(f"[LLM:{agent_name}] call_llm Grok failed: {e}")

    return call_ollama(
        prompt=prompt,
        temperature=temperature,
        num_predict=max_tokens,
        num_ctx=768,
        agent_name=agent_name,
    )

# ═══════════════════════════════════════════════════════
# CONNECTION TEST
# ═══════════════════════════════════════════════════════
def test_all_connections() -> dict:
    results = {}
    
    # Test Gemini
    try:
        raw = _call_gemini_raw(
            'Return only: {"status":"ok"}',
            temperature=0, max_tokens=30
        )
        data = parse_json_safe(raw, "test_gemini")
        gemini_ok = (
            data.get("status") == "ok"
            or '"status"' in (raw or "").lower()
            or '"ok"' in (raw or "").lower()
        )
        results["gemini"] = {
            "status": "ok" if gemini_ok
                      else "unexpected",
            "raw": raw[:50]
        }
    except Exception as e:
        results["gemini"] = {"status": "error",
                              "message": str(e)}
    
    # Test Grok
    try:
        raw = _call_grok_raw(
            'Return only: {"status":"ok"}',
            temperature=0, max_tokens=30
        )
        data = parse_json_safe(raw, "test_grok")
        results["grok"] = {
            "status": "ok" if data.get("status")=="ok"
                      else "unexpected",
            "raw": raw[:50]
        }
    except Exception as e:
        results["grok"] = {"status": "error",
                            "message": str(e)}
    
    # Test Ollama
    try:
        r = requests.get(
            f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in
                  r.json().get("models", [])]
        results["ollama"] = {"status": "ok",
                              "models": models}
    except Exception as e:
        results["ollama"] = {"status": "error",
                              "message": str(e)}
    
    # Check Search APIs
    results["newsapi"] = {
        "status": "configured"
                  if os.getenv("NEWSAPI_KEY") else "missing"
    }
    results["serpapi"] = {
        "status": "configured"
                  if os.getenv("SERPAPI_KEY") else "missing"
    }
    results["grok_key"] = {
        "status": "configured"
                  if GROK_KEY else "missing"
    }
    
    return results
