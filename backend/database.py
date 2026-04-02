import os
import json
from datetime import datetime
import uuid

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./veritas.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    claims: Mapped[list["ClaimHistory"]] = relationship(back_populates="user")


class ClaimHistory(Base):
    __tablename__ = "claim_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    claim_text: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    domain: Mapped[str] = mapped_column(String(64), default="general")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    short_id: Mapped[str | None] = mapped_column(String(16), unique=True, index=True, nullable=True)
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="claims")


class ClaimCache(Base):
    __tablename__ = "claim_cache"

    claim_hash: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)

    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:
            columns = connection.exec_driver_sql("PRAGMA table_info(claim_history)").fetchall()
            existing = {row[1] for row in columns}
            if "details_json" not in existing:
                connection.exec_driver_sql("ALTER TABLE claim_history ADD COLUMN details_json TEXT")
            if "short_id" not in existing:
                connection.exec_driver_sql("ALTER TABLE claim_history ADD COLUMN short_id TEXT")

            # Compatibility table for legacy checks that expect a `claims` table.
            connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS claims (id INTEGER PRIMARY KEY)")

            for statement in [
                "ALTER TABLE claims ADD COLUMN claim_hash TEXT",
                "ALTER TABLE claims ADD COLUMN cached_response TEXT",
                "ALTER TABLE claims ADD COLUMN short_id TEXT",
                "CREATE INDEX IF NOT EXISTS idx_claim_hash ON claims(claim_hash)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_short_id ON claims(short_id)",
            ]:
                try:
                    connection.exec_driver_sql(statement)
                except OperationalError:
                    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_cached_result(claim_hash: str, max_age_hours: int = 24):
    """Return cached verification result if it exists and is fresh."""
    import sqlite3, json
    from datetime import datetime, timedelta

    conn = sqlite3.connect("veritas.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_cache (
            claim_hash TEXT PRIMARY KEY,
            result_json TEXT,
            created_at TEXT
        )
    """)
    cutoff = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
    cursor.execute(
        "SELECT result_json FROM claim_cache WHERE claim_hash=? AND created_at>?",
        (claim_hash, cutoff)
    )
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def save_cached_result(claim_hash: str, result: dict):
    """Save verification result to cache."""
    import sqlite3, json
    from datetime import datetime

    conn = sqlite3.connect("veritas.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_cache (
            claim_hash TEXT PRIMARY KEY,
            result_json TEXT,
            created_at TEXT
        )
    """)
    cursor.execute(
        "INSERT OR REPLACE INTO claim_cache VALUES (?, ?, ?)",
        (claim_hash, json.dumps(result), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_claim_by_short_id(short_id: str):
    db = SessionLocal()
    try:
        row = db.query(ClaimHistory).filter(ClaimHistory.short_id == short_id).first()
        if not row:
            return None

        if row.details_json:
            try:
                payload = json.loads(row.details_json)
                payload["history_id"] = row.id
                payload["short_id"] = row.short_id
                return payload
            except Exception:
                pass

        return {
            "history_id": row.id,
            "short_id": row.short_id,
            "claim": row.claim_text,
            "claim_type": "factual_claim",
            "domain": row.domain,
            "verdict": row.verdict,
            "confidence": row.confidence,
            "reasoning": "Detailed snapshot unavailable for this record.",
            "evidence": [],
            "prosecutor": {"arguments": []},
            "defender": {"arguments": []},
        }
    finally:
        db.close()
