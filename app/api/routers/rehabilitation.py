# app/api/routers/rehabilitation.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.schemas.rehabilitation import (
    ExerciseRecommendationRequest,
    RehabilitationRecommendation,
    SaveRehabRecordRequest,
    RehabHistoryResponse,
    PainAreaPredictionRequest,
    PainAreaPredictionResponse,
    PainAreaCandidate,
)

from app.models.rehabilitation import RehabilitationRecord
from app.models.exercise_recommendation import ExerciseRecommendation, DifficultyLevel
from app.models.user import User
from app.database import get_db

from app.services.rehab_recommender import generate_rehab_recommendation
from app.services.hf_models.rehab_json_generator import (
    generate_local_rehab_recommendation,
    LocalRehabModelUnavailable,
)
from app.services.hf_models.pain_area_classifier import predict_pain_area


router = APIRouter(prefix="/api/rehabilitation", tags=["Rehabilitation"])


def _youtube_search_url(primary_keyword: str) -> str:
    q = (primary_keyword or "").strip().replace(" ", "+")
    return f"https://www.youtube.com/results?search_query={q}"


def _difficulty_safe(value: str) -> DifficultyLevel:
    v = (value or "").strip()
    if v in ("쉬움", "보통", "어려움"):
        return DifficultyLevel(v)
    mapping = {"초급": "쉬움", "중급": "보통", "고급": "어려움"}
    return DifficultyLevel(mapping.get(v, "쉬움"))


def _ensure_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


def _resolve_pain_area(pain_area: str, pain_description: str) -> str:
    pa = (pain_area or "").strip()
    if pa.upper() != "AUTO":
        return pa

    if not pain_description or not pain_description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pain_area='AUTO' 인 경우 pain_description 이 필요합니다.",
        )

    pred = predict_pain_area(pain_description, top_k=1)
    return pred.predicted_label


def _persist_recommendation(
    db: Session,
    user_id: int,
    pain_area: str,
    pain_description: str,
    severity: int,
    recommendation: dict,
):
    """
    RehabilitationRecord + ExerciseRecommendation 저장 공통 로직
    """
    # 서버 기준 pain_area/severity 최종 고정
    recommendation["pain_area"] = pain_area
    recommendation["severity"] = severity

    new_record = RehabilitationRecord(
        user_id=user_id,
        pain_area=pain_area,
        pain_description=pain_description,
        severity=severity,
        completed=False,
    )
    db.add(new_record)
    db.flush()  # ID 확보

    for ex in recommendation.get("exercises", []):
        yk = ex.get("youtube_keywords") or []
        youtube_search_url = ex.get("youtube_search_url")
        if not youtube_search_url and isinstance(yk, list) and len(yk) > 0:
            youtube_search_url = _youtube_search_url(yk[0])

        exercise = ExerciseRecommendation(
            rehab_record_id=new_record.id,
            name=ex["name"],
            description=ex["description"],
            sets=ex.get("sets"),
            reps=ex.get("reps"),
            duration_seconds=ex.get("duration_seconds"),
            difficulty=_difficulty_safe(ex.get("difficulty", "쉬움")),
            cautions=ex.get("cautions", []),
            youtube_keywords=yk,
            youtube_search_url=youtube_search_url,
        )
        db.add(exercise)

    db.commit()
    db.refresh(new_record)


@router.post("/pain-area/predict", response_model=PainAreaPredictionResponse)
async def predict_pain_area_api(request: PainAreaPredictionRequest):
    """
    통증 설명(text) -> 통증 부위 분류(HF fine-tuned model 우선, 없으면 heuristic fallback)
    """
    pred = predict_pain_area(request.text, top_k=request.top_k)
    return PainAreaPredictionResponse(
        predicted_label=pred.predicted_label,
        engine=pred.engine,
        candidates=[PainAreaCandidate(label=c.label, score=c.score) for c in pred.candidates],
    )


@router.post("/recommend", response_model=RehabilitationRecommendation)
async def get_ai_recommendation(request: ExerciseRecommendationRequest, db: Session = Depends(get_db)):
    """
    기본은 Claude 추천(기존 기능 유지)
    단, REHAB_REC_ENGINE 환경변수로 로컬 LoRA를 '옵션'으로 선택/폴백 가능.
      - claude (default): 기존 그대로
      - local: 로컬만
      - claude_then_local / local_then_claude: 폴백 체인
    """
    _ensure_user(db, request.user_id)

    pain_area = _resolve_pain_area(request.pain_area, request.pain_description or "")
    pain_description = request.pain_description or ""
    severity = request.severity

    try:
        recommendation = generate_rehab_recommendation(
            pain_area=pain_area,
            pain_description=pain_description,
            severity=severity,
        )
    except LocalRehabModelUnavailable as e:
        # 엔진이 local 계열로 설정되어 있는데 로컬 모델이 없으면 503
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"추천 생성 오류: {str(e)}")

    try:
        _persist_recommendation(
            db=db,
            user_id=request.user_id,
            pain_area=pain_area,
            pain_description=pain_description,
            severity=severity,
            recommendation=recommendation,
        )
        return RehabilitationRecommendation(**recommendation)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"저장 중 오류 발생: {str(e)}")


