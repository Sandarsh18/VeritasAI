import os
from datetime import datetime, timezone
from typing import Dict, List

from dotenv import load_dotenv

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None

load_dotenv()


class GraphStore:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    def connect(self):
        if GraphDatabase is None:
            return
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            with self.driver.session() as session:
                session.run("RETURN 1")
        except Exception:
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def store_claim(self, claim: str, results: List[Dict], verdict: Dict):
        if not self.driver or not claim:
            return

        verdict_label = str(verdict.get("verdict", "MISLEADING")).upper()
        relation_type = "SUPPORTED_BY" if verdict_label == "TRUE" else "REFUTED_BY"
        confidence = int(verdict.get("confidence", 50))
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Claim {text: $claim})
                SET c.updated_at = datetime($updated_at),
                    c.verdict = $verdict,
                    c.confidence = $confidence
                """,
                claim=claim,
                updated_at=now_iso,
                verdict=verdict_label,
                confidence=confidence,
            )

            for item in results or []:
                url = item.get("link", "")
                if not url:
                    continue
                title = item.get("title", "")
                source = item.get("source", "unknown")
                date = item.get("date", "")
                snippet = item.get("snippet", "")
                credibility = 0.9 if any(domain in (url or "") for domain in ["reuters.com", "bbc.com", "who.int", "thehindu.com", "ndtv.com"]) else 0.6

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
                    MERGE (c)-[r:{relation_type}]->(s)
                    SET r.credibility = $credibility,
                        r.timestamp = datetime($updated_at)
                    """,
                    claim=claim,
                    url=url,
                    title=title,
                    source=source,
                    snippet=snippet,
                    date=date,
                    credibility=float(credibility),
                    updated_at=now_iso,
                )
