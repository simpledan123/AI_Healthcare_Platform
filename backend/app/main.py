from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .config import Settings, get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import AIReview, PoseAttempt, ReferenceExercise, ReviewTask
from .schemas import (
    AttemptOut,
    DashboardOut,
    ReferenceOut,
    ResolveTaskRequest,
    ReviewTaskOut,
)
from .seed import seed_demo_reference
from .services.demo_data import user_wrist_sequence
from .services.video_pose import extract_right_wrist_features
from .services.workflow import run_motion_review


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_reference(db)
    yield


app = FastAPI(
    title="AI Rehabilitation Motion Review",
    description=(
        "MediaPipe Pose+Hands, DTW alignment, evidence-bound AI review, "
        "audit logging, and human review workflow."
    ),
    version="2.0.0",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _attempt_out(attempt: PoseAttempt) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        reference_id=attempt.reference_id,
        reference_name=attempt.reference.name,
        mode=attempt.mode,
        status=attempt.status,
        severity=attempt.severity,
        overall_similarity=attempt.overall_similarity,
        dtw_distance=attempt.dtw_distance,
        speed_ratio=attempt.speed_ratio,
        data_quality=attempt.data_quality,
        worst_segments=attempt.worst_segments,
        metrics=attempt.metrics,
        created_at=attempt.created_at,
        review=attempt.review,
    )


def _load_attempt(db: Session, attempt_id: int) -> PoseAttempt:
    attempt = (
        db.query(PoseAttempt)
        .options(
            joinedload(PoseAttempt.reference),
            joinedload(PoseAttempt.review),
        )
        .filter(PoseAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="분석 기록을 찾을 수 없습니다.")
    return attempt


async def _temporary_video(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "video.mp4")[1] or ".mp4"
    content = await upload.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="영상은 50MB 이하만 업로드할 수 있습니다.")
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(content)
        return handle.name
    finally:
        handle.close()


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "version": "2.0.0",
        "ai_review_mode": settings.ai_review_mode,
        "demo_data": True,
    }


@app.get("/api/meta")
def meta() -> dict:
    return {
        "project": "AI Rehabilitation Motion Review",
        "purpose": "전문가 동작과 사용자 동작을 비교하고 측정 근거에 한정해 AI 피드백을 검수합니다.",
        "ai_review_mode": settings.ai_review_mode,
        "demo_notice": (
            "데모 실행은 합성 포즈 특징을 사용합니다. 실제 영상 분석은 Pose+Hands 특징만 저장하고 "
            "원본 임시 파일을 즉시 삭제합니다."
        ),
        "medical_notice": "본 서비스는 의료 진단이나 치료를 제공하지 않는 동작 비교 프로토타입입니다.",
    }


@app.get("/api/references", response_model=list[ReferenceOut])
def list_references(db: Session = Depends(get_db)):
    return db.query(ReferenceExercise).order_by(ReferenceExercise.created_at.asc()).all()


@app.post("/api/references/import-video", response_model=ReferenceOut)
async def import_reference_video(
    video: UploadFile = File(...),
    exercise_id: str = Form(...),
    name: str = Form(...),
    body_part: str = Form("손목"),
    description: str = Form(...),
    version: str = Form("1.0"),
    approved: bool = Form(False),
    db: Session = Depends(get_db),
):
    path = await _temporary_video(video)
    try:
        extracted = extract_right_wrist_features(path)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if os.path.exists(path):
            os.remove(path)

    reference = db.get(ReferenceExercise, exercise_id)
    if reference is None:
        reference = ReferenceExercise(id=exercise_id)
        db.add(reference)
    reference.name = name
    reference.body_part = body_part
    reference.description = description
    reference.version = version
    reference.sequence = extracted.sequence
    reference.feature_names = extracted.metrics["feature_names"]
    reference.source_type = "expert_video"
    reference.approved = approved
    db.commit()
    db.refresh(reference)
    return reference


@app.post("/api/attempts/demo", response_model=AttemptOut)
def run_demo(
    severity: int = 3,
    pain_description: str = "",
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
):
    if severity < 1 or severity > 10:
        raise HTTPException(status_code=422, detail="severity는 1~10이어야 합니다.")
    reference = seed_demo_reference(db)
    attempt = run_motion_review(
        db,
        app_settings,
        reference,
        user_wrist_sequence(),
        data_quality=0.91,
        mode="demo",
        severity=severity,
        pain_description=pain_description,
        extraction_metrics={
            "data_source": "deterministic_synthetic_demo",
            "demo_labeled": True,
            "raw_video_stored": False,
        },
    )
    return _attempt_out(_load_attempt(db, attempt.id))


