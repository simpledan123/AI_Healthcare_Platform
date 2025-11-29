from ..database import Base
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # 외래 키 (Foreign Key): users 테이블의 id를 참조
    user_id = Column(Integer, ForeignKey("users.id"))
    
    activity_type = Column(String)  # 예: Running, Cycling, Yoga
    duration_minutes = Column(Integer)
    calories_burned = Column(Float)
    
    # 시계열 분석(Time Series)의 핵심 기준점
    logged_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정 (User 테이블과 연결)
    owner = relationship("User", back_populates="workout_logs")