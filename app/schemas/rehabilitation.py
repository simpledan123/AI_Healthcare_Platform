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
    pain_area: str = Field(..., description="통증 부위 (예: 손목, 어깨, 허리, 무릎, 발목) 또는 'AUTO'")
    pain_description: Optional[str] = Field(None, description="통증에 대한 추가 설명")
    severity: int = Field(..., ge=1, le=10, description="통증 강도 (1-10)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "pain_area": "AUTO",
                "pain_description": "마우스 사용 후 손목이 시큰거리고 찌릿함",
                "severity": 6,
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
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None  # 스트레칭 유지 시간
    cautions: List[str] = []
    difficulty: str = "쉬움"
    youtube_keywords: List[str] = []
    youtube_search_url: Optional[str] = None


class RehabilitationRecommendation(BaseModel):
    """AI 추천 결과"""

    pain_area: str
    severity: int
    exercises: List[ExerciseDetail]
    general_advice: str
    estimated_duration_minutes: int


class RehabRecordResponse(BaseModel):
    """저장된 재활 기록 응답"""

    id: int
    user_id: int
    pain_area: str
    severity: int
    recommended_exercises: List[ExerciseDetail] = []
    completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RehabHistoryResponse(BaseModel):
    """사용자 재활 기록 목록"""

    total_records: int
    records: List[RehabRecordResponse]


# ============================================
# NEW: Pain Area Prediction Schemas
# ============================================
class PainAreaPredictionRequest(BaseModel):
    text: str = Field(..., description="통증 설명 문장")
    top_k: int = Field(3, ge=1, le=10, description="상위 후보 개수")


class PainAreaCandidate(BaseModel):
    label: str
    score: float


class PainAreaPredictionResponse(BaseModel):
    predicted_label: str
    engine: str  # "hf" | "heuristic"
    candidates: List[PainAreaCandidate]