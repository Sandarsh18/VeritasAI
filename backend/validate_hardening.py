"""Task 8.5 validation — re-run targeted claims and report hardening fields."""
import json, time, urllib.request

API = "http://localhost:8000/api/verify"
CLAIMS = [
    "Did NEET 2026 paper leak before examination?",
    "Did NEET 2025 paper leak before examination?",
    "Did humans land on the moon?",
    "Is climate change a hoax?",
]


def post(claim):
    body = json.dumps({"claim": claim}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode()), round(time.time() - t0, 1)


for claim in CLAIMS:
    d, dt = post(claim)
    vi = d.get("verdict_insights") or {}
    pros = d.get("prosecutor") or {}
    deff = d.get("defender") or {}
    print("=" * 72)
    print(claim, f"({dt}s)")
    print(f"  verdict            = {d.get('verdict')}")
    print(f"  confidence         = {d.get('confidence')}")
    print(f"  supporting_count   = {d.get('supporting_count')}")
    print(f"  contradicting_count= {d.get('contradicting_count')}")
    print(f"  defender_strength  = {deff.get('defense_strength')}")
    print(f"  prosecutor_strength= {pros.get('prosecution_strength')}")
    print(f"  year_match_score   = {vi.get('year_match_score')}  year_match={vi.get('year_match')}")
    print(f"  judge_reasoning    = {(d.get('judge_reasoning') or d.get('reasoning') or '')[:300]}")
