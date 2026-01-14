# app/api/routers/__init__.py

from . import rehabilitation
from . import pose_comparison
from . import infra
from . import community
from . import analytics  # 새로 추가

__all__ = [
    "rehabilitation",
    "pose_comparison",
    "infra",
    "community",
    "analytics",  # 새로 추가
]
