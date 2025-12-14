# app/models/__init__.py

from ..database import Base
from .user import User
from .workout import WorkoutLog
from .community import CommunityPost, PostLike, PostComment
from .rehabilitation import RehabilitationRecord
from .exercise_recommendation import ExerciseRecommendation  # 추가!
