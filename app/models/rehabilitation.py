# app/models.py에 추가할 RehabilitationRecord 모델

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

# 기존 Base를 import 한다고 가정
# from app.database import Base

class RehabilitationRecord(Base):
    """재활 운동 기록 테이블"""
    __tablename__ = "rehabilitation_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 통증 정보
    pain_area = Column(String(100), nullable=False)  # 손목, 어깨, 허리 등
    pain_description = Column(Text, nullable=True)    # 추가 설명
    severity = Column(Integer, nullable=False)        # 1-10 통증 강도
    
    # AI 추천 결과 (JSON 형태로 저장)
    recommended_exercises = Column(JSONB, nullable=False)
    # 예시: [
    #   {
    #     "name": "손목 신전 스트레칭",
    #     "description": "팔을 앞으로 쭉 펴고...",
    #     "sets": 3,
    #     "reps": 10,
    #     "cautions": ["무리하지 마세요"]
    #   }
    # ]
    
    # 실행 여부
    completed = Column(Boolean, default=False)
    completion_notes = Column(Text, nullable=True)    # 사용자 피드백
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="rehabilitation_records")


# User 모델에도 다음 관계를 추가해야 함:
# rehabilitation_records = relationship("RehabilitationRecord", back_populates="user")
