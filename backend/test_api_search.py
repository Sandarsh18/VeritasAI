from rag.retriever import news_search, serp_search


def test_serp():
    results = serp_search("Is India corrupt country")
    print("SERP count:", len(results))
    if results:
        print("SERP first:", results[0].get("title", ""), results[0].get("url", ""))


def test_news():
    articles = news_search("India corruption ranking")
    print("NEWS count:", len(articles))
    if articles:
        print("NEWS first:", articles[0].get("title", ""), articles[0].get("url", ""))


if __name__ == "__main__":
    test_serp()
    print("-" * 80)
    test_news()
