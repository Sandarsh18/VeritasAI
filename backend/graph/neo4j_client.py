from neo4j import GraphDatabase
import hashlib
import os
from datetime import datetime

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

_driver = None
_connected = False

def get_driver():
    global _driver, _connected
    if _driver is None:
        try:
            auth = (NEO4J_USER, NEO4J_PASSWORD) if NEO4J_PASSWORD else ("neo4j", "")
            _driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
            _driver.verify_connectivity()
            _connected = True
            _create_constraints()
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            _driver = None
            _connected = False
    return _driver

def is_connected():
    try:
        driver = get_driver()
        return driver is not None and _connected
    except:
        return False

def _create_constraints():
    driver = get_driver()
    if not driver:
        return
    with driver.session() as session:
        try:
            session.run("CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.claim_id IS UNIQUE")
            session.run("CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE")
        except Exception as e:
            print(f"Constraint creation warning: {e}")

def _generate_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def store_claim(claim_text: str, verdict: str, confidence: float) -> str:
    driver = get_driver()
    if not driver:
        return _generate_id(claim_text)

    claim_id = _generate_id(claim_text)
    with driver.session() as session:
        session.run("""
            MERGE (c:Claim {claim_id: $claim_id})
            SET c.text = $text,
                c.verdict = $verdict,
                c.confidence = $confidence,
                c.timestamp = $timestamp
        """, claim_id=claim_id, text=claim_text, verdict=verdict,
            confidence=confidence, timestamp=datetime.now().isoformat())
    return claim_id

def store_evidence_link(claim_id: str, article_id: str, relationship_type: str, article_title: str = "", source: str = ""):
    driver = get_driver()
    if not driver:
        return

    valid_types = ['CONTRADICTED_BY', 'SUPPORTED_BY', 'RELATED_TO']
    if relationship_type not in valid_types:
        relationship_type = 'RELATED_TO'

    with driver.session() as session:
        session.run(f"""
            MERGE (a:Article {{article_id: $article_id}})
            SET a.title = $title, a.source = $source
            WITH a
            MATCH (c:Claim {{claim_id: $claim_id}})
            MERGE (c)-[:{relationship_type}]->(a)
        """, article_id=article_id, title=article_title, source=source, claim_id=claim_id)

def find_similar_claims(claim_text: str, threshold: float = 0.85) -> list[dict]:
    driver = get_driver()
    if not driver:
        return []

    with driver.session() as session:
        result = session.run("""
            MATCH (c:Claim)
            WHERE c.text CONTAINS $keyword
            RETURN c.claim_id as id, c.text as text, c.verdict as verdict,
                   c.confidence as confidence, c.timestamp as timestamp
            LIMIT 5
        """, keyword=claim_text[:30])

        claims = []
        for record in result:
            claims.append({
                'id': record['id'],
                'text': record['text'],
                'verdict': record['verdict'],
                'confidence': record['confidence'],
                'timestamp': record['timestamp']
            })
        return claims

def get_claim_network(claim_id: str) -> dict:
    driver = get_driver()
    if not driver:
        return {"nodes": [], "edges": []}

    with driver.session() as session:
        result = session.run("""
            MATCH (c:Claim {claim_id: $claim_id})
            OPTIONAL MATCH (c)-[r]->(a:Article)
            RETURN c, r, a
        """, claim_id=claim_id)

        nodes = []
        edges = []
        seen_nodes = set()

        for record in result:
            claim = record['c']
            if claim_id not in seen_nodes:
                nodes.append({
                    'id': claim_id,
                    'label': claim['text'][:50] + '...' if len(claim.get('text', '')) > 50 else claim.get('text', ''),
                    'type': 'claim',
                    'verdict': claim.get('verdict', 'UNVERIFIED')
                })
                seen_nodes.add(claim_id)

            if record['a']:
                article = record['a']
                art_id = article['article_id']
                if art_id not in seen_nodes:
                    nodes.append({
                        'id': art_id,
                        'label': article.get('title', art_id),
                        'type': 'article',
                        'source': article.get('source', '')
                    })
                    seen_nodes.add(art_id)

                if record['r']:
                    edges.append({
                        'source': claim_id,
                        'target': art_id,
                        'type': type(record['r']).__name__
                    })

        return {"nodes": nodes, "edges": edges}

def get_all_claims(limit: int = 20) -> list[dict]:
    driver = get_driver()
    if not driver:
        return []

    with driver.session() as session:
        result = session.run("""
            MATCH (c:Claim)
            RETURN c.claim_id as id, c.text as text, c.verdict as verdict,
                   c.confidence as confidence, c.timestamp as timestamp
            ORDER BY c.timestamp DESC
            LIMIT $limit
        """, limit=limit)

        return [dict(record) for record in result]

def get_stats() -> dict:
    driver = get_driver()
    if not driver:
        return {"total_claims": 0, "verdict_distribution": {}, "top_sources": []}

    with driver.session() as session:
        total = session.run("MATCH (c:Claim) RETURN count(c) as total").single()
        verdicts = session.run("""
            MATCH (c:Claim)
            RETURN c.verdict as verdict, count(c) as count
            ORDER BY count DESC
        """)
        sources = session.run("""
            MATCH (a:Article)
            RETURN a.source as source, count(a) as count
            ORDER BY count DESC
            LIMIT 5
        """)

        verdict_dist = {r['verdict']: r['count'] for r in verdicts if r['verdict']}
        source_list = [{'source': r['source'], 'count': r['count']} for r in sources if r['source']]

        return {
            "total_claims": total['total'] if total else 0,
            "verdict_distribution": verdict_dist,
            "top_sources": source_list
        }
