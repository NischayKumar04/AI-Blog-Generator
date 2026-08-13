"""SQLAlchemy ORM models for persisted blog generations.

One table, ``blog_generations``, records every run of the pipeline: its inputs
(topic), its structured outputs (plan/evidence as JSON, final markdown), a few
denormalized metrics for cheap list queries, and lifecycle status/timing.

Portability: JSON columns use ``JSON().with_variant(JSONB, "postgresql")`` so
the same models run on SQLite (local dev + tests) and Postgres (container) with
no changes. The UUID primary key uses SQLAlchemy's generic ``Uuid`` type, which
is a native ``UUID`` on Postgres and a CHAR on SQLite.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class BlogGeneration(Base):
    __tablename__ = "blog_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )

    # inputs
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # routing / plan summary (denormalized for list views)
    mode: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blog_kind: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blog_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # outputs
    final_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_json: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    evidence_json: Mapped[Optional[list]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    # metrics
    section_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    diagram_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # lifecycle
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return (
            f"<BlogGeneration id={self.id} status={self.status!r} "
            f"topic={self.topic!r}>"
        )