@app.post("/api/attempts/analyze", response_model=AttemptOut)
async def analyze_user_video(
    video: UploadFile = File(...),
    reference_id: str = Form(...),
    severity: int = Form(3),
    pain_description: str = Form(""),
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
):
    if severity < 1 or severity > 10:
        raise HTTPException(status_code=422, detail="severity는 1~10이어야 합니다.")
    reference = db.get(ReferenceExercise, reference_id)
    if not reference:
        raise HTTPException(status_code=404, detail="전문가 기준 동작을 찾을 수 없습니다.")

    path = await _temporary_video(video)
    try:
        extracted = extract_right_wrist_features(path)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if os.path.exists(path):
            os.remove(path)

    attempt = run_motion_review(
        db,
        app_settings,
        reference,
        extracted.sequence,
        data_quality=extracted.data_quality,
        mode="video",
        severity=severity,
        pain_description=pain_description,
        extraction_metrics={
            **extracted.metrics,
            "data_source": "uploaded_user_video",
            "raw_video_stored": False,
        },
    )
    return _attempt_out(_load_attempt(db, attempt.id))


@app.get("/api/attempts/{attempt_id}", response_model=AttemptOut)
def get_attempt(attempt_id: int, db: Session = Depends(get_db)):
    return _attempt_out(_load_attempt(db, attempt_id))


@app.get("/api/review-tasks", response_model=list[ReviewTaskOut])
def list_review_tasks(db: Session = Depends(get_db)):
    tasks = (
        db.query(ReviewTask)
        .options(
            joinedload(ReviewTask.review)
            .joinedload(AIReview.attempt)
            .joinedload(PoseAttempt.reference)
        )
        .order_by(ReviewTask.created_at.desc())
        .all()
    )
    return [
        ReviewTaskOut(
            id=task.id,
            review_id=task.review_id,
            attempt_id=task.review.attempt_id,
            reference_name=task.review.attempt.reference.name,
            reason=task.reason,
            status=task.status,
            reviewer_note=task.reviewer_note,
            created_at=task.created_at,
            resolved_at=task.resolved_at,
        )
        for task in tasks
    ]


@app.patch("/api/review-tasks/{task_id}", response_model=ReviewTaskOut)
def resolve_review_task(
    task_id: int,
    request: ResolveTaskRequest,
    db: Session = Depends(get_db),
):
    task = (
        db.query(ReviewTask)
        .options(
            joinedload(ReviewTask.review)
            .joinedload(AIReview.attempt)
            .joinedload(PoseAttempt.reference)
        )
        .filter(ReviewTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="검토 작업을 찾을 수 없습니다.")
    task.status = request.status
    task.reviewer_note = request.reviewer_note
    task.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return ReviewTaskOut(
        id=task.id,
        review_id=task.review_id,
        attempt_id=task.review.attempt_id,
        reference_name=task.review.attempt.reference.name,
        reason=task.reason,
        status=task.status,
        reviewer_note=task.reviewer_note,
        created_at=task.created_at,
        resolved_at=task.resolved_at,
    )


@app.get("/api/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    total = db.query(func.count(PoseAttempt.id)).scalar() or 0
    demo_count = db.query(func.count(PoseAttempt.id)).filter(PoseAttempt.mode == "demo").scalar() or 0
    avg_similarity = db.query(func.avg(PoseAttempt.overall_similarity)).scalar() or 0
    avg_quality = db.query(func.avg(PoseAttempt.data_quality)).scalar() or 0
    review_total = db.query(func.count(AIReview.id)).scalar() or 0
    fallback_count = db.query(func.count(AIReview.id)).filter(AIReview.fallback_used.is_(True)).scalar() or 0
    open_tasks = db.query(func.count(ReviewTask.id)).filter(ReviewTask.status == "OPEN").scalar() or 0

    distribution = []
    counts: dict[str, int] = {}
    for verdict, count in db.query(AIReview.verdict, func.count(AIReview.id)).group_by(AIReview.verdict):
        counts[verdict] = count
        distribution.append({"verdict": verdict, "count": count})

    recent = (
        db.query(PoseAttempt)
        .options(joinedload(PoseAttempt.reference), joinedload(PoseAttempt.review))
        .order_by(PoseAttempt.created_at.desc())
        .limit(8)
        .all()
    )
    recent_payload = [
        {
            "id": item.id,
            "exercise": item.reference.name,
            "mode": item.mode,
            "similarity": item.overall_similarity,
            "quality": item.data_quality,
            "verdict": item.review.verdict,
            "requires_review": item.review.requires_review,
            "created_at": item.created_at.isoformat(),
        }
        for item in recent
    ]

    denominator = review_total or 1
    return DashboardOut(
        total_attempts=total,
        demo_attempts=demo_count,
        average_similarity=round(float(avg_similarity), 2),
        average_quality=round(float(avg_quality), 3),
        pass_rate=round(counts.get("PASS", 0) / denominator * 100, 1),
        retry_rate=round(counts.get("RETRY", 0) / denominator * 100, 1),
        review_rate=round(counts.get("REVIEW", 0) / denominator * 100, 1),
        fallback_rate=round(fallback_count / denominator * 100, 1),
        open_review_tasks=open_tasks,
        recent_attempts=recent_payload,
        verdict_distribution=distribution,
    )

