# app/api/routers/rehabilitation.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.schemas.rehabilitation import (
    ExerciseRecommendationRequest,
    RehabilitationRecommendation,
    SaveRehabRecordRequest,
    RehabRecordResponse,
    RehabHistoryResponse
)
from app.models.rehabilitation import RehabilitationRecord
from app.models.exercise_recommendation import ExerciseRecommendation, DifficultyLevel
from app.models.user import User
from app.database import get_db
from app.services.rehabilitation_ai import RehabilitationAI

router = APIRouter(
    prefix="/api/rehabilitation",
    tags=["Rehabilitation"]
)


@router.post("/recommend", response_model=RehabilitationRecommendation)
async def get_ai_recommendation(
    request: ExerciseRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    AI 기반 재활 운동 추천 (정규화 버전)
    
    - RehabilitationRecord에 통증 정보 저장
    - ExerciseRecommendation에 각 운동 개별 저장
    - 트랜잭션으로 원자성 보장
    """
    
    # 1. 사용자 존재 확인
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 2. AI 추천 생성
    recommendation = RehabilitationAI.generate_recommendation(
        pain_area=request.pain_area,
        pain_description=request.pain_description or "",
        severity=request.severity
    )
    
    try:
        # 3. DB에 저장 (트랜잭션)
        
        # 3-1. 재활 기록 생성 (통증 정보만)
        new_record = RehabilitationRecord(
            user_id=request.user_id,
            pain_area=request.pain_area,
            pain_description=request.pain_description,
            severity=request.severity,
            completed=False
        )
        db.add(new_record)
        db.flush()  # ID 생성 (commit은 아직 안 함)
        
        # 3-2. 추천 운동들 개별 저장
        for exercise_data in recommendation["exercises"]:
            exercise = ExerciseRecommendation(
                rehab_record_id=new_record.id,
                name=exercise_data["name"],
                description=exercise_data["description"],
                sets=exercise_data.get("sets"),
                reps=exercise_data.get("reps"),
                duration_seconds=exercise_data.get("duration_seconds"),
                difficulty=DifficultyLevel(exercise_data.get("difficulty", "쉬움")),
                cautions=exercise_data.get("cautions", []),
                youtube_keywords=exercise_data.get("youtube_keywords", []),
                youtube_search_url=exercise_data.get("youtube_search_url")
            )
            db.add(exercise)
        
        # 3-3. 커밋 (모두 성공 시)
        db.commit()
        db.refresh(new_record)
        
        # 4. 응답 반환
        return RehabilitationRecommendation(**recommendation)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"저장 중 오류 발생: {str(e)}"
        )


@router.get("/history/{user_id}", response_model=RehabHistoryResponse)
async def get_user_rehab_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    사용자의 재활 운동 기록 조회 (정규화 버전)
    
    JOIN으로 운동 목록까지 한 번에 가져오기 (N+1 문제 방지)
    """
    
    # 전체 레코드 수 조회
    total = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id
    ).count()
    
    # 레코드 + 운동 목록 조회 (Eager Loading)
    records = db.query(RehabilitationRecord)\
        .options(joinedload(RehabilitationRecord.exercises))\
        .filter(RehabilitationRecord.user_id == user_id)\
        .order_by(RehabilitationRecord.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return RehabHistoryResponse(
        total_records=total,
        records=records
    )


@router.patch("/complete/{record_id}")
async def mark_exercise_completed(
    record_id: int,
    request: SaveRehabRecordRequest,
    db: Session = Depends(get_db)
):
    """재활 운동 완료 표시 및 피드백 저장"""
    
    # 기록 조회
    record = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.id == record_id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="재활 기록을 찾을 수 없습니다."
        )
    
    # 완료 상태 업데이트
    record.completed = request.completed
    if request.completion_notes:
        record.completion_notes = request.completion_notes
    
    db.commit()
    db.refresh(record)
    
    return {
        "message": "재활 기록이 업데이트되었습니다.",
        "record_id": record_id,
        "completed": record.completed
    }


