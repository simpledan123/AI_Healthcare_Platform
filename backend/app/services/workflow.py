from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AIReview, PoseAttempt, ReferenceExercise, ReviewTask
from .ai_reviewer import review_pose
from .dtw import compare_sequences
from .notifier import notify_review_queue


def run_motion_review(
    db: Session,
    settings: Settings,
    reference: ReferenceExercise,
    user_sequence: list[list[float]],
    *,
    data_quality: float,
    mode: str,
    severity: int,
    pain_description: str = "",
    extraction_metrics: dict | None = None,
) -> PoseAttempt:
    comparison = compare_sequences(user_sequence, reference.sequence)
    status = "ANALYZED" if data_quality >= 0.62 else "LOW_QUALITY"
    metrics = {**comparison.metrics, **(extraction_metrics or {})}

    attempt = PoseAttempt(
        reference_id=reference.id,
        mode=mode,
        status=status,
        severity=severity,
        overall_similarity=comparison.similarity,
        dtw_distance=comparison.distance,
        speed_ratio=comparison.speed_ratio,
        data_quality=data_quality,
        worst_segments=comparison.worst_segments,
        metrics=metrics,
        derived_sequence=user_sequence if settings.store_derived_sequence else None,
    )
    db.add(attempt)
    db.flush()

    snapshot = {
        "attempt_id": attempt.id,
        "exercise_id": reference.id,
        "exercise_name": reference.name,
        "reference_version": reference.version,
        "reference_source_type": reference.source_type,
        "overall_similarity": comparison.similarity,
        "dtw_distance": comparison.distance,
        "speed_ratio": comparison.speed_ratio,
        "data_quality": data_quality,
        "severity": severity,
        "pain_description": pain_description,
        "worst_segments": comparison.worst_segments,
        "metrics": metrics,
        "medical_scope": "motion-comparison-only",
    }
    result = review_pose(snapshot, settings)

    review = AIReview(
        attempt_id=attempt.id,
        provider=result.provider,
        model=result.model,
        prompt_version="pose-review-v1.0",
        verdict=result.payload.verdict,
        confidence=result.payload.confidence,
        summary=result.payload.summary,
        corrections=[item.model_dump(mode="json") for item in result.payload.corrections],
        safety_flags=result.payload.safety_flags,
        requires_review=result.payload.requires_review,
        validation_status=result.validation_status,
        latency_ms=result.latency_ms,
        fallback_used=result.fallback_used,
        input_snapshot=result.input_snapshot,
        output_snapshot=result.output_snapshot,
    )
    db.add(review)
    db.flush()

    if review.requires_review:
        reasons = list(review.safety_flags)
        if data_quality < 0.62:
            reasons.append(f"데이터 품질 부족({data_quality:.2f})")
        task = ReviewTask(
            review_id=review.id,
            reason=", ".join(reasons) or "AI 검수 결과 확인 필요",
            status="OPEN",
        )
        db.add(task)
        db.flush()
        notify_review_queue(
            settings.n8n_webhook_url,
            {
                "event": "rehab.review.created",
                "task_id": task.id,
                "attempt_id": attempt.id,
                "exercise": reference.name,
                "reason": task.reason,
                "similarity": attempt.overall_similarity,
                "data_quality": attempt.data_quality,
            },
        )

    db.commit()
    db.refresh(attempt)
    return attempt

