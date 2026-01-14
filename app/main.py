# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 개별 임포트 대신 통합된 api_router를 임포트합니다.
from app.api import api_router

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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록: 개별 등록 대신 api_router 하나로 모든 경로를 등록합니다.
# /api/v1 등의 프리픽스를 붙여 버전 관리를 할 수도 있습니다.
app.include_router(api_router)

@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Physical AI Healthcare Platform API",
        "version": "1.0.0",
        "status": "online"
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
    # 개별 경로 로그는 api_router 설정에 따라 자동으로 관리되므로 
    # 여기서는 서비스 시작 메시지만 간단히 출력해도 충분합니다.
    logger.info("API System Ready")
    logger.info("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("Shutting down Physical AI Healthcare Platform API...")