from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    body_part: str
    description: str
    version: str
    source_type: str
    approved: bool


class Correction(BaseModel):
    segment: str
    joint: str
    feedback: str
    evidence: str


class AIReviewPayload(BaseModel):
    verdict: Literal["PASS", "RETRY", "REVIEW"]
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=3, max_length=500)
    corrections: list[Correction] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    requires_review: bool = False


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    model: str
    prompt_version: str
    verdict: str
    confidence: float
    summary: str
    corrections: list[dict]
    safety_flags: list[str]
    requires_review: bool
    validation_status: str
    latency_ms: int
    fallback_used: bool
    created_at: datetime


class AttemptOut(BaseModel):
    id: int
    reference_id: str
    reference_name: str
    mode: str
    status: str
    severity: int
    overall_similarity: float
    dtw_distance: float
    speed_ratio: float
    data_quality: float
    worst_segments: list[dict]
    metrics: dict
    created_at: datetime
    review: ReviewOut


class ReviewTaskOut(BaseModel):
    id: int
    review_id: int
    attempt_id: int
    reference_name: str
    reason: str
    status: str
    reviewer_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class ResolveTaskRequest(BaseModel):
    status: Literal["RESOLVED", "DISMISSED"]
    reviewer_note: str = Field(min_length=2, max_length=1000)


class DashboardOut(BaseModel):
    total_attempts: int
    demo_attempts: int
    average_similarity: float
    average_quality: float
    pass_rate: float
    retry_rate: float
    review_rate: float
    fallback_rate: float
    open_review_tasks: int
    recent_attempts: list[dict]
    verdict_distribution: list[dict]

