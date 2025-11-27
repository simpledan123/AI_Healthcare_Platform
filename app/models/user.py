"""
User Model - 사용자 정보 및 프로필
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # OAuth 사용 시 null 가능
    
    # 신체 정보 (재활 추천에 활용)
    age = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    occupation = Column(String(100), nullable=True)  # 직업 (사무직, 개발자 등)
    
    # 상태
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계 설정
    pain_records = relationship("PainRecord", back_populates="user")
    exercise_logs = relationship("ExerciseLog", back_populates="user")
    community_posts = relationship("CommunityPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")