@router.get("/statistics/{user_id}")
async def get_user_rehab_statistics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    사용자의 재활 운동 통계 (정규화 버전)
    
    - 총 추천 받은 횟수
    - 완료한 운동 횟수
    - 주요 통증 부위
    - 가장 많이 추천된 운동 TOP 3
    """
    
    from sqlalchemy import func
    
    # 1. 기본 통계
    total_records = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id
    ).count()
    
    completed_records = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id,
        RehabilitationRecord.completed == True
    ).count()
    
    # 2. 주요 통증 부위 (빈도순)
    pain_areas = db.query(
        RehabilitationRecord.pain_area,
        func.count(RehabilitationRecord.id).label("count")
    ).filter(
        RehabilitationRecord.user_id == user_id
    ).group_by(
        RehabilitationRecord.pain_area
    ).order_by(
        func.count(RehabilitationRecord.id).desc()
    ).limit(3).all()
    
    # 3. 평균 통증 강도
    avg_severity = db.query(
        func.avg(RehabilitationRecord.severity)
    ).filter(
        RehabilitationRecord.user_id == user_id
    ).scalar()
    
    # 4. ⭐ 정규화의 장점: 가장 많이 추천된 운동 TOP 3 (JOIN 쿼리)
    top_exercises = db.query(
        ExerciseRecommendation.name,
        func.count(ExerciseRecommendation.id).label("count")
    ).join(
        RehabilitationRecord,
        ExerciseRecommendation.rehab_record_id == RehabilitationRecord.id
    ).filter(
        RehabilitationRecord.user_id == user_id
    ).group_by(
        ExerciseRecommendation.name
    ).order_by(
        func.count(ExerciseRecommendation.id).desc()
    ).limit(3).all()
    
    return {
        "user_id": user_id,
        "total_recommendations": total_records,
        "completed_exercises": completed_records,
        "completion_rate": round(completed_records / total_records * 100, 1) if total_records > 0 else 0,
        "top_pain_areas": [
            {"area": area, "count": count} for area, count in pain_areas
        ],
        "average_severity": round(avg_severity, 1) if avg_severity else 0,
        "most_recommended_exercises": [
            {"exercise_name": name, "count": count} for name, count in top_exercises
        ]
    }


@router.delete("/record/{record_id}")
async def delete_rehab_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    재활 기록 삭제
    
    Cascade delete로 연결된 운동들도 자동 삭제됨
    """
    
    record = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.id == record_id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="재활 기록을 찾을 수 없습니다."
        )
    
    db.delete(record)
    db.commit()
    
    return {
        "message": "재활 기록 및 관련 운동이 삭제되었습니다.",
        "record_id": record_id
    }


@router.get("/exercise-analysis/{pain_area}")
async def analyze_exercises_by_area(
    pain_area: str,
    db: Session = Depends(get_db)
):
    """
    ⭐ 정규화의 장점: 부위별 운동 분석
    
    특정 부위에 대해 어떤 운동이 가장 많이 추천되는지 분석
    (JSONB 구조에서는 쿼리하기 어려움)
    """
    
    from sqlalchemy import func
    
    exercise_stats = db.query(
        ExerciseRecommendation.name,
        func.count(ExerciseRecommendation.id).label("recommended_count"),
        func.avg(RehabilitationRecord.severity).label("avg_severity"),
        ExerciseRecommendation.difficulty
    ).join(
        RehabilitationRecord,
        ExerciseRecommendation.rehab_record_id == RehabilitationRecord.id
    ).filter(
        RehabilitationRecord.pain_area == pain_area
    ).group_by(
        ExerciseRecommendation.name,
        ExerciseRecommendation.difficulty
    ).order_by(
        func.count(ExerciseRecommendation.id).desc()
    ).limit(10).all()
    
    return {
        "pain_area": pain_area,
        "analysis": [
            {
                "exercise_name": name,
                "recommended_count": count,
                "avg_pain_severity": round(avg_sev, 1) if avg_sev else 0,
                "difficulty": difficulty.value
            }
            for name, count, avg_sev, difficulty in exercise_stats
        ]
    }
