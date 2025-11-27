from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models import Base
# 라우터들 import
from .api.routers import users, community, infra, rehabilitation

# 1. DB 테이블 생성 (Alembic을 쓰더라도 개발 편의상 둠)
Base.metadata.create_all(bind=engine)

# 2. FastAPI 앱 생성
app = FastAPI(
    title="Physical AI Healthcare Platform",
    description="Integrated System for Health & Infrastructure",
    version="1.0.0"
)

# 3. CORS 설정 (앱 생성 직후에!)
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 라우터 등록
app.include_router(users.router)
app.include_router(community.router)
app.include_router(infra.router)
app.include_router(rehabilitation.router)

@app.get("/")
def root():
    return {"message": "Physical AI Healthcare Server is Running! 🚀"}