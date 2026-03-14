import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"
REQUEST_TIMEOUT = 120
MAX_RETRIES = 2

def call_ollama(prompt: str, retries: int = MAX_RETRIES) -> str:
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {
                        "num_predict": 250,
                        "temperature": 0,
                        "num_ctx": 512,
                        "num_thread": 4,
                        "repeat_penalty": 1.0
                    }
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.Timeout:
            if attempt == retries - 1:
                return ""
        except Exception as e:
            if attempt == retries - 1:
                print(f"Claim analyzer fallback: {e}")
                return ""
    return ""

def analyze_claim(claim: str) -> dict:
    prompt = (
        "Analyze this claim quickly and return JSON only.\n"
        f"Claim: {claim}\n"
        "{\"category\":\"health|politics|science|technology|other\","
        "\"claim_type\":\"factual|statistical|causal|comparative\","
        "\"entities\":[\"item\"],\"keywords\":[\"item\"],"
        "\"complexity\":\"simple|moderate|complex\","
        "\"potential_bias\":\"none|moderate|high\"}"
    )

    response = call_ollama(prompt)
    if not response:
        return {
            "category": "other",
            "claim_type": "factual",
            "entities": [],
            "keywords": claim.split()[:5],
            "complexity": "moderate",
            "potential_bias": "moderate"
        }

    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return {
                "category": parsed.get("category", "other"),
                "claim_type": parsed.get("claim_type", "factual"),
                "entities": parsed.get("entities", [])[:8] if isinstance(parsed.get("entities", []), list) else [],
                "keywords": parsed.get("keywords", [])[:8] if isinstance(parsed.get("keywords", []), list) else claim.split()[:5],
                "complexity": parsed.get("complexity", "moderate"),
                "potential_bias": parsed.get("potential_bias", "moderate"),
            }
        except json.JSONDecodeError:
            pass

    return {
        "category": "other",
        "claim_type": "factual",
        "entities": [],
        "keywords": claim.split()[:5],
        "complexity": "moderate",
        "potential_bias": "moderate"
    }
