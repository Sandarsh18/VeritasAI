"""SQLite fallback store for claims when Neo4j is unavailable."""
import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'claims.db')

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                verdict TEXT,
                confidence INTEGER,
                timestamp TEXT
            )
        """)
        conn.commit()

def save_claim(claim_text: str, verdict: str, confidence: float) -> str:
    init_db()
    claim_id = hashlib.md5(claim_text.encode()).hexdigest()[:12]
    ts = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO claims (id, text, verdict, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (claim_id, claim_text, verdict, int(confidence), ts))
        conn.commit()
    return claim_id

def load_claims(limit: int = 20) -> list[dict]:
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, text, verdict, confidence, timestamp FROM claims ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

def load_stats() -> dict:
    init_db()
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        verdict_rows = conn.execute(
            "SELECT verdict, COUNT(*) as cnt FROM claims GROUP BY verdict"
        ).fetchall()
    verdict_dist = {r['verdict']: r['cnt'] for r in verdict_rows if r['verdict']}
    return {
        "total_claims": total,
        "verdict_distribution": verdict_dist,
        "top_sources": [],
    }
