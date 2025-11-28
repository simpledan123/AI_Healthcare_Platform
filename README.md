# 🏥 Physical AI Healthcare Platform

> AI 기반 맞춤 운동 추천 및 실시간 자세 분석 시스템

---

## 📖 프로젝트 개요

Physical AI Healthcare Platform은 **Physical AI**와 **Healthcare AI**를 통합한 헬스케어 플랫폼입니다.

### 해결하는 문제

**1. 인프라 불안정**
- 헬스케어 서비스는 이벤트 시 트래픽이 급증하며 서비스 가용성이 저하됩니다.

**2. 사용자 경험 부족**
- 기존 앱은 단순한 운동 목록만 제공하거나, 관절 각도 측정만으로 구체적 피드백을 주지 못합니다.

### 우리의 솔루션

```
Physical AI          +          Healthcare AI
트래픽 예측/서버 제어           AI 운동 추천/자세 분석
→ 인프라 안정성               → 사용자 경험 개선
```

---

## 🌟 주요 기능

### 1. 🤖 AI 맞춤 운동 추천

**Claude Sonnet 4 기반 개인화 추천**

```
사용자 입력: 손목 통증, 강도 7/10
    ↓
Claude AI 분석
    ↓
결과: 3가지 맞춤 운동 + YouTube 링크
```

- 통증 부위 및 강도 분석
- 의학적 컨텍스트 주입
- 운동 방법, 세트, 주의사항 제공
- YouTube 영상 자동 연동

---

### 2. 📹 실시간 자세 분석

**MediaPipe + DTW + 코사인 유사도 기반 정밀 분석**

#### 핵심 기술

| 기술 | 역할 | 효과 |
|------|------|------|
| **MediaPipe** | 33개 신체 랜드마크 추출 | 실시간 포즈 인식 |
| **DTW** (Dynamic Time Warping) | 시간축 정렬 | 속도 차이 보정 |
| **코사인 유사도** | 포즈 벡터 비교 | 0-100점 정량화 |
| **정규화** | 어깨 기준 스케일 조정 | 체형 차이 보정 |

#### 분석 결과 예시

```
✅ 전체 유사도: 82/100점
🎯 최저 구간: 40% 지점 (65점)
⏱️ 속도 비율: 1.2x (조금 느림)
📊 DTW 거리: 0.18

피드백:
• 전반적으로 잘하고 있습니다
• 40% 지점에서 자세 개선이 필요합니다
• 속도를 약간 높여보세요
```

---

### 3. 🏗️ Physical AI 인프라 제어

**Prophet 기반 트래픽 예측 및 자동 제어**

- 실시간 부하 모니터링 (3초 갱신)
- 트래픽 패턴 학습 및 예측
- 서버 자동 증설/감축
- 에너지 효율 최적화

```
트래픽 예측 → 서버 제어 → 에너지 절감
   ↓            ↓            ↓
Prophet     Auto Scaling   PUE 개선
```

---

### 4. 💬 커뮤니티

- AI 추천 vs 사용자 방법 비교
- 효과 평점 및 후기 공유
- 부위별/타입별 필터링
- YouTube 링크 공유

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────┐
│         React + Vite (Frontend)         │
└─────────────────────────────────────────┘
                  ↓ REST API
┌─────────────────────────────────────────┐
│          FastAPI (Backend)              │
│   ┌──────────┬──────────┬──────────┐   │
│   │ Routers  │ Services │  Models  │   │
│   └──────────┴──────────┴──────────┘   │
└─────────────────────────────────────────┘
        ↓           ↓           ↓
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Claude   │ │MediaPipe │ │PostgreSQL│
│ Sonnet 4 │ │          │ │  + JSONB │
└──────────┘ └──────────┘ └──────────┘
```

### 디렉토리 구조

```
app/
├── api/
│   └── routers/              # API 엔드포인트
│       ├── rehabilitation.py  # AI 운동 추천
│       ├── pose_comparison.py # 자세 비교
│       ├── community.py       # 커뮤니티
│       └── infra.py           # 인프라 모니터링
├── services/                 # 비즈니스 로직
│   ├── rehabilitation_ai.py   # Claude API 통신
│   └── pose_similarity.py     # 자세 분석 알고리즘
├── models/                   # DB 모델 (SQLAlchemy)
├── schemas/                  # API 스키마 (Pydantic)
└── main.py                   # FastAPI 앱

frontend/
└── src/
    └── components/
        ├── ExerciseComparison.jsx  # 자세 비교 UI
        ├── CommunityFeed.jsx       # 커뮤니티 UI
        └── Rehabilitation.jsx      # AI 추천 UI
