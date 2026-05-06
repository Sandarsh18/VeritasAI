import os
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List

from dotenv import load_dotenv

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None

load_dotenv()

LOGGER = logging.getLogger("veritas.graph_store")


class GraphStore:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    def connect(self):
        if GraphDatabase is None:
            LOGGER.warning("[Neo4j] Neo4j driver not available")
            return
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            with self.driver.session() as session:
                session.run("RETURN 1")
            LOGGER.info("[Neo4j] Connected to %s", self.uri)
        except Exception as e:
            LOGGER.error("[Neo4j] Connection failed: %s", str(e))
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            LOGGER.info("[Neo4j] Closed connection")

    def _extract_entities(self, text: str) -> List[str]:
        """Extract capitalized entities from text."""
        # Find capitalized words/phrases (entities)
        entities = []
        words = text.split()
        i = 0
        while i < len(words):
            if words[i] and words[i][0].isupper():
                entity = words[i]
                j = i + 1
                while j < len(words) and words[j] and words[j][0].isupper():
                    entity += " " + words[j]
                    j += 1
                if len(entity) > 2:
                    entities.append(entity)
                i = j
            else:
                i += 1
        return list(set(entities))[:5]  # Unique, limit to 5

    def _infer_topics(self, claim: str) -> List[str]:
        """Infer topics from claim text."""
        topics = []
        keywords = {
            "health": ["covid", "vaccine", "health", "disease", "virus", "hospital"],
            "politics": ["election", "minister", "government", "vote", "parliament"],
            "technology": ["5g", "ai", "chip", "software", "robot", "tech"],
            "finance": ["economy", "gdp", "market", "stock", "inflation"],
            "climate": ["climate", "global warming", "greenhouse"],
        }
        claim_lower = claim.lower()
        for topic, keywords_list in keywords.items():
            if any(kw in claim_lower for kw in keywords_list):
                topics.append(topic)
        return topics or ["factual_claim"]

    def store_claim(self, claim: str, results: List[Dict], verdict: Dict):
        """Store claim and sources in Neo4j with proper relationships."""
        if not self.driver or not claim:
            return

        try:
            verdict_label = str(verdict.get("verdict", "MISLEADING")).upper()
            confidence = int(verdict.get("confidence", 50))
            now_iso = datetime.now(timezone.utc).isoformat()

            entities = self._extract_entities(claim)
            topics = self._infer_topics(claim)

            with self.driver.session() as session:
                # Create Claim node
                LOGGER.info("[Neo4j] Creating claim node: %s", claim[:80])
                session.run(
                    """
                    MERGE (c:Claim {text: $claim})
                    SET c.updated_at = datetime($updated_at),
                        c.verdict = $verdict,
                        c.confidence = $confidence,
                        c.timestamp = datetime($updated_at)
                    RETURN c
                    """,
                    claim=claim,
                    updated_at=now_iso,
                    verdict=verdict_label,
                    confidence=confidence,
                )

                # Create Topic nodes and relationships
                for topic in topics:
                    LOGGER.debug("[Neo4j] Creating topic node: %s", topic)
                    session.run(
                        """
                        MERGE (t:Topic {name: $topic})
                        WITH t
                        MATCH (c:Claim {text: $claim})
                        MERGE (c)-[:ABOUT_TOPIC]->(t)
                        """,
                        topic=topic,
                        claim=claim,
                    )

                # Create Entity nodes and relationships
                for entity in entities:
                    LOGGER.debug("[Neo4j] Creating entity node: %s", entity)
                    session.run(
                        """
                        MERGE (e:Entity {name: $entity})
                        WITH e
                        MATCH (c:Claim {text: $claim})
                        MERGE (c)-[:MENTIONS]->(e)
                        """,
                        entity=entity,
                        claim=claim,
                    )

                # Create Source nodes and relationships
                for item in results or []:
                    url = item.get("link", "")
                    if not url:
                        continue
                    
                    title = item.get("title", "")
                    source = item.get("source", "unknown")
                    date = item.get("date", "")
                    snippet = item.get("snippet", "")
                    credibility = float(item.get("credibility_score", 0.5))

                    # Determine per-source relationship type
                    stance = str(item.get("stance", "")).lower()
                    if stance == "supporting" or verdict_label == "TRUE":
                        rel_type = "SUPPORTED_BY"
                    elif stance == "contradicting" or verdict_label == "FALSE":
                        rel_type = "CONTRADICTED_BY"
                    else:
                        rel_type = "REFERENCED_BY"

                    LOGGER.debug("[Neo4j] Creating source node: %s from %s (rel=%s)", title[:60], source, rel_type)
                    session.run(
                        f"""
                        MERGE (s:Source {{url: $url}})
                        SET s.title = $title,
                            s.source = $source,
                            s.snippet = $snippet,
                            s.date = $date,
                            s.credibility = $credibility,
                            s.updated_at = datetime($updated_at)
                        WITH s
                        MATCH (c:Claim {{text: $claim}})
                        MERGE (c)-[r:{rel_type}]->(s)
                        SET r.credibility = $credibility,
                            r.timestamp = datetime($updated_at)
                        """,
                        claim=claim,
                        url=url,
                        title=title,
                        source=source,
                        snippet=snippet,
                        date=date,
                        credibility=credibility,
                        updated_at=now_iso,
                    )

                    # Extract entities from source and create relationships
                    source_entities = self._extract_entities(f"{title} {source}")
                    for entity in source_entities:
                        LOGGER.debug("[Neo4j] Linking entity %s to source %s", entity, source)
                        session.run(
                            """
                            MERGE (e:Entity {name: $entity})
                            WITH e
                            MATCH (s:Source {url: $url})
                            MERGE (s)-[:MENTIONS]->(e)
                            """,
                            entity=entity,
                            url=url,
                        )

            LOGGER.info("[Neo4j] Successfully stored claim with %d sources", len(results or []))

        except Exception as e:
            LOGGER.error("[Neo4j] Error storing claim: %s", str(e))

    def get_source_reputation(self, url: str) -> float:
        """Get aggregated credibility for a source URL from past verdicts."""
        if not self.driver or not url:
            return 0.5
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (s:Source {url: $url})
                    RETURN s.credibility AS credibility, count(*) AS mentions
                    """,
                    url=url,
                )
                record = result.single()
                if record:
                    cred = float(record.get("credibility", 0.5) or 0.5)
                    mentions = int(record.get("mentions", 1) or 1)
                    # Boost confidence with more mentions (diminishing returns)
                    boost = min(0.1, mentions * 0.02)
                    return min(1.0, cred + boost)
        except Exception as e:
            LOGGER.debug("[Neo4j] get_source_reputation error: %s", str(e)[:80])
        return 0.5

    def get_related_claims(self, claim: str, limit: int = 5) -> List[Dict]:
        """Find similar claims via shared entities or topics."""
        if not self.driver or not claim:
            return []
        try:
            entities = self._extract_entities(claim)
            if not entities:
                return []
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (c:Claim)-[:MENTIONS]->(e:Entity)
                    WHERE e.name IN $entities AND c.text <> $claim
                    RETURN c.text AS claim, c.verdict AS verdict,
                           c.confidence AS confidence, count(e) AS shared_entities
                    ORDER BY shared_entities DESC
                    LIMIT $limit
                    """,
                    entities=entities,
                    claim=claim,
                    limit=limit,
                )
                return [
                    {
                        "claim": r["claim"],
                        "verdict": r["verdict"],
                        "confidence": r["confidence"],
                        "shared_entities": r["shared_entities"],
                    }
                    for r in result
                ]
        except Exception as e:
            LOGGER.debug("[Neo4j] get_related_claims error: %s", str(e)[:80])
        return []

    def get_entity_mentions(self, entity: str) -> List[Dict]:
        """Find all claims mentioning a specific entity."""
        if not self.driver or not entity:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (c:Claim)-[:MENTIONS]->(e:Entity {name: $entity})
                    RETURN c.text AS claim, c.verdict AS verdict, c.confidence AS confidence
                    ORDER BY c.updated_at DESC
                    LIMIT 10
                    """,
                    entity=entity,
                )
                return [
                    {"claim": r["claim"], "verdict": r["verdict"], "confidence": r["confidence"]}
                    for r in result
                ]
        except Exception as e:
            LOGGER.debug("[Neo4j] get_entity_mentions error: %s", str(e)[:80])
        return []
