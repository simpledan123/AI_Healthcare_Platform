from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .workout import Workout  # 같은 폴더의 workout.py에서 가져옴
#from .community import Post   # 같은 폴더의 community.py에서 가져옴

# [기본]
class UserBase(BaseModel):
    username: str
    email: str
    # AI 예측용 신체 데이터 (선택 사항)
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None

# [생성] 회원가입 시
class UserCreate(UserBase):
    pass
    # 실제로는 여기에 password 필드가 추가되어야 합니다.

# [응답] 내 정보 조회 시 (내 운동 기록, 내 글 목록 포함)
class User(UserBase):
    id: int
    created_at: datetime
    
    # 1:N 관계 데이터 포함 (기본값은 빈 리스트)
    logs: List[Workout] = []
    #posts: List[PostResponse] = []

    class Config:
        from_attributes = True