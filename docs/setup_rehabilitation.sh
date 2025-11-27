#!/bin/bash
# setup_rehabilitation.sh
# AI 재활 운동 추천 기능 자동 설치 스크립트

echo "🏥 AI 재활 운동 추천 기능 설치를 시작합니다..."

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 백엔드 패키지 설치
echo -e "${YELLOW}📦 백엔드 패키지 설치 중...${NC}"
pip install anthropic>=0.7.0 --break-system-packages

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 백엔드 패키지 설치 완료${NC}"
else
    echo -e "${RED}❌ 백엔드 패키지 설치 실패${NC}"
    exit 1
fi

# 2. 프론트엔드 패키지 설치
echo -e "${YELLOW}📦 프론트엔드 패키지 설치 중...${NC}"
cd frontend
npm install axios

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 프론트엔드 패키지 설치 완료${NC}"
else
    echo -e "${RED}❌ 프론트엔드 패키지 설치 실패${NC}"
    exit 1
fi
cd ..

# 3. 환경 변수 설정 확인
echo -e "${YELLOW}🔑 환경 변수 확인 중...${NC}"
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}⚠️  경고: ANTHROPIC_API_KEY가 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}다음 명령어로 설정하세요:${NC}"
    echo "export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here"
    echo ""
    read -p "API 키를 입력하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "API 키를 입력하세요: " api_key
        export ANTHROPIC_API_KEY=$api_key
        echo "export ANTHROPIC_API_KEY=$api_key" >> ~/.bashrc
        echo -e "${GREEN}✅ API 키가 설정되었습니다${NC}"
    fi
else
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY 설정 완료${NC}"
fi

# 4. 데이터베이스 마이그레이션
echo -e "${YELLOW}🗄️  데이터베이스 마이그레이션 실행 중...${NC}"
alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 데이터베이스 마이그레이션 완료${NC}"
else
    echo -e "${RED}❌ 데이터베이스 마이그레이션 실패${NC}"
    echo -e "${YELLOW}다음 명령어를 수동으로 실행하세요:${NC}"
    echo "alembic upgrade head"
fi

# 5. 파일 구조 생성
echo -e "${YELLOW}📁 파일 구조 생성 중...${NC}"
mkdir -p app/schemas app/services app/routers
mkdir -p frontend/src/api frontend/src/components frontend/src/pages

echo -e "${GREEN}✅ 파일 구조 생성 완료${NC}"

# 6. 설치 완료 메시지
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 AI 재활 운동 추천 기능 설치 완료!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📋 다음 단계:${NC}"
echo ""
echo "1. 제공된 파일들을 해당 경로에 복사하세요:"
echo "   - app/models.py에 RehabilitationRecord 모델 추가"
echo "   - app/schemas/rehabilitation.py 생성"
echo "   - app/services/rehabilitation_ai.py 생성"
echo "   - app/routers/rehabilitation.py 생성"
echo "   - frontend 파일들 복사"
echo ""
echo "2. app/main.py에 라우터를 등록하세요:"
echo "   from app.routers import rehabilitation"
echo "   app.include_router(rehabilitation.router)"
echo ""
echo "3. 백엔드 서버를 실행하세요:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "4. 프론트엔드 서버를 실행하세요:"
echo "   cd frontend && npm run dev"
echo ""
echo "5. 브라우저에서 접속하세요:"
echo "   http://localhost:5173/rehabilitation"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📖 자세한 내용은 INTEGRATION_GUIDE.md를 참고하세요${NC}"
