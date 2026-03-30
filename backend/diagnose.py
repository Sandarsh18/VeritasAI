import requests, json, os
from dotenv import load_dotenv
load_dotenv()

print("=" * 55)
print("VERITASAI DIAGNOSTIC")
print("=" * 55)

# ── Test 1: Ollama ──
print("\n[1] OLLAMA CHECK")
try:
  r = requests.get(
    "http://localhost:11434/api/tags", timeout=5)
  models = r.json().get("models", [])
  names = [m["name"] for m in models]
  print(f"✅ Ollama running")
  print(f"   Models: {names}")
except Exception as e:
  print(f"❌ Ollama unreachable: {e}")

# ── Test 2: Ollama JSON response ──
print("\n[2] OLLAMA JSON TEST (Prosecutor/Defender)")
try:
  r = requests.post(
    "http://localhost:11434/api/generate",
    json={
      "model": "llama3.2:1b",
      "prompt": 'Return ONLY this JSON: '
                '{"status":"working","number":42}',
      "stream": False,
      "options": {"temperature": 0, "num_predict": 50}
    },
    timeout=30
  )
  raw = r.json()["response"]
  print(f"   Raw: '{raw}'")
  parsed = json.loads(raw.strip())
  print(f"✅ Ollama JSON works: {parsed}")
except json.JSONDecodeError:
  print(f"❌ Ollama returned non-JSON: '{raw}'")
  print("   → Prosecutor/Defender will use fallback")
except Exception as e:
  print(f"❌ Ollama call failed: {e}")

# ── Test 3: Gemini API ──
print("\n[3] GEMINI API TEST (Judge)")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv(
  "GEMINI_MODEL", "gemini-1.5-flash")

if not GEMINI_KEY:
  print("❌ GEMINI_API_KEY not found in .env")
else:
  print(f"   Key: {GEMINI_KEY[:12]}...")
  print(f"   Model: {GEMINI_MODEL}")
  try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    resp = model.generate_content(
      'Return ONLY this JSON: '
      '{"verdict":"FALSE","confidence":88,'
      '"reasoning":"sky is blue not green"}'
    )
    raw = resp.text
    print(f"   Raw: '{raw}'")
    parsed = json.loads(
      raw.replace("```json","").replace("```","").strip())
    print(f"✅ Gemini works: verdict={parsed['verdict']}, "
          f"confidence={parsed['confidence']}")
  except Exception as e:
    print(f"❌ Gemini failed: {e}")

# ── Test 4: SerpAPI ──
print("\n[4] SERPAPI TEST")
SERP_KEY = os.getenv("SERPAPI_KEY", "")
if not SERP_KEY:
  print("❌ SERPAPI_KEY not found in .env")
else:
  try:
    r = requests.get(
      "https://serpapi.com/search",
      params={
        "q": "fact check vaccines safety WHO",
        "api_key": SERP_KEY,
        "num": 3,
        "engine": "google"
      },
      timeout=10
    )
    results = r.json().get("organic_results", [])
    print(f"✅ SerpAPI works: {len(results)} results")
    for res in results[:2]:
      print(f"   - {res.get('title','')[:50]}")
      print(f"     {res.get('link','')[:60]}")
  except Exception as e:
    print(f"❌ SerpAPI failed: {e}")

# ── Test 5: NewsAPI ──
print("\n[5] NEWSAPI TEST")
NEWS_KEY = os.getenv("NEWSAPI_KEY", "")
if not NEWS_KEY:
  print("❌ NEWSAPI_KEY not found in .env")
else:
  try:
    r = requests.get(
      "https://newsapi.org/v2/everything",
      params={
        "q": "vaccines safety",
        "apiKey": NEWS_KEY,
        "pageSize": 3,
        "language": "en"
      },
      timeout=10
    )
    data = r.json()
    if data.get("status") == "ok":
      arts = data.get("articles", [])
      print(f"✅ NewsAPI works: {len(arts)} articles")
      for a in arts[:2]:
        print(f"   - {a['title'][:50]}")
        print(f"     {a['url'][:60]}")
    else:
      print(f"❌ NewsAPI error: {data.get('message')}")
  except Exception as e:
    print(f"❌ NewsAPI failed: {e}")

print("\n" + "=" * 55)
print("DIAGNOSIS COMPLETE")
print("=" * 55)