```

---

## 🛠️ 기술 스택

### Backend

| 카테고리 | 기술 | 역할 | 버전 |
|---------|------|------|------|
| **Web Framework** | FastAPI | 고성능 비동기 API 서버 | 0.104+ |
| **ORM** | SQLAlchemy | 데이터베이스 ORM | 2.0+ |
| **Database** | PostgreSQL | 관계형 DB (JSONB 지원) | 14+ |
| **Migration** | Alembic | DB 스키마 버전 관리 | 1.12+ |
| **Validation** | Pydantic | 데이터 검증 및 직렬화 | 2.5+ |

### AI & ML

| 카테고리 | 기술 | 역할 | 제공 |
|---------|------|------|------|
| **LLM** | Claude Sonnet 4 | 운동 추천 생성 | Anthropic |
| **Computer Vision** | MediaPipe | 실시간 포즈 추정 (33 landmarks) | Google |
| **Time Series** | Prophet | 트래픽 예측 | Meta |
| **ML Library** | scikit-learn | 코사인 유사도 계산 | - |
| **CV Library** | OpenCV | 이미지/영상 처리 | - |

### Frontend

| 카테고리 | 기술 | 역할 | 버전 |
|---------|------|------|------|
| **Framework** | React | UI 라이브러리 | 18+ |
| **Build Tool** | Vite | 빌드 도구 | 5+ |
| **HTTP Client** | Axios | API 통신 | 1.6+ |
| **Styling** | Tailwind CSS | CSS 프레임워크 | 3+ |

### 알고리즘

| 알고리즘 | 목적 | 구현 |
|---------|------|------|
| **DTW** (Dynamic Time Warping) | 시간축 정렬 (속도 보정) | Python (NumPy) |
| **코사인 유사도** | 포즈 벡터 유사도 측정 | scikit-learn |
| **정규화** (Normalization) | 체형 차이 보정 | 어깨 중심 기준 스케일 |

### DevOps & Tools

| 카테고리 | 기술 | 역할 |
|---------|------|------|
| **Environment** | Conda | Python 가상환경 |
| **API Documentation** | Swagger/OpenAPI | 자동 API 문서 생성 |
| **CORS** | FastAPI Middleware | 크로스 오리진 처리 |

---

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Conda (권장)

### 1. 레포지토리 클론

```bash
git clone https://github.com/simpledan123/Web-load-Prediction.git
cd Web-load-Prediction
```

### 2. 백엔드 설정

#### 가상환경 생성 및 패키지 설치

```bash
conda create -n healthcare python=3.10
conda activate healthcare
pip install -r requirements.txt
```

#### 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
ANTHROPIC_API_KEY=your_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=health_db
DB_USER=user_health
DB_PASS=your_password
EOF
```

#### 데이터베이스 설정

```bash
# PostgreSQL에 DB 및 유저 생성
psql -U postgres
CREATE DATABASE health_db;
CREATE USER user_health WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE health_db TO user_health;
\q

# Alembic 마이그레이션 실행
alembic upgrade head
```

#### 서버 실행

```bash
uvicorn app.main:app --reload
```

**Swagger 문서:** http://localhost:8000/docs

### 3. 프론트엔드 설정

```bash
cd frontend
npm install
npm run dev
```

**웹 접속:** http://localhost:5173

---

## 📊 API 엔드포인트

### Healthcare AI

#### 1. AI 운동 추천

```http
POST /api/rehabilitation/recommend
Content-Type: application/json

{
  "user_id": 1,
  "pain_area": "손목",
  "severity": 7,
  "pain_description": "마우스 사용 후 시큰거림"
}
```

**응답:**
```json
{
  "pain_area": "손목",
  "severity": 7,
  "exercises": [
    {
      "name": "손목 신전 스트레칭",
      "description": "1. 팔을 앞으로...",
      "sets": 3,
      "reps": 10,
      "duration_seconds": 15,
      "cautions": ["무리하지 마세요"],
      "difficulty": "초급",
      "youtube_keywords": ["손목 스트레칭", "wrist stretch"],
      "youtube_search_url": "https://youtube.com/..."
    }
  ],
  "general_advice": "하루 2-3회 반복하세요",
  "estimated_duration_minutes": 10,
  "medical_disclaimer": "이것은 의료 조언이 아닙니다..."
}
```

#### 2. 웹캠 자세 비교

```http
POST /api/pose-comparison/compare
Content-Type: multipart/form-data

user_video: <file>
exercise_id: "wrist_stretch_1"
sample_rate: 5
```

**응답:**
```json
{
  "success": true,
  "overall_similarity": 82,
  "dtw_distance": 0.18,
  "frame_similarities": [0.90, 0.85, 0.65, ...],
  "worst_frame_index": 15,
  "feedback": [
    "전반적으로 잘하고 있습니다",
    "40% 지점에서 자세 개선 필요"
  ],
  "speed_ratio": 1.2
}
```

#### 3. 실시간 프레임 체크

```http
POST /api/pose-comparison/realtime-frame-check
Content-Type: multipart/form-data

frame: <image>
exercise_id: "wrist_stretch_1"
frame_index: 0
```

**응답:**
```json
{
  "success": true,
  "similarity_score": 82,
  "feedback": "✅ 완벽합니다!",
  "color": "green"
}
```

### Physical AI

#### 인프라 상태 조회

```http
GET /infra/status
```

**응답:**
```json
{
  "active_users": 1250,
  "total_posts": 8430,
  "system_status": "High Load",
  "ai_prediction": {
    "needed_servers": 8,
    "rack_temperature_avg": 27.3,
    "power_usage_watt": 2400
  }
}
```

---

## 📍 개발 현황

### ✅ 완료

- [x] FastAPI 백엔드 아키텍처
- [x] React 프론트엔드 UI/UX
- [x] Claude AI 운동 추천 시스템
- [x] MediaPipe 포즈 추출
- [x] DTW + 코사인 유사도 알고리즘
- [x] 실시간 프레임 분석
- [x] 커뮤니티 기능
- [x] Physical AI 모니터링 대시보드

### 🚧 진행 중

- [ ] **참조 영상 데이터베이스**
  - 현재: 알고리즘 검증 단계 (플레이스홀더)
  - 계획: 실제 시연 영상 추가

### 투명성 공개

참조 영상은 현재 **플레이스홀더** 상태이며, API 응답과 UI에서 이를 명시합니다.

```json
{
  "status": "placeholder_phase",
  "message": "현재는 시스템 검증 단계입니다",
  "note": "추후 실제 영상으로 업데이트 예정"
}
```

---

### 테스트

```bash
# 백엔드
pytest tests/

# 프론트엔드
cd frontend
npm test
```

---