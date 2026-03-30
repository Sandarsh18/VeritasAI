import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
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
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="claims")



def init_db():
    Base.metadata.create_all(bind=engine)

    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:
            columns = connection.exec_driver_sql("PRAGMA table_info(claim_history)").fetchall()
            existing = {row[1] for row in columns}
            if "details_json" not in existing:
                connection.exec_driver_sql("ALTER TABLE claim_history ADD COLUMN details_json TEXT")



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
