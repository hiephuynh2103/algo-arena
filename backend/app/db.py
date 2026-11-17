import os
from datetime import datetime, timezone

from sqlalchemy import (create_engine, String, Integer, Boolean, DateTime, JSON, ForeignKey,
                        UniqueConstraint, Float)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def _db_url():
    url = os.getenv("DATABASE_URL", "sqlite:///./algoarena.db")
    # Supabase/Render thường cấp dạng postgres:// hoặc postgresql:// → dùng driver psycopg v3
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _db_url()
_kw = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {
    "pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}
engine = create_engine(DATABASE_URL, **_kw)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16), default="player")  # player | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    acc_sum: Mapped[float] = mapped_column(Float, default=0)
    puzzles_done: Mapped[list] = mapped_column(JSON, default=list)
    tutorials_done: Mapped[list] = mapped_column(JSON, default=list)


class Deck(Base):
    __tablename__ = "decks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    cards: Mapped[list] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("user_id", "seed", name="uq_match_user_seed"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    difficulty: Mapped[str] = mapped_column(String(10))
    seed: Mapped[int] = mapped_column(Integer)
    player_deck: Mapped[list] = mapped_column(JSON)
    ai_deck: Mapped[list] = mapped_column(JSON)
    actions: Mapped[list] = mapped_column(JSON)
    winner: Mapped[int] = mapped_column(Integer)          # 0 người chơi, 1 AI, -1 hoà
    surrender: Mapped[bool] = mapped_column(Boolean, default=False)
    turns: Mapped[int] = mapped_column(Integer)
    accuracy: Mapped[int] = mapped_column(Integer)
    insight: Mapped[int] = mapped_column(Integer)
    xp_gain: Mapped[int] = mapped_column(Integer)
    points_gain: Mapped[int] = mapped_column(Integer)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
