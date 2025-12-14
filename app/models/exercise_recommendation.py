# app/models/exercise_recommendation.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from ..database import Base
import enum


class DifficultyLevel(str, enum.Enum):
    """난이도 레벨"""
    EASY = "쉬움"
    MEDIUM = "보통"
    HARD = "어려움"


class ExerciseRecommendation(Base):
    """
    AI 추천 운동 상세 테이블 (정규화)
    
    RehabilitationRecord와 1:N 관계
    한 재활 기록에 여러 개의 운동이 추천됨
    """
    __tablename__ = "exercise_recommendations"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key - RehabilitationRecord 참조
    rehab_record_id = Column(
        Integer, 
        ForeignKey("rehabilitation_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 운동 기본 정보
    name = Column(String(200), nullable=False)  # 운동 이름
    description = Column(Text, nullable=False)  # 실행 방법 (단계별)
    
    # 운동 처방 (sets/reps 또는 duration)
    sets = Column(Integer, nullable=True)  # 세트 수 (근력 운동)
    reps = Column(Integer, nullable=True)  # 반복 횟수 (근력 운동)
    duration_seconds = Column(Integer, nullable=True)  # 유지 시간 (스트레칭)
    
    # 난이도 및 주의사항
    difficulty = Column(
        SQLEnum(DifficultyLevel),
        default=DifficultyLevel.EASY,
        nullable=False
    )
    cautions = Column(ARRAY(String), nullable=True)  # 주의사항 배열
    
    # 유튜브 참고 자료
    youtube_keywords = Column(ARRAY(String), nullable=True)  # 검색 키워드
    youtube_search_url = Column(String(500), nullable=True)  # 유튜브 검색 URL
    
    # Relationship
    rehab_record = relationship(
        "RehabilitationRecord", 
        back_populates="exercises"
    )
    
    def __repr__(self):
        return f"<ExerciseRecommendation(id={self.id}, name={self.name}, difficulty={self.difficulty})>"
