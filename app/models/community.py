# app/models/community.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class CommunityPost(Base):
    """커뮤니티 게시글 테이블"""
    __tablename__ = "community_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 게시글 기본 정보
    pain_area = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # 운동 타입
    exercise_type = Column(
        String(50), 
        nullable=False,
        index=True
    )  # 'ai_recommended', 'self_created', 'mixed'
    
    # 운동 상세 정보 (JSON)
    exercise_details = Column(JSONB, nullable=True)
    # 예시: [
    #   {
    #     "name": "손목 스트레칭",
    #     "sets": 3,
    #     "reps": 10,
    #     "my_modification": "나는 5초 더 유지했어요"
    #   }
    # ]
    
    # 효과 및 기간
    duration_days = Column(Integer, nullable=True)  # 며칠간 했는지
    effectiveness_rating = Column(Float, nullable=True)  # 1.0-5.0 효과 평점
    
    # 미디어
    images = Column(ARRAY(String), nullable=True)  # 이미지 URL 배열
    youtube_links = Column(ARRAY(String), nullable=True)  # 유튜브 링크 배열
    
    # 통계
    view_count = Column(Integer, default=0)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="community_posts")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")


class PostLike(Base):
    """게시글 좋아요 테이블"""
    __tablename__ = "post_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("CommunityPost", back_populates="likes")
    user = relationship("User", back_populates="post_likes")
    
    # 유니크 제약 (한 사용자가 같은 게시글에 중복 좋아요 방지)
    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='unique_post_like'),
    )


class PostComment(Base):
    """게시글 댓글 테이블"""
    __tablename__ = "post_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    post = relationship("CommunityPost", back_populates="comments")
    user = relationship("User", back_populates="comments")


# User 모델에 추가할 관계들:
# community_posts = relationship("CommunityPost", back_populates="user")
# post_likes = relationship("PostLike", back_populates="user")
# comments = relationship("PostComment", back_populates="user")
