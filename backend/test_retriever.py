import json

from rag.retriever import retrieve_evidence_minimal


CLAIM = "Will Earth end after 10 billion years?"


def main():
    evidence, meta = retrieve_evidence_minimal(CLAIM, top_k=5, max_retries=1)

    print("INPUT CLAIM:")
    print(CLAIM)

    print("\nRAW API RESPONSE META:")
    print(json.dumps(meta.get("api_runs", []), indent=2, ensure_ascii=False))

    print("\nPARSED SOURCES:")
    for index, item in enumerate(evidence, start=1):
        print(f"{index}. {item.get('title', '')}")
        print(f"   URL: {item.get('url', '')}")
        print(f"   Snippet: {(item.get('content') or item.get('snippet') or '')[:350]}")

    print("\nFILTERED SOURCES:")
    print(json.dumps(meta.get("top_k", []), indent=2, ensure_ascii=False))

    if len(evidence) < 5:
        raise SystemExit(f"Expected at least 5 sources, got {len(evidence)}")


if __name__ == "__main__":
    main()