@router.post("/recommend-local", response_model=RehabilitationRecommendation)
async def get_local_recommendation(request: ExerciseRecommendationRequest, db: Session = Depends(get_db)):
    """
    로컬 LoRA 추천 (덤 기능 / 명시적 엔드포인트)
    - Claude 추천 기능은 그대로 두고, 로컬 모델은 별도 엔드포인트에서만 "강제" 사용
    - 로컬 모델이 없으면 503 반환
    """
    _ensure_user(db, request.user_id)

    pain_area = _resolve_pain_area(request.pain_area, request.pain_description or "")
    pain_description = request.pain_description or ""
    severity = request.severity

    try:
        recommendation = generate_local_rehab_recommendation(
            pain_area=pain_area,
            pain_description=pain_description,
            severity=severity,
        )
    except LocalRehabModelUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"로컬 추천 생성 오류: {str(e)}")

    try:
        _persist_recommendation(
            db=db,
            user_id=request.user_id,
            pain_area=pain_area,
            pain_description=pain_description,
            severity=severity,
            recommendation=recommendation,
        )
        return RehabilitationRecommendation(**recommendation)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"저장 중 오류 발생: {str(e)}")


@router.get("/history/{user_id}", response_model=RehabHistoryResponse)
async def get_user_rehab_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    total = db.query(RehabilitationRecord).filter(RehabilitationRecord.user_id == user_id).count()

    records = (
        db.query(RehabilitationRecord)
        .options(joinedload(RehabilitationRecord.exercises))
        .filter(RehabilitationRecord.user_id == user_id)
        .order_by(RehabilitationRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return RehabHistoryResponse(total_records=total, records=records)


@router.patch("/complete/{record_id}")
async def mark_exercise_completed(record_id: int, request: SaveRehabRecordRequest, db: Session = Depends(get_db)):
    record = db.query(RehabilitationRecord).filter(RehabilitationRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="재활 기록을 찾을 수 없습니다.")

    record.completed = request.completed
    if request.completion_notes:
        record.completion_notes = request.completion_notes

    db.commit()
    db.refresh(record)
    return {"message": "재활 기록이 업데이트되었습니다.", "record_id": record_id, "completed": record.completed}


@router.get("/statistics/{user_id}")
async def get_user_rehab_statistics(user_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import func

    total_records = db.query(RehabilitationRecord).filter(RehabilitationRecord.user_id == user_id).count()

    completed_records = (
        db.query(RehabilitationRecord)
        .filter(RehabilitationRecord.user_id == user_id, RehabilitationRecord.completed == True)
        .count()
    )

    pain_areas = (
        db.query(RehabilitationRecord.pain_area, func.count(RehabilitationRecord.id).label("count"))
        .filter(RehabilitationRecord.user_id == user_id)
        .group_by(RehabilitationRecord.pain_area)
        .order_by(func.count(RehabilitationRecord.id).desc())
        .limit(3)
        .all()
    )

    avg_severity = (
        db.query(func.avg(RehabilitationRecord.severity))
        .filter(RehabilitationRecord.user_id == user_id)
        .scalar()
    )

    top_exercises = (
        db.query(ExerciseRecommendation.name, func.count(ExerciseRecommendation.id).label("count"))
        .join(RehabilitationRecord, ExerciseRecommendation.rehab_record_id == RehabilitationRecord.id)
        .filter(RehabilitationRecord.user_id == user_id)
        .group_by(ExerciseRecommendation.name)
        .order_by(func.count(ExerciseRecommendation.id).desc())
        .limit(3)
        .all()
    )

    return {
        "user_id": user_id,
        "total_recommendations": total_records,
        "completed_exercises": completed_records,
        "completion_rate": round(completed_records / total_records * 100, 1) if total_records > 0 else 0,
        "top_pain_areas": [{"area": area, "count": count} for area, count in pain_areas],
        "average_severity": round(avg_severity, 1) if avg_severity else 0,
        "most_recommended_exercises": [{"exercise_name": name, "count": count} for name, count in top_exercises],
    }


@router.delete("/record/{record_id}")
async def delete_rehab_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(RehabilitationRecord).filter(RehabilitationRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="재활 기록을 찾을 수 없습니다.")

    db.delete(record)
    db.commit()
    return {"message": "재활 기록 및 관련 운동이 삭제되었습니다.", "record_id": record_id}


@router.get("/exercise-analysis/{pain_area}")
async def analyze_exercises_by_area(pain_area: str, db: Session = Depends(get_db)):
    from sqlalchemy import func

    exercise_stats = (
        db.query(
            ExerciseRecommendation.name,
            func.count(ExerciseRecommendation.id).label("recommended_count"),
            func.avg(RehabilitationRecord.severity).label("avg_severity"),
            ExerciseRecommendation.difficulty,
        )
        .join(RehabilitationRecord, ExerciseRecommendation.rehab_record_id == RehabilitationRecord.id)
        .filter(RehabilitationRecord.pain_area == pain_area)
        .group_by(ExerciseRecommendation.name, ExerciseRecommendation.difficulty)
        .order_by(func.count(ExerciseRecommendation.id).desc())
        .limit(10)
        .all()
    )

    return {
        "pain_area": pain_area,
        "analysis": [
            {
                "exercise_name": name,
                "recommended_count": count,
                "avg_pain_severity": round(avg_sev, 1) if avg_sev else 0,
                "difficulty": difficulty.value,
            }
            for name, count, avg_sev, difficulty in exercise_stats
        ],
    }