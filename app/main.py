# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routers import (
    rehabilitation,
    pose_comparison,
    infra,
    community,
    analytics  # 새로 추가
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Physical AI Healthcare Platform API",
    description="재활운동 AI 추천 및 자세 분석 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(
    rehabilitation.router,
    prefix="/rehabilitation",
    tags=["Rehabilitation AI"]
)

app.include_router(
    pose_comparison.router,
    prefix="/pose",
    tags=["Pose Comparison"]
)

app.include_router(
    infra.router,
    prefix="/infra",
    tags=["Infrastructure Monitoring"]
)

app.include_router(
    community.router,
    prefix="/community",
    tags=["Community"]
)

app.include_router(
    analytics.router,  # 새로 추가!
    prefix="/analytics",
    tags=["Analytics & Statistics"]
)


@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Physical AI Healthcare Platform API",
        "version": "1.0.0",
        "endpoints": {
            "rehabilitation": "/rehabilitation",
            "pose_comparison": "/pose",
            "infrastructure": "/infra",
            "community": "/community",
            "analytics": "/analytics",  # 새로 추가!
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "services": {
            "rehabilitation_ai": "running",
            "pose_analysis": "running",
            "traffic_prediction": "running",
            "analytics": "running"
        }
    }


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("=" * 50)
    logger.info("Physical AI Healthcare Platform API Starting...")
    logger.info("=" * 50)
    logger.info("Available routes:")
    logger.info("  - Rehabilitation AI: /rehabilitation")
    logger.info("  - Pose Comparison: /pose")
    logger.info("  - Infrastructure: /infra")
    logger.info("  - Community: /community")
    logger.info("  - Analytics: /analytics")  # 새로 추가!
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("Shutting down Physical AI Healthcare Platform API...")
