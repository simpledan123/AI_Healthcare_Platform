"""
Database Configuration for Physical AI Healthcare Platform
PostgreSQL 연결 및 SQLAlchemy 설정
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ----------------------------------------------------
# DB 접속 정보 설정 (🌟 환경변수 또는 직접 수정)
# ----------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "health_db")
DB_USER = os.getenv("DB_USER", "user_health")
DB_PASS = os.getenv("DB_PASS", "1234")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_size=10,
    max_overflow=20
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 Base 클래스
Base = declarative_base()

# Dependency: DB 세션 주입
def get_db():
    """FastAPI Dependency - DB 세션 생성 및 자동 정리"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()