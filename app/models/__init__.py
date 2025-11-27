# app/models/__init__.py

from ..database import Base
from .user import User
from .workout import WorkoutLog
from .community import CommunityPost
# 재활 모델이 있다면 아래 주석 해제
from .rehabilitation import RehabilitationRecord