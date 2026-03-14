import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"
REQUEST_TIMEOUT = 120
MAX_RETRIES = 2

FALLBACK = {
    "arguments": ["No supporting evidence retrieved due to timeout"],
    "strongest_point": "Timeout - unable to analyze"
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
                print(f"Defender fallback: Ollama call failed after {retries} attempt(s): {e}")
                return ""
    return ""

def defend(claim: str, evidence_summary: str) -> dict:
    prompt = (
        "You are a researcher. Find evidence SUPPORTING this claim.\n"
        f"Claim: {claim}\n"
        f"Evidence: {evidence_summary}\n"
        "Return JSON only:\n"
        "{\"arguments\": [\"point1\", \"point2\"], \"strongest_point\": \"summary\"}"
    )

    response = call_ollama(prompt)
    if not response:
        return FALLBACK

    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            args = data.get("arguments") if isinstance(data, dict) else None
            strongest = data.get("strongest_point") if isinstance(data, dict) else None
            if isinstance(args, list) and args:
                return {
                    "arguments": [str(a)[:220] for a in args[:4]],
                    "strongest_point": str(strongest or args[0])[:240]
                }
        except json.JSONDecodeError:
            pass

    lines = [l.strip() for l in response.split('\n') if l.strip() and (l.strip()[0].isdigit() or l.strip().startswith('-'))]
    if lines:
        return {
            "arguments": [l[:220] for l in lines[:4]],
            "strongest_point": lines[0][:240]
        }

    return FALLBACK

# Alias for external test compatibility
run_defender = defend
