# app/api/routers/rehabilitation.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# ⭐ 수정: 주석 해제 및 경로 수정
from app.schemas.rehabilitation import (
    ExerciseRecommendationRequest,
    RehabilitationRecommendation,
    SaveRehabRecordRequest,
    RehabRecordResponse,
    RehabHistoryResponse
)
from app.models.rehabilitation import RehabilitationRecord
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
    AI 기반 재활 운동 추천
    
    - **pain_area**: 통증 부위 (손목, 어깨, 허리, 무릎, 목, 발목)
    - **severity**: 통증 강도 (1-10)
    - **pain_description**: 추가 설명 (선택)
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
    
    # 3. DB에 기록 저장
    new_record = RehabilitationRecord(
        user_id=request.user_id,
        pain_area=request.pain_area,
        pain_description=request.pain_description,
        severity=request.severity,
        recommended_exercises=recommendation["exercises"],
        completed=False
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # 4. 응답 반환
    return RehabilitationRecommendation(**recommendation)


@router.get("/history/{user_id}", response_model=RehabHistoryResponse)
async def get_user_rehab_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    사용자의 재활 운동 기록 조회
    
    - **user_id**: 사용자 ID
    - **skip**: 건너뛸 레코드 수 (페이징)
    - **limit**: 가져올 최대 레코드 수
    """
    
    # 전체 레코드 수 조회
    total = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id
    ).count()
    
    # 레코드 조회 (최신순)
    records = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id
    ).order_by(
        RehabilitationRecord.created_at.desc()
    ).offset(skip).limit(limit).all()
    
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
    """
    재활 운동 완료 표시 및 피드백 저장
    
    - **record_id**: 재활 기록 ID
    - **completed**: 완료 여부
    - **completion_notes**: 사용자 피드백 (선택)
    """
    
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
    사용자의 재활 운동 통계
    
    - 총 추천 받은 횟수
    - 완료한 운동 횟수
    - 주요 통증 부위
    - 평균 통증 강도 변화
    """
    
    from sqlalchemy import func
    
    # 기본 통계
    total_records = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id
    ).count()
    
    completed_records = db.query(RehabilitationRecord).filter(
        RehabilitationRecord.user_id == user_id,
        RehabilitationRecord.completed == True
    ).count()
    
    # 주요 통증 부위 (빈도순)
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
    
    # 평균 통증 강도
    avg_severity = db.query(
        func.avg(RehabilitationRecord.severity)
    ).filter(
        RehabilitationRecord.user_id == user_id
    ).scalar()
    
    return {
        "user_id": user_id,
        "total_recommendations": total_records,
        "completed_exercises": completed_records,
        "completion_rate": round(completed_records / total_records * 100, 1) if total_records > 0 else 0,
        "top_pain_areas": [
            {"area": area, "count": count} for area, count in pain_areas
        ],
        "average_severity": round(avg_severity, 1) if avg_severity else 0
    }


@router.delete("/record/{record_id}")
async def delete_rehab_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """재활 기록 삭제"""
    
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
    
    return {"message": "재활 기록이 삭제되었습니다.", "record_id": record_id}