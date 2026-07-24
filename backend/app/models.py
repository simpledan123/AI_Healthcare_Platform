from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReferenceExercise(Base):
    __tablename__ = "reference_exercises"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    body_part: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0")
    sequence: Mapped[list] = mapped_column(JSON, nullable=False)
    feature_names: Mapped[list] = mapped_column(JSON, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="demo")
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attempts: Mapped[list["PoseAttempt"]] = relationship(back_populates="reference")


class PoseAttempt(Base):
    __tablename__ = "pose_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("reference_exercises.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="demo")
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    overall_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    dtw_distance: Mapped[float] = mapped_column(Float, nullable=False)
    speed_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    data_quality: Mapped[float] = mapped_column(Float, nullable=False)
    worst_segments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    derived_sequence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    reference: Mapped["ReferenceExercise"] = relationship(back_populates="attempts")
    review: Mapped["AIReview"] = relationship(back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("pose_attempts.id"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(30), nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    corrections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    safety_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attempt: Mapped["PoseAttempt"] = relationship(back_populates="review")
    task: Mapped["ReviewTask"] = relationship(back_populates="review", uselist=False, cascade="all, delete-orphan")


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("ai_reviews.id"), unique=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN", index=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review: Mapped["AIReview"] = relationship(back_populates="task")

