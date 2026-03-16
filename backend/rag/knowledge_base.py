"""
Static knowledge base for well-known facts.
Used when real-time or local retrieval is sparse or off-topic.
"""

KNOWLEDGE_BASE = [
    {
        "id": "kb_ww2_001",
        "title": "World War 2 Timeline: 1939-1945",
        "content": "World War 2 began on September 1, 1939 when Nazi Germany invaded Poland. Britain and France declared war on Germany two days later. The war ended in 1945. Claims that World War 2 started in 2000 are historically false.",
        "source": "Historical Record",
        "credibility_score": 0.99,
        "source_logo": "📚",
        "source_type": "Historical Fact",
        "published_date": "Established History",
        "author": "Historical Consensus",
        "is_realtime": False,
        "keywords": ["world war", "world war 2", "ww2", "1939", "1945", "germany", "poland"],
    },
    {
        "id": "kb_ww1_001",
        "title": "World War 1: 1914-1918",
        "content": "World War 1 began in 1914 and ended in 1918 after years of conflict involving the Allied and Central Powers.",
        "source": "Historical Record",
        "credibility_score": 0.99,
        "source_logo": "📚",
        "source_type": "Historical Fact",
        "published_date": "Established History",
        "author": "Historical Consensus",
        "is_realtime": False,
        "keywords": ["world war 1", "ww1", "first world war", "1914", "1918"],
    },
    {
        "id": "kb_in_pm_001",
        "title": "Current Prime Minister of India: Narendra Modi",
        "content": "Narendra Modi is the current Prime Minister of India. Rahul Gandhi is not the Prime Minister of India.",
        "source": "Government of India",
        "credibility_score": 0.99,
        "source_logo": "🇮🇳",
        "source_type": "Official Record",
        "published_date": "2024",
        "author": "Government Record",
        "is_realtime": False,
        "keywords": ["prime minister", "pm", "india", "narendra modi", "rahul gandhi"],
    },
    {
        "id": "kb_in_pres_001",
        "title": "Current President of India: Droupadi Murmu",
        "content": "Droupadi Murmu is the current President of India, serving since July 2022.",
        "source": "Government of India",
        "credibility_score": 0.99,
        "source_logo": "🇮🇳",
        "source_type": "Official Record",
        "published_date": "2024",
        "author": "Government Record",
        "is_realtime": False,
        "keywords": ["president", "india", "droupadi murmu", "murmu"],
    },
    {
        "id": "kb_sci_light_001",
        "title": "Speed of Light vs Speed of Sound",
        "content": "Light travels at approximately 299,792,458 meters per second in vacuum. Sound travels at approximately 343 meters per second in air at room temperature. Light is therefore vastly faster than sound.",
        "source": "Physics Research",
        "credibility_score": 0.99,
        "source_logo": "🔬",
        "source_type": "Scientific Fact",
        "published_date": "Established Science",
        "author": "Scientific Consensus",
        "is_realtime": False,
        "keywords": ["light", "sound", "faster", "speed of light", "speed of sound", "physics"],
    },
    {
        "id": "kb_sci_earth_001",
        "title": "Earth's Shape and Solar System Facts",
        "content": "Earth is an oblate spheroid and orbits the Sun. Claims that Earth is flat are false and contradicted by astronomy, physics, and direct observation.",
        "source": "NASA/Scientific Consensus",
        "credibility_score": 0.99,
        "source_logo": "🚀",
        "source_type": "Scientific Fact",
        "published_date": "Established Science",
        "author": "NASA & Scientific Consensus",
        "is_realtime": False,
        "keywords": ["earth", "flat", "round", "sphere", "sun", "orbits"],
    },
    {
        "id": "kb_health_vax_001",
        "title": "COVID-19 Vaccines: Safety and Fertility",
        "content": "COVID-19 vaccines do not cause infertility. This has been studied extensively by WHO, CDC, and peer-reviewed research with no credible evidence of fertility harm.",
        "source": "WHO/CDC",
        "credibility_score": 0.99,
        "source_logo": "🏥",
        "source_type": "Health Authority",
        "published_date": "2024",
        "author": "WHO & CDC",
        "is_realtime": False,
        "keywords": ["covid", "vaccine", "infertility", "fertility", "who", "cdc"],
    },
    {
        "id": "kb_health_5g_001",
        "title": "5G Technology and COVID-19: No Connection",
        "content": "5G technology does not spread coronavirus. COVID-19 is caused by the SARS-CoV-2 virus and spreads through biological transmission pathways, not radio waves.",
        "source": "WHO",
        "credibility_score": 0.99,
        "source_logo": "🏥",
        "source_type": "Health Authority",
        "published_date": "2024",
        "author": "WHO/Telecom Authorities",
        "is_realtime": False,
        "keywords": ["5g", "coronavirus", "covid", "spread", "radio waves"],
    },
]


def search_knowledge_base(claim: str, top_k: int = 3) -> list:
    claim_lower = claim.lower()
    claim_words = {
        word
        for word in claim_lower.replace("?", " ").replace(",", " ").split()
        if word not in {"is", "are", "was", "the", "a", "an", "in", "of", "to", "and", "or", "that", "this", "it"}
    }

    scored = []
    for article in KNOWLEDGE_BASE:
        keywords = [keyword.lower() for keyword in article.get("keywords", [])]
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()

        score = 0
        for keyword in keywords:
            if keyword in claim_lower:
                score += 2

        for word in claim_words:
            if len(word) > 3 and (word in title or word in content):
                score += 1

        if score > 0:
            candidate = article.copy()
            candidate["relevance_score"] = min(score / 10, 0.95)
            candidate["combined_score"] = min(score / 8, 0.95)
            candidate["evidence_source"] = "knowledge_base"
            scored.append(candidate)

    scored.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
    return scored[:top_k]