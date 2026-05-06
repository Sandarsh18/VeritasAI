import os

import requests
from dotenv import load_dotenv


load_dotenv()


def test_gemini_or_ollama_generates_text():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    if key and key != "DISABLED":
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": "Summarize why the sky is blue in one sentence."}
                        ]
                    }
                ]
            },
            timeout=30,
        )
        if response.status_code >= 400:
            print(f"Gemini status={response.status_code}")
            print(response.text)
        assert response.status_code < 400

        payload = response.json()
        candidates = payload.get("candidates") or []
        text = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            if candidates
            else ""
        )
        print(f"Gemini status={response.status_code} text={text[:160]}")
        assert text.strip()
        return

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral:latest")
    response = requests.post(
        f"{ollama_url}/api/generate",
        json={
            "model": ollama_model,
            "prompt": "Summarize why the sky is blue in one sentence.",
            "stream": False,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        print(f"Ollama status={response.status_code}")
        print(response.text)
    assert response.status_code < 400
    text = response.json().get("response", "")
    print(f"Ollama status={response.status_code} text={text[:160]}")
    assert text.strip()

