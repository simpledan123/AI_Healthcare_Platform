# app/api/__init__.py

"""
API Module
모든 엔드포인트 라우터를 통합하는 패키지 초기화 파일
"""

from fastapi import APIRouter
from app.api.routers import (
    users,
    workout,
    rehabilitation,
    community,
    pose_comparison,
    analytics,
    infra
)

# 메인 API 라우터 생성
api_router = APIRouter()

# 각 도메인별 라우터 등록
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(workout.router, prefix="/workout", tags=["workout"])
api_router.include_router(rehabilitation.router, prefix="/rehabilitation", tags=["rehabilitation"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(pose_comparison.router, prefix="/pose", tags=["pose-analysis"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(infra.router, prefix="/infra", tags=["infrastructure"])