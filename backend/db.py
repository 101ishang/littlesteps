"""SQLite database models.

Privacy design (Agents.md -> Hard rules, Data & privacy):
- `User` and `Child` hold the only personal data in this app (email, child
  nickname/DOB) and are only ever readable through an authenticated request
  for that same user (see backend/auth.py).
- `ScreeningRecord` tracks a child's screening history over time so a
  parent can see trends, not just a one-off result. It's owned by a child,
  which is owned by a user — access is gated the same way.
- `AnalyticsEvent` is deliberately NOT linked to `User` or `Child` at all —
  no user_id, no child_id, no email, no name, no free text. It stores only
  coarse, non-identifying fields (age bracket, band, domain, day-level
  timestamp) so product-improvement analytics can't be traced back to a
  specific parent or child by anyone, including us. This is anonymization
  by construction (no identifier exists to remove), not just an access
  rule on top of identifiable data.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    children: Mapped[list["Child"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Child(Base):
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gestational_age_weeks: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner: Mapped["User"] = relationship(back_populates="children")
    screenings: Mapped[list["ScreeningRecord"]] = relationship(
        back_populates="child", cascade="all, delete-orphan", order_by="ScreeningRecord.created_at"
    )


class ScreeningRecord(Base):
    """One completed screening session for a child, kept for trend tracking."""

    __tablename__ = "screening_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    age_label: Mapped[str] = mapped_column(String, nullable=False)
    corrected_age_months: Mapped[float | None] = mapped_column(nullable=True)
    band: Mapped[str] = mapped_column(String, nullable=False)
    regression_detected: Mapped[bool] = mapped_column(default=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)  # list[MilestoneAnswer] as JSON
    ai_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_encouragement: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_used_fallback: Mapped[bool] = mapped_column(default=True)

    child: Mapped["Child"] = relationship(back_populates="screenings")


class PasswordResetToken(Base):
    """A one-time, time-limited password reset token.

    Only `token_hash` (sha256 of the raw token) is stored — never the raw
    token itself — same principle as `User.password_hash` (see backend/auth.py).
    A token is single-use (`used_at`) and expires (`expires_at`); both are
    checked before it's honored (backend/main.py's reset-password endpoint).
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AnalyticsEvent(Base):
    """Anonymized, aggregate-only analytics. No user_id/child_id/email/name — see module docstring.

    input_tokens/output_tokens/model/ai_used_fallback are cost/reliability telemetry for the
    explainer+safety-reviewer agent pair (backend/agents.py) — non-identifying, same as every
    other column here, and this is the project's real Tokenomics data source (see Agents.md).
    """

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column(Date, default=date.today)  # day precision only
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "screening_completed"
    age_label: Mapped[str] = mapped_column(String, nullable=False)
    band: Mapped[str] = mapped_column(String, nullable=False)
    flagged_count: Mapped[int] = mapped_column(default=0)
    regression_detected: Mapped[bool] = mapped_column(default=False)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_used_fallback: Mapped[bool | None] = mapped_column(nullable=True)


def _ensure_columns_exist() -> None:
    """Tiny, idempotent SQLite migration: add any columns a prior app.db is missing.

    There's no Alembic in this prototype; `Base.metadata.create_all` only creates
    missing tables, not missing columns on existing ones, so a dev database created
    before a column was added would otherwise be stuck on the old schema.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if not inspector.has_table("screening_records") or not inspector.has_table("analytics_events"):
        return  # fresh DB — create_all already includes every current column

    with engine.begin() as conn:
        existing = {c["name"] for c in inspector.get_columns("screening_records")}
        for col, ddl_type in [
            ("ai_summary", "TEXT"),
            ("ai_encouragement", "TEXT"),
            ("ai_used_fallback", "BOOLEAN DEFAULT 1"),
        ]:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE screening_records ADD COLUMN {col} {ddl_type}"))

        existing = {c["name"] for c in inspector.get_columns("analytics_events")}
        for col, ddl_type in [
            ("input_tokens", "INTEGER"),
            ("output_tokens", "INTEGER"),
            ("model", "TEXT"),
            ("ai_used_fallback", "BOOLEAN"),
        ]:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE analytics_events ADD COLUMN {col} {ddl_type}"))


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    _ensure_columns_exist()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
