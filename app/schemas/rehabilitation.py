# app/schemas/rehabilitation.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# ============================================
# Request Schemas
# ============================================

class ExerciseRecommendationRequest(BaseModel):
    """AI 재활 운동 추천 요청"""
    user_id: int
    pain_area: str = Field(..., description="통증 부위 (예: 손목, 어깨, 허리, 무릎, 발목)")
    pain_description: Optional[str] = Field(None, description="통증에 대한 추가 설명")
    severity: int = Field(..., ge=1, le=10, description="통증 강도 (1-10)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "pain_area": "손목",
                "pain_description": "마우스 사용 후 시큰거림",
                "severity": 6
            }
        }


class SaveRehabRecordRequest(BaseModel):
    """재활 기록 저장 요청"""
    record_id: int
    completed: bool
    completion_notes: Optional[str] = None


# ============================================
# Response Schemas
# ============================================

class ExerciseDetail(BaseModel):
    """개별 운동 정보"""
    name: str
    description: str
    sets: int
    reps: int
    duration_seconds: Optional[int] = None  # 스트레칭 유지 시간
    cautions: List[str]
    difficulty: str = "초급"  # 초급, 중급, 고급
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "손목 신전 스트레칭",
                "description": "1. 팔을 앞으로 쭉 펴세요\n2. 반대 손으로 손등을 몸쪽으로 당기세요\n3. 15초간 유지하세요",
                "sets": 3,
                "reps": 10,
                "duration_seconds": 15,
                "cautions": ["통증이 심해지면 즉시 중단하세요", "천천히 부드럽게 진행하세요"],
                "difficulty": "초급"
            }
        }


class RehabilitationRecommendation(BaseModel):
    """AI 추천 결과"""
    pain_area: str
    severity: int
    exercises: List[ExerciseDetail]
    general_advice: str
    estimated_duration_minutes: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "pain_area": "손목",
                "severity": 6,
                "exercises": [
                    {
                        "name": "손목 신전 스트레칭",
                        "description": "팔을 앞으로 쭉 펴고...",
                        "sets": 3,
                        "reps": 10,
                        "duration_seconds": 15,
                        "cautions": ["무리하지 마세요"],
                        "difficulty": "초급"
                    }
                ],
                "general_advice": "하루 3회, 장시간 같은 자세 유지 후 실시하세요",
                "estimated_duration_minutes": 10
            }
        }


class RehabRecordResponse(BaseModel):
    """저장된 재활 기록 응답"""
    id: int
    user_id: int
    pain_area: str
    severity: int
    recommended_exercises: List[ExerciseDetail]
    completed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class RehabHistoryResponse(BaseModel):
    """사용자 재활 기록 목록"""
    total_records: int
    records: List[RehabRecordResponse]
