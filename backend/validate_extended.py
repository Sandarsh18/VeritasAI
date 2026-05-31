"""Extended validation harness (read-only). Phases A–E.

Runs each claim through /api/verify and reports retrieval, agent, stance,
overlap, confidence, and schema-contract metrics. Does NOT modify any logic.
"""

import json
import sys
import time
import urllib.request

API = "http://localhost:8000/api/verify"

CLAIMS = [
    ("Is Earth flat?", "FALSE"),
    ("Did humans land on the moon?", "TRUE"),
    ("Is Bangalore the capital of Karnataka?", "TRUE"),
    ("Is Islam older than Hinduism?", "FALSE"),
]


def _post(claim: str) -> dict:
    body = json.dumps({"claim": claim}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def _evidence_ids(items):
    """Stable id per evidence row = source_url (or title)."""
    ids = []
    for it in items or []:
        key = (it.get("source_url") or it.get("url") or it.get("link") or it.get("title") or "").strip().lower()
        if key:
            ids.append(key)
    return ids


def _provider_counts(meta: dict) -> dict:
    totals = {"tavily": 0, "serpapi": 0, "newsapi": 0}
    if not isinstance(meta, dict):
        return totals
    if isinstance(meta.get("provider_counts"), dict):
        for k in totals:
            totals[k] = meta["provider_counts"].get(k, 0)
        return totals
    # dig through api_runs
    for run in meta.get("api_runs", []) or []:
        for q in run.get("queries", []) or []:
            pc = q.get("provider_counts") or {}
            for k in totals:
                totals[k] += int(pc.get(k, 0) or 0)
    return totals


def main():
    results = []
    for claim, expected in CLAIMS:
        print(f"\n{'='*70}\nCLAIM: {claim}  (expected {expected})\n{'='*70}")
        t0 = time.time()
        try:
            d = _post(claim)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            results.append({"claim": claim, "error": str(exc)})
            continue
        dt = round(time.time() - t0, 1)

        evidence = d.get("evidence") or []
        pros = d.get("prosecutor") or {}
        deff = d.get("defender") or {}
        pros_ev = d.get("prosecutor_evidence") or []
        def_ev = d.get("defender_evidence") or []
        vi = d.get("verdict_insights") or {}
        meta = d.get("retrieval_meta") or {}
        pc = _provider_counts(meta)

        # Overlap (Phase B)
        d_ids = set(_evidence_ids(def_ev)) or set(_evidence_ids([{"source_url": a.get("source")} for a in (deff.get("arguments") or [])]))
        p_ids = set(_evidence_ids(pros_ev)) or set(_evidence_ids([{"source_url": a.get("source")} for a in (pros.get("arguments") or [])]))
        shared = d_ids & p_ids
        union = d_ids | p_ids
        overlap_pct = round(100.0 * len(shared) / len(union), 1) if union else 0.0

        row = {
            "claim": claim,
            "expected": expected,
            "verdict": d.get("verdict"),
            "confidence": d.get("confidence"),
            "time_s": dt,
            "provider_counts": pc,
            "final_evidence_count": len(evidence),
            "sources": [e.get("source") for e in evidence],
            "pros_args": len(pros.get("arguments") or []),
            "pros_strength": pros.get("prosecution_strength"),
            "def_args": len(deff.get("arguments") or []),
            "def_strength": deff.get("defense_strength"),
            "supporting_count": vi.get("supporting_sources"),
            "contradicting_count": vi.get("contradicting_sources"),
            "fmt_judge_reasoning": bool(d.get("judge_reasoning")),
            "fmt_supporting_count": d.get("supporting_count"),
            "fmt_contradicting_count": d.get("contradicting_count"),
            "def_ev_ids": sorted(d_ids),
            "pros_ev_ids": sorted(p_ids),
            "shared_ev_ids": sorted(shared),
            "overlap_pct": overlap_pct,
            "reasoning": (d.get("reasoning") or "")[:300],
            "schema_keys": sorted(d.keys()),
        }
        results.append(row)

        print(f"  verdict={row['verdict']} confidence={row['confidence']} time={dt}s")
        print(f"  providers: tavily={pc['tavily']} serpapi={pc['serpapi']} newsapi={pc['newsapi']}")
        print(f"  final_evidence={row['final_evidence_count']} sources={row['sources']}")
        print(f"  prosecutor: args={row['pros_args']} strength={row['pros_strength']}")
        print(f"  defender:   args={row['def_args']} strength={row['def_strength']}")
        print(f"  supporting={row['supporting_count']} contradicting={row['contradicting_count']}")
        print(f"  OVERLAP: def_ids={len(d_ids)} pros_ids={len(p_ids)} shared={len(shared)} -> {overlap_pct}%")
        print(f"  reasoning: {row['reasoning'][:160]}")

    with open("/tmp/extended_validation.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved /tmp/extended_validation.json")


if __name__ == "__main__":
    main()
