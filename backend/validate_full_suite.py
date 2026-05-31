"""Task 8 — Full System Validation Suite (read-only).

Phases:
  1. Full 8-claim suite (metrics)
  2. NEET recent-news stress test (live retrieval, no shortcut)
  3. Edge cases (empty/single-word/long/non-english/typos)
  4. Performance timing
  5. (scoring done in report)
Does NOT modify logic. Writes /tmp/full_suite.json + /tmp/edge_cases.json.
"""

import json
import time
import urllib.request
import urllib.error

API = "http://localhost:8000/api/verify"

SUITE = [
    ("Is India the least populated country in the world?", "FALSE"),
    ("Is Islam older than Hinduism?", "FALSE"),
    ("Is Earth flat?", "FALSE"),
    ("Did humans land on the moon?", "TRUE"),
    ("Is Python a programming language?", "TRUE"),
    ("Is Bangalore the capital of Karnataka?", "TRUE"),
    ("Did NEET 2026 paper leak before examination?", "EVIDENCE_BASED"),
    ("Is climate change a hoax?", "FALSE"),
]

EDGE = [
    ("empty", ""),
    ("single_word", "Python"),
    ("long_paragraph", ("Considering the entire history of space exploration and the many "
                        "missions launched by various nations over several decades, including "
                        "the Apollo program and subsequent crewed and uncrewed missions, is it "
                        "ultimately accurate to assert that human beings have physically walked "
                        "on the surface of the Moon at least once in recorded history?") ),
    ("non_english", "¿Es la Tierra plana?"),
    ("typos", "Did hummans lnad on teh mooon?"),
]


def _post(claim: str, timeout=300):
    body = json.dumps({"claim": claim}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode()), round(time.time() - t0, 1)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}, round(time.time() - t0, 1)
    except Exception as e:
        return -1, {"error": str(e)[:300]}, round(time.time() - t0, 1)


def _provider_counts(meta):
    totals = {"tavily": 0, "serpapi": 0, "newsapi": 0}
    if not isinstance(meta, dict):
        return totals
    if isinstance(meta.get("provider_counts"), dict):
        for k in totals:
            totals[k] = meta["provider_counts"].get(k, 0)
        return totals
    for run in meta.get("api_runs", []) or []:
        for q in run.get("queries", []) or []:
            pc = q.get("provider_counts") or {}
            for k in totals:
                totals[k] += int(pc.get(k, 0) or 0)
    return totals


def run_suite():
    rows = []
    for claim, expected in SUITE:
        print(f"\n{'='*72}\n{claim}  (expected {expected})")
        status, d, dt = _post(claim)
        if status != 200:
            print(f"  HTTP {status}: {d.get('error','')[:120]}")
            rows.append({"claim": claim, "expected": expected, "http": status, "error": d.get("error")})
            continue
        ev = d.get("evidence") or []
        pros = d.get("prosecutor") or {}
        deff = d.get("defender") or {}
        meta = d.get("retrieval_meta") or {}
        pc = _provider_counts(meta)
        mode = meta.get("mode") or ("curated_fact_base" if d.get("cache_source") == "curated_fact_base" else "live")
        row = {
            "claim": claim, "expected": expected,
            "verdict": d.get("verdict"), "confidence": d.get("confidence"),
            "evidence_count": len(ev),
            "tavily": pc["tavily"], "serpapi": pc["serpapi"], "newsapi": pc["newsapi"],
            "def_args": len(deff.get("arguments") or []),
            "pros_args": len(pros.get("arguments") or []),
            "def_strength": deff.get("defense_strength"),
            "pros_strength": pros.get("prosecution_strength"),
            "sources": [e.get("source") for e in ev],
            "judge_reasoning": (d.get("judge_reasoning") or d.get("reasoning") or "")[:240],
            "mode": mode,
            "cache_source": d.get("cache_source"),
            "time_s": dt,
            "processing_time_seconds": d.get("processing_time_seconds"),
            "supporting_count": d.get("supporting_count"),
            "contradicting_count": d.get("contradicting_count"),
        }
        rows.append(row)
        print(f"  verdict={row['verdict']} conf={row['confidence']} ev={row['evidence_count']} "
              f"providers(t/s/n)={pc['tavily']}/{pc['serpapi']}/{pc['newsapi']} "
              f"def={row['def_args']} pros={row['pros_args']} mode={mode} time={dt}s")
        print(f"  sources={row['sources']}")
        print(f"  judge: {row['judge_reasoning'][:160]}")
    json.dump(rows, open("/tmp/full_suite.json", "w"), indent=2)
    return rows


def run_edge():
    rows = []
    for name, claim in EDGE:
        print(f"\n[EDGE] {name}: {claim[:50]!r}")
        status, d, dt = _post(claim, timeout=180)
        ok = status in (200, 400, 422)
        row = {
            "case": name, "http": status, "ok_no_crash": ok, "time_s": dt,
            "verdict": d.get("verdict") if isinstance(d, dict) else None,
            "error": (d.get("error") if isinstance(d, dict) else None),
        }
        rows.append(row)
        print(f"  HTTP {status} time={dt}s verdict={row['verdict']} err={str(row['error'])[:80]}")
    json.dump(rows, open("/tmp/edge_cases.json", "w"), indent=2)
    return rows


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "suite"):
        run_suite()
    if mode in ("all", "edge"):
        run_edge()
    print("\nDone.")
