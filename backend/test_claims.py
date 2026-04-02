import requests, json, sys, time

print("Starting tests...")

BASE = "http://localhost:8000"

TESTS = [
    {
        "name": "WW3 Claim",
        "claim": "WW3 is happening right now",
        "expected_verdict": "FALSE",
        "expected_min_confidence": 75,
        "must_have_sources": [
            "reuters", "bbc", "ndtv",
            "altnews", "apnews"
        ],
        "must_not_have_sources": [
            "wikipedia", "reddit", "twitter"
        ]
    },
    {
        "name": "Gold Rate Drop",
        "claim": "Gold rate has dropped by nearly "
                 "4000 rupees in India",
        "expected_verdict": "TRUE",
        "expected_min_confidence": 70,
        "must_have_sources": [
            "economictimes", "livemint",
            "business-standard", "thehindu",
            "moneycontrol", "goodreturns"
        ],
        "must_not_have_sources": []
    },
    {
        "name": "Capabl Unicorn (Unknown Claim)",
        "claim": "Capabl is a unicorn company",
        "expected_verdict": "UNVERIFIED",
        "expected_min_confidence": 36,
        "must_have_sources": [],
        "must_not_have_sources": ["capabl.in", "capabl"]
    },
    {
        "name": "5G COVID (Known False)",
        "claim": "5G towers are spreading COVID-19",
        "expected_verdict": "FALSE",
        "expected_min_confidence": 80,
        "must_have_sources": [
            "who", "reuters", "bbc",
            "altnews", "boomlive"
        ],
        "must_not_have_sources": []
    }
]

def run_test(test: dict) -> bool:
    print(f"\n{'='*55}")
    print(f"TEST: {test['name']}")
    print(f"Claim: '{test['claim']}'")
    print(f"Expected: {test['expected_verdict']} "
          f"(>= {test['expected_min_confidence']}%)")
    print(f"{'='*55}")

    try:
        resp = requests.post(
            f"{BASE}/api/verify",
            json={"claim": test["claim"]},
            timeout=600
        )
        data = resp.json()

        verdict = data.get("verdict", "")
        confidence = data.get("confidence", 0)
        reasoning = data.get("reasoning", "")
        evidence = data.get("evidence", [])

        print(f"\nVerdict:    {verdict}")
        print(f"Confidence: {confidence}%")
        print(f"Reasoning:  {reasoning[:120]}")
        print(f"\nEvidence sources ({len(evidence)}):")

        source_urls = []
        for e in evidence:
            src = e.get("source", "")
            url = e.get("source_url", "")
            cred = e.get("credibility_score", 0)
            print(f"  • [{src}] cred={cred:.2f}")
            print(f"    {url}")
            source_urls.append(url.lower())

        disagreement = data.get("verdict_insights", {}).get("disagreement_score", -1.0)
        if disagreement >= 0.0 and disagreement <= 1.0:
            print(f"✅ Disagreement score is valid: {disagreement:.2f}")
        else:
            print(f"❌ Disagreement score is invalid: {disagreement}")
            passed = False

        passed = True

        if verdict != test["expected_verdict"]:
            print(f"\n❌ VERDICT WRONG: "
                  f"got {verdict}, "
                  f"expected {test['expected_verdict']}")
            passed = False
        else:
            print(f"\n✅ Verdict correct: {verdict}")

        if confidence < test["expected_min_confidence"]:
            print(f"❌ CONFIDENCE TOO LOW: "
                  f"got {confidence}, "
                  f"need >= "
                  f"{test['expected_min_confidence']}")
            passed = False
        else:
            print(f"✅ Confidence ok: {confidence}%")

        for must in test["must_not_have_sources"]:
            if any(must in u for u in source_urls):
                print(f"❌ BLOCKED SOURCE APPEARED: {must}")
                passed = False
            else:
                print(f"✅ Blocked source absent: {must}")

        if passed:
            print(f"\n🎉 TEST PASSED: {test['name']}")
        else:
            print(f"\n💥 TEST FAILED: {test['name']}")
            print(f"Full response:")
            print(json.dumps(data, indent=2)[:1500])

        return passed

    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False

results = []
for test in TESTS:
    result = run_test(test)
    results.append(result)
    time.sleep(3)

print(f"\n{'='*55}")
print("FINAL RESULTS:")
for i, test in enumerate(TESTS):
    icon = "✅" if results[i] else "❌"
    print(f"  {icon} {test['name']}")

if all(results):
    print("\n🎉 ALL 4 TESTS PASSED. VeritasAI is working!")
    sys.exit(0)
else:
    failed = sum(1 for r in results if not r)
    print(f"\n💥 {failed}/4 TESTS FAILED. Fix and retry.")
    sys.exit(1)
