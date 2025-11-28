# app/schemas/community.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============================================
# Request Schemas
# ============================================

class CreatePostRequest(BaseModel):
    """커뮤니티 게시글 작성 요청"""
    user_id: int
    pain_area: str
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=10)
    exercise_type: str = Field(..., description="ai_recommended, self_created, mixed")
    exercise_details: Optional[List[dict]] = None
    duration_days: Optional[int] = Field(None, ge=1, description="며칠간 수행했는지")
    effectiveness_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    images: Optional[List[str]] = None
    youtube_links: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "pain_area": "손목",
                "title": "AI 추천 손목 스트레칭 2주 후기",
                "content": "AI가 추천해준 손목 스트레칭을 2주간 꾸준히 했더니 통증이 많이 줄었어요!",
                "exercise_type": "ai_recommended",
                "exercise_details": [
                    {
                        "name": "손목 신전 스트레칭",
                        "sets": 3,
                        "reps": 10,
                        "my_note": "아침저녁으로 했어요"
                    }
                ],
                "duration_days": 14,
                "effectiveness_rating": 4.5,
                "youtube_links": ["https://youtube.com/watch?v=example"]
            }
        }


class CommentRequest(BaseModel):
    """댓글 작성 요청"""
    user_id: int
    content: str = Field(..., min_length=1, max_length=500)


# ============================================
# Response Schemas
# ============================================

class UserBasicInfo(BaseModel):
    """사용자 기본 정보"""
    id: int
    username: str
    profile_image: Optional[str] = None
    
    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    """게시글 응답 (목록용)"""
    id: int
    user: UserBasicInfo
    pain_area: str
    title: str
    content: str
    exercise_type: str
    duration_days: Optional[int]
    effectiveness_rating: Optional[float]
    view_count: int
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostDetailResponse(BaseModel):
    """게시글 상세 응답"""
    id: int
    user: UserBasicInfo
    pain_area: str
    title: str
    content: str
    exercise_type: str
    exercise_details: Optional[List[dict]]
    duration_days: Optional[int]
    effectiveness_rating: Optional[float]
    images: Optional[List[str]]
    youtube_links: Optional[List[str]]
    view_count: int
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """댓글 응답"""
    id: int
    user: UserBasicInfo
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    """게시글 목록 응답"""
    total_posts: int
    posts: List[PostResponse]
