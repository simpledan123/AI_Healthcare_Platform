# 🏥 AI 재활 운동 추천 시스템 아키텍처

## 📊 전체 시스템 구조

```mermaid
graph TB
    User[👤 사용자] --> Frontend[🌐 React Frontend]
    
    Frontend --> |HTTP Request| API[⚡ FastAPI Backend]
    
    API --> |ORM Query| DB[(🗄️ PostgreSQL)]
    API --> |AI Request| Claude[🤖 Claude API]
    
    subgraph "Frontend Components"
        Frontend --> Rehab[재활 페이지]
        Rehab --> BodySelect[통증 부위 선택]
        Rehab --> ExCard[운동 카드]
        Rehab --> History[기록 조회]
    end
    
    subgraph "Backend Services"
        API --> Router[rehabilitation.py]
        Router --> Service[rehabilitation_ai.py]
        Router --> Model[RehabilitationRecord]
        Service --> Claude
    end
    
    subgraph "Database"
        DB --> Users[users]
        DB --> RehabRecords[rehabilitation_records]
        Users --> |1:N| RehabRecords
    end
    
    style User fill:#667eea,color:#fff
    style Frontend fill:#4ECDC4,color:#fff
    style API fill:#FF6B6B,color:#fff
    style DB fill:#FFA07A,color:#fff
    style Claude fill:#98D8C8,color:#000
```

## 🔄 데이터 흐름

```mermaid
sequenceDiagram
    participant U as 👤 사용자
    participant F as 🌐 Frontend
    participant A as ⚡ API
    participant C as 🤖 Claude
    participant D as 🗄️ DB
    
    U->>F: 1. 통증 부위 선택 (손목, 6/10)
    F->>A: 2. POST /api/rehabilitation/recommend
    A->>D: 3. 사용자 확인
    D-->>A: 4. User 정보
    A->>C: 5. AI 추천 요청 (프롬프트)
    C-->>A: 6. 맞춤형 운동 추천 (JSON)
    A->>D: 7. 추천 기록 저장
    D-->>A: 8. record_id
    A-->>F: 9. 추천 결과 반환
    F-->>U: 10. 운동 카드 표시
    U->>F: 11. 운동 완료 표시
    F->>A: 12. PATCH /api/rehabilitation/complete
    A->>D: 13. 완료 상태 업데이트
```

## 🎨 UI 컴포넌트 구조

```mermaid
graph LR
    Rehab[Rehabilitation.jsx] --> Header[페이지 헤더]
    Rehab --> Tabs[탭 네비게이션]
    
    Tabs --> Recommend[추천받기 탭]
    Tabs --> History[기록 탭]
    
    Recommend --> Body[BodyPartSelector]
    Recommend --> Slider[통증 강도 슬라이더]
    Recommend --> Desc[설명 입력]
    Recommend --> Btn[AI 추천 버튼]
    Recommend --> Result[추천 결과]
    
    Result --> Advice[전체 조언]
    Result --> Cards[ExerciseCard 목록]
    
    Cards --> Card1[운동 카드 1]
    Cards --> Card2[운동 카드 2]
    Cards --> Card3[운동 카드 3]
    
    Card1 --> Info[운동 정보]
    Card1 --> Caution[주의사항]
    Card1 --> Actions[액션 버튼]
    
    History --> List[기록 목록]
    List --> Item1[기록 1]
    List --> Item2[기록 2]
    
    style Rehab fill:#667eea,color:#fff
    style Body fill:#4ECDC4,color:#fff
    style Cards fill:#FF6B6B,color:#fff
```

## 🗄️ 데이터베이스 스키마

```mermaid
erDiagram
    USERS ||--o{ REHABILITATION_RECORDS : has
    USERS {
        int id PK
        string username
        string email
        datetime created_at
    }
    REHABILITATION_RECORDS {
        int id PK
        int user_id FK
        string pain_area
        text pain_description
        int severity
        jsonb recommended_exercises
        boolean completed
        text completion_notes
        datetime created_at
        datetime updated_at
    }
```

