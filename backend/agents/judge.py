import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"
REQUEST_TIMEOUT = 120
MAX_RETRIES = 2

FALLBACK = {
    "verdict": "UNVERIFIED",
    "confidence": 35,
    "reasoning": "Analysis timed out. Please retry.",
    "key_evidence": [],
    "recommendation": "Retry the claim for full analysis"
}

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
                print(f"Judge fallback: Ollama call failed after {retries} attempt(s): {e}")
                return ""
    return ""

def judge(claim: str, prosecutor_result: dict, defender_result: dict, avg_credibility: float) -> dict:
    prosecutor_points = prosecutor_result.get("arguments", [])[:3]
    defender_points = defender_result.get("arguments", [])[:3]

    prompt = f"""You are a judge. Evaluate these arguments about a claim.
Claim: {claim}
Against: {prosecutor_points}
For: {defender_points}
Source credibility avg: {round(avg_credibility, 2)}

Return ONLY this JSON, no other text:
{{
  "verdict": "TRUE|FALSE|MISLEADING|UNVERIFIED",
  "confidence": <number 30-97, never exactly 60>,
  "reasoning": "<2 sentences max>",
  "key_evidence": ["<point1>", "<point2>"],
  "recommendation": "<1 sentence>"
}}

Confidence rules:
- Strong contradicting evidence + high credibility = 75-95
- Weak evidence either side = 45-65
- No clear evidence = 30-44
- NEVER return exactly 60"""

    response = call_ollama(prompt)
    if not response:
        return FALLBACK

    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            result = json.loads(response[start:end])
            result['verdict'] = result.get('verdict', 'UNVERIFIED').upper()

            allowed = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
            if result['verdict'] not in allowed:
                result['verdict'] = 'UNVERIFIED'

            conf = int(result.get('confidence', 35))
            if conf == 60:
                if avg_credibility >= 0.7:
                    conf = 72
                elif avg_credibility >= 0.5:
                    conf = 58
                else:
                    conf = 42

            result['confidence'] = max(30, min(97, conf))
            result['reasoning'] = str(result.get('reasoning', FALLBACK['reasoning']))[:220]
            key_evidence = result.get('key_evidence', [])
            if not isinstance(key_evidence, list):
                key_evidence = []
            result['key_evidence'] = [str(x)[:180] for x in key_evidence[:2]]
            result['recommendation'] = str(result.get('recommendation', FALLBACK['recommendation']))[:180]
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    return FALLBACK

# Alias for external test compatibility
run_judge = judge
