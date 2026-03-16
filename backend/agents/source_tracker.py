import json
from datetime import datetime

import requests


def track_misinformation_source(
    claim: str,
    verdict: str,
    evidence: list,
    realtime_articles: list,
) -> dict:
    """
    Identify who is spreading this misinformation.
    Returns source analysis with platform detection.
    """

    if verdict not in ["FALSE", "MISLEADING"]:
        return {
            "tracked": False,
            "reason": "Only tracked for FALSE/MISLEADING claims",
        }

    evidence_text = "\n".join(
        [
            f"- {a.get('title', '')} ({a.get('source', '')} on {a.get('published_date', '')})"
            for a in (evidence or [])[:5]
        ]
    )

    prompt = f"""You are a misinformation analyst.

A claim has been verified as {verdict}:
Claim: "{claim}"

Evidence articles found:
{evidence_text}

Based on the claim content and evidence, analyze:

1. ORIGIN TYPE: Where does this type of misinformation
   typically originate?
   Choose from: social_media / political_propaganda /
   satire_misunderstood / health_misinformation /
   manipulated_media / unknown

2. SPREADING PLATFORMS: Which platforms is this
   likely spreading on?
   Examples: WhatsApp, Twitter/X, Facebook, Telegram,
   YouTube, forwarded messages, news websites

3. SPREAD PATTERN: How is this spreading?
   Examples: viral forwards, bot accounts,
   misleading headlines, out-of-context videos,
   fake screenshots

4. WHO BENEFITS: Who politically or commercially
   benefits from spreading this claim?
   Be objective and factual, not speculative.
   If unclear, say "Cannot determine"

5. FACT CHECK STATUS: Has this been fact-checked
   by known organizations?
   Based on evidence articles, name which
   fact-checkers have addressed this.

6. HOW TO SPOT IT: Give 2-3 ways a regular person
   can identify this is fake news.

Return ONLY valid JSON:
{{
  "origin_type": "category",
  "spreading_platforms": ["platform1", "platform2"],
  "spread_pattern": "description",
  "who_benefits": "description or Cannot determine",
  "fact_checked_by": ["org1", "org2"],
  "how_to_spot": ["tip1", "tip2", "tip3"],
  "warning_level": "low|medium|high|critical",
  "warning_reason": "why this is dangerous"
}}"""

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:1b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 300,
                    "temperature": 0,
                    "num_ctx": 512,
                },
                "keep_alive": "10m",
            },
            timeout=60,
        )

        raw = resp.json().get("response", "")

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
            result["tracked"] = True
            result["analyzed_at"] = datetime.now().isoformat()
            return result

    except Exception as exc:
        print(f"Source tracker error: {exc}")

    return {
        "tracked": True,
        "origin_type": "unknown",
        "spreading_platforms": ["WhatsApp", "Social Media"],
        "spread_pattern": "Viral forwarding",
        "who_benefits": "Cannot determine",
        "fact_checked_by": [],
        "how_to_spot": [
            "Check official government sources",
            "Look for the original article URL",
            "Verify with multiple trusted news outlets",
        ],
        "warning_level": "medium",
        "warning_reason": "Unverified claim spreading online",
    }