## 📡 API 엔드포인트 맵

```mermaid
graph LR
    API[/api/rehabilitation] --> Recommend[POST /recommend]
    API --> History[GET /history/:id]
    API --> Complete[PATCH /complete/:id]
    API --> Stats[GET /statistics/:id]
    API --> Delete[DELETE /record/:id]
    
    Recommend --> |Request| ReqBody1[통증 정보]
    Recommend --> |Response| ResBody1[AI 추천]
    
    History --> |Response| ResBody2[기록 목록]
    
    Complete --> |Request| ReqBody2[완료 정보]
    Complete --> |Response| ResBody3[업데이트 결과]
    
    Stats --> |Response| ResBody4[통계 데이터]
    
    style API fill:#667eea,color:#fff
    style Recommend fill:#51cf66,color:#fff
    style History fill:#4ECDC4,color:#fff
    style Complete fill:#ffd43b,color:#000
    style Stats fill:#FF6B6B,color:#fff
```

## 🔐 보안 흐름

```mermaid
graph TD
    Request[HTTP 요청] --> CORS{CORS 검사}
    CORS -->|허용된 출처| Auth{인증 확인}
    CORS -->|차단된 출처| Reject1[403 Forbidden]
    
    Auth -->|유효한 토큰| RateLimit{Rate Limit}
    Auth -->|무효한 토큰| Reject2[401 Unauthorized]
    
    RateLimit -->|제한 내| Validate{입력 검증}
    RateLimit -->|제한 초과| Reject3[429 Too Many Requests]
    
    Validate -->|유효한 입력| Process[요청 처리]
    Validate -->|무효한 입력| Reject4[400 Bad Request]
    
    Process --> Response[응답 반환]
    
    style Request fill:#667eea,color:#fff
    style Process fill:#51cf66,color:#fff
    style Response fill:#4ECDC4,color:#fff
    style Reject1 fill:#ff6b6b,color:#fff
    style Reject2 fill:#ff6b6b,color:#fff
    style Reject3 fill:#ff6b6b,color:#fff
    style Reject4 fill:#ff6b6b,color:#fff
```

## 🚀 배포 파이프라인

```mermaid
graph LR
    Dev[개발 환경] --> Test[테스트]
    Test --> Build[빌드]
    Build --> Docker[Docker 이미지]
    Docker --> Registry[Container Registry]
    Registry --> Deploy[배포]
    
    Deploy --> Backend[Backend Server]
    Deploy --> Frontend[Frontend Server]
    Deploy --> DB[Database]
    
    Backend --> Health[Health Check]
    Frontend --> Health
    
    Health --> Monitor[모니터링]
    Monitor --> Alert[알림]
    
    style Dev fill:#667eea,color:#fff
    style Deploy fill:#51cf66,color:#fff
    style Monitor fill:#ffd43b,color:#000
    style Alert fill:#ff6b6b,color:#fff
```

---

## 📝 주요 기술 스택 요약

| 계층 | 기술 | 역할 |
|------|------|------|
| **Frontend** | React + Vite | UI 렌더링 |
| **API** | FastAPI | REST API 서버 |
| **AI** | Claude API | 운동 추천 생성 |
| **Database** | PostgreSQL | 데이터 저장 |
| **ORM** | SQLAlchemy | DB 추상화 |
| **Migration** | Alembic | 스키마 관리 |
| **Styling** | CSS3 | UI 디자인 |

---

## 🎯 핵심 기능 흐름

### 1️⃣ AI 추천 받기
```
사용자 입력 → Frontend 검증 → API 호출 → Claude AI 요청 
→ 추천 생성 → DB 저장 → 결과 반환 → UI 표시
```

### 2️⃣ 운동 완료하기
```
완료 버튼 클릭 → API 호출 → DB 업데이트 
→ 통계 갱신 → 성공 메시지
```

### 3️⃣ 기록 조회하기
```
기록 탭 클릭 → API 호출 → DB 쿼리 
→ 데이터 반환 → 목록 렌더링
```

---

**Made with 💙 using Mermaid.js**
