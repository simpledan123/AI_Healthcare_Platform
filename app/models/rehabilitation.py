# app/models/rehabilitation.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class RehabilitationRecord(Base):
    """
    재활 운동 기록 테이블 (정규화 버전)
    
    통증 정보만 저장하고, 추천 운동은 별도 테이블(ExerciseRecommendation)로 분리
    """
    __tablename__ = "rehabilitation_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 통증 정보
    pain_area = Column(String(100), nullable=False, index=True)  # 손목, 어깨, 허리 등
    pain_description = Column(Text, nullable=True)  # 추가 설명
    severity = Column(Integer, nullable=False)  # 1-10 통증 강도
    
    # 실행 여부
    completed = Column(Boolean, default=False)
    completion_notes = Column(Text, nullable=True)  # 사용자 피드백
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="rehabilitation_records")
    exercises = relationship(
        "ExerciseRecommendation",
        back_populates="rehab_record",
        cascade="all, delete-orphan",  # 재활 기록 삭제 시 운동도 함께 삭제
        lazy="joined"  # N+1 문제 방지 - 기본적으로 JOIN으로 가져오기
    )
    
    def __repr__(self):
        return f"<RehabilitationRecord(id={self.id}, pain_area={self.pain_area}, severity={self.severity})>"
