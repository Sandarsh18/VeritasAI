"""
Search for claim on social media platforms
using free/public APIs and RSS.
No API key required for basic detection.
"""

from urllib.parse import quote

import feedparser


def search_claim_online(claim: str) -> dict:
    """
    Search for where this claim is appearing online.
    Uses Google News RSS (free, no key needed).
    """
    results = {
        "found_in_news": [],
        "fact_check_results": [],
        "social_signals": [],
    }

    try:
        encoded = quote(f'"{claim[:50]}"')
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"

        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            source = entry.get("source", {}).get("title", "Unknown")
            date = entry.get("published", "")[:16]

            item = {
                "title": title[:100],
                "source": source,
                "url": link,
                "date": date,
            }

            title_lower = title.lower()
            is_factcheck = any(
                word in title_lower
                for word in ["fact check", "fact-check", "false", "misleading", "fake", "debunk", "claim", "viral"]
            )

            if is_factcheck:
                results["fact_check_results"].append(item)
            else:
                results["found_in_news"].append(item)

        fc_encoded = quote(f'fact check "{claim[:40]}"')
        fc_url = f"https://news.google.com/rss/search?q={fc_encoded}&hl=en-IN&gl=IN"
        fc_feed = feedparser.parse(fc_url)

        for entry in fc_feed.entries[:5]:
            results["fact_check_results"].append(
                {
                    "title": entry.get("title", "")[:100],
                    "source": entry.get("source", {}).get("title", "Unknown"),
                    "url": entry.get("link", ""),
                    "date": entry.get("published", "")[:16],
                }
            )

    except Exception as exc:
        print(f"Social search error: {exc}")

    seen = set()
    unique_fc = []
    for item in results["fact_check_results"]:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique_fc.append(item)

    results["fact_check_results"] = unique_fc[:5]
    results["found_in_news"] = results["found_in_news"][:5]

    return results
