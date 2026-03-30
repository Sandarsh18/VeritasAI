import json
import logging
import math
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None

load_dotenv()
LOGGER = logging.getLogger(__name__)



def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class Neo4jClient:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "neo4j")
        self.driver = None

    def connect(self):
        try:
            if GraphDatabase is None:
                LOGGER.warning("Neo4j driver not installed; graph features disabled.")
                self.driver = None
                return
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            with self.driver.session() as session:
                session.run("RETURN 1")
        except Exception as exc:
            LOGGER.warning("Neo4j unavailable. Continuing without graph storage. %s", exc)
            self.driver = None

    def close(self):
        try:
            if self.driver:
                self.driver.close()
        except Exception:
            LOGGER.warning("Failed to close Neo4j driver cleanly")

    def check_duplicate_claim(self, embedding: List[float], threshold: float = 0.85) -> Optional[Dict]:
        try:
            if not self.driver:
                return None

            query = """
            MATCH (c:Claim)
            RETURN c.claim_text AS claim_text,
                   c.verdict AS verdict,
                   c.confidence AS confidence,
                   c.domain AS domain,
                   c.embedding AS embedding,
                   c.reasoning AS reasoning,
                   c.key_evidence AS key_evidence,
                   c.recommendation AS recommendation,
                     c.evidence_json AS evidence_json,
                     c.prosecutor_json AS prosecutor_json,
                     c.defender_json AS defender_json
            ORDER BY c.created_at DESC
            LIMIT 200
            """

            with self.driver.session() as session:
                rows = list(session.run(query))

            best = None
            best_score = -1.0
            for row in rows:
                row_embedding = row.get("embedding") or []
                score = _cosine_similarity(embedding, row_embedding)
                if score > best_score:
                    best_score = score
                    best = row

            if best is not None and best_score >= threshold:
                evidence = []
                evidence_json = best.get("evidence_json")
                if evidence_json:
                    try:
                        evidence = json.loads(evidence_json)
                    except Exception:
                        evidence = []

                key_evidence = best.get("key_evidence") or []
                if isinstance(key_evidence, str):
                    key_evidence = [key_evidence]

                prosecutor = None
                defender = None
                prosecutor_json = best.get("prosecutor_json")
                defender_json = best.get("defender_json")
                if prosecutor_json:
                    try:
                        prosecutor = json.loads(prosecutor_json)
                    except Exception:
                        prosecutor = None
                if defender_json:
                    try:
                        defender = json.loads(defender_json)
                    except Exception:
                        defender = None

                return {
                    "claim": best.get("claim_text"),
                    "verdict": best.get("verdict"),
                    "confidence": best.get("confidence"),
                    "domain": best.get("domain"),
                    "reasoning": best.get("reasoning"),
                    "key_evidence": key_evidence,
                    "recommendation": best.get("recommendation"),
                    "evidence": evidence,
                    "prosecutor": prosecutor,
                    "defender": defender,
                    "cached": True,
                    "similarity": round(best_score, 4),
                }
        except Exception as exc:
            LOGGER.warning("Neo4j duplicate check failed. Continuing. %s", exc)
        return None

    def store_claim(
        self,
        claim_text: str,
        verdict: str,
        confidence: int,
        domain: str,
        embedding: List[float],
        evidence: List[Dict],
        reasoning: str = "",
        key_evidence: List[str] | None = None,
        recommendation: str = "",
        prosecutor: Dict | None = None,
        defender: Dict | None = None,
    ):
        try:
            if not self.driver:
                return

            key_evidence = key_evidence or []
            evidence_json = json.dumps(evidence, ensure_ascii=False)
            prosecutor_json = json.dumps(prosecutor or {}, ensure_ascii=False)
            defender_json = json.dumps(defender or {}, ensure_ascii=False)

            query_claim = """
            MERGE (c:Claim {claim_text: $claim_text})
            SET c.verdict = $verdict,
                c.confidence = $confidence,
                c.domain = $domain,
                c.embedding = $embedding,
                c.reasoning = $reasoning,
                c.key_evidence = $key_evidence,
                c.recommendation = $recommendation,
                c.evidence_json = $evidence_json,
                c.prosecutor_json = $prosecutor_json,
                c.defender_json = $defender_json,
                c.created_at = datetime()
            """

            with self.driver.session() as session:
                session.run(
                    query_claim,
                    claim_text=claim_text,
                    verdict=verdict,
                    confidence=int(confidence),
                    domain=domain,
                    embedding=[float(x) for x in embedding],
                    reasoning=reasoning,
                    key_evidence=key_evidence,
                    recommendation=recommendation,
                    evidence_json=evidence_json,
                    prosecutor_json=prosecutor_json,
                    defender_json=defender_json,
                )

                for article in evidence:
                    session.run(
                        """
                        MERGE (a:Article {id: $id})
                        SET a.title = $title,
                            a.source = $source,
                            a.source_url = $source_url,
                            a.credibility_score = $credibility_score,
                            a.published_date = $published_date
                        WITH a
                        MERGE (s:Source {name: $source})
                        SET s.source_type = $source_type,
                            s.logo = $source_logo
                        WITH a, s
                        MATCH (c:Claim {claim_text: $claim_text})
                        MERGE (c)-[:SUPPORTED_BY]->(a)
                        MERGE (a)-[:PUBLISHED_BY]->(s)
                        """,
                        id=article.get("id", article.get("title", "unknown")),
                        title=article.get("title", ""),
                        source=article.get("source", "Unknown"),
                        source_url=article.get("source_url", ""),
                        credibility_score=float(article.get("credibility_score", 0.0)),
                        published_date=article.get("published_date", ""),
                        source_type=article.get("source_type", "Unknown"),
                        source_logo=article.get("source_logo", "📰"),
                        claim_text=claim_text,
                    )
        except Exception as exc:
            LOGGER.warning("Neo4j store failed. Continuing. %s", exc)
