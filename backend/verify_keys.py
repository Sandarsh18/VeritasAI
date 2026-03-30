import os, requests
from dotenv import load_dotenv
load_dotenv()

print("="*50)
print("API KEY VERIFICATION")
print("="*50)

# Test Gemini
GEMINI_KEY = os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    resp = model.generate_content(
        'Return only: {"ok":true}')
    print(f"✅ Gemini: WORKING — {resp.text[:40]}")
except Exception as e:
    print(f"❌ Gemini: FAILED — {e}")

# Test Grok
GROK_KEY = os.getenv("GROK_API_KEY","")
try:
    model_candidates = [
        os.getenv("GROK_MODEL", "grok-beta"),
        "grok-3-mini",
        "grok-3-latest",
        "grok-2-latest",
    ]
    tried = []
    worked = False
    for model_name in model_candidates:
        if model_name in tried:
            continue
        tried.append(model_name)

        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROK_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": 'Return only: {"ok":true}'}],
                "max_tokens": 30,
                "temperature": 0
            },
            timeout=30
        )
        if resp.status_code >= 400:
            print(f"⚠️  Grok model {model_name} failed: {resp.status_code} {resp.text[:120]}")
            continue

        raw = (resp.json().get("choices", [{}])[0]
               .get("message", {})
               .get("content", ""))
        print(f"✅ Grok: WORKING ({model_name}) — {raw[:40]}")
        worked = True
        break

    if not worked:
        print("❌ Grok: FAILED — no accessible model for this API key")
except Exception as e:
    print(f"❌ Grok: FAILED — {e}")

# Test NewsAPI
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY","")
try:
    r = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={"apiKey":NEWSAPI_KEY,"country":"in",
                "pageSize":1},
        timeout=10
    )
    data = r.json()
    if data.get("status") == "ok":
        print(f"✅ NewsAPI: WORKING — "
              f"{data.get('totalResults')} articles")
    else:
        print(f"❌ NewsAPI: {data.get('message')}")
except Exception as e:
    print(f"❌ NewsAPI: FAILED — {e}")

# Test SerpAPI
SERPAPI_KEY = os.getenv("SERPAPI_KEY","")
if SERPAPI_KEY:
    try:
        from serpapi import GoogleSearch
        s = GoogleSearch({
            "q": "gold price india",
            "api_key": SERPAPI_KEY, "num": 1
        })
        r = s.get_dict()
        if r.get("organic_results"):
            print(f"✅ SerpAPI: WORKING")
        else:
            print(f"⚠️  SerpAPI: No results "
                  f"(key may be invalid)")
    except Exception as e:
        print(f"❌ SerpAPI: FAILED — {e}")
else:
    print("⚠️  SerpAPI: KEY NOT SET in .env")

print("="*50)
