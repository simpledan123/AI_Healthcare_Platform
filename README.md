# 🏥 Physical AI Healthcare Platform
> **AI 기반 맞춤형 재활 가이드 & 실시간 인프라 최적화 시스템**

본 프로젝트는 **Claude 3.5 Sonnet** 기반의 지능형 운동 처방과 **Prophet** 기반의 선제적 인프라 관리를 결합한 통합 헬스케어 플랫폼입니다.

---

## 🛠️ 핵심 아키텍처 및 로직 (Implementation Detail)

### 1. 🤖 하이브리드 운동 추천 엔진 (Rehabilitation AI)
단순한 AI 답변을 넘어 서비스 안정성을 보장하는 **3단계 추천 로직**이 구현되어 있습니다.

* **지능형 프롬프트 엔진**: 사용자의 통증 부위, 설명, 강도($0\sim10$)를 분석하여 최적화된 운동 세트, 횟수, 주의사항을 생성합니다.
* **응답 정규화 (JSON Strict Mode)**: 백엔드와 DB 처리를 위해 AI 응답을 엄격한 JSON 구조로 강제하며, 마크다운 형식을 배제합니다.
* **2중 방어 로직 (Fallback Strategy)**: API 키가 없거나 호출 실패 시, 시스템에 내장된 **기본 재활 가이드**를 즉시 반환하여 서비스 연속성을 보장합니다.
* **자동 YouTube 브릿지**: AI가 추출한 키워드를 기반으로 백엔드에서 실시간 YouTube 검색 URL을 생성하여 시각적 가이드를 제공합니다.

### 2. 📹 정밀 포즈 분석 및 시각화 (Pose Analytics)
MediaPipe를 기반으로 동작을 수치화하고, 전문가 데이터와 비교하는 정밀 알고리즘을 사용합니다.

* **고급 전처리 파이프라인**: `PoseDataProcessor`를 통해 이상치 제거(Cleaning) 및 스무딩(Smoothing) 처리를 거쳐 데이터 신뢰도를 높입니다.
* **DTW (Dynamic Time Warping)**: 사용자 동작과 참조 영상 간의 속도 차이를 시간축 정렬 알고리즘으로 보정하여 유사도를 측정합니다.
* **실시간 피드백 시스템**: 웹캠 프레임을 캡처하여 즉각적으로 자세 정확도(Score)와 개선 방향(Feedback)을 시각적으로 제공합니다.

### 3. 📈 지능형 인프라 제어 (Physical AI)
Prophet 시계열 모델을 활용하여 인프라 가용성을 자동 관리합니다.

* **자동 재학습 (Retraining)**: 6시간 주기로 모델을 자동 업데이트하여 예측 정확도를 유지합니다.
* **트래픽 급증 탐지 (Spike Detection)**: 갑작스러운 트래픽 변화를 실시간 감지하고 심각도(Severity)를 분류하여 경고를 생성합니다.
* **서버 권장 사항**: 예측된 피크 타임을 기준으로 최적의 서버 대수를 산출하여 리소스 낭비를 최소화합니다.

---

## 📊 주요 API 엔드포인트

| 카테고리 | 경로 | 주요 기능 |
| :--- | :--- | :--- |
| **Healthcare** | `POST /api/rehabilitation/recommend` | AI/Fallback 기반 운동 추천 생성 및 DB 저장 |
| **Analytics** | `GET /api/rehabilitation/statistics/{id}` | 사용자의 운동 완료율 및 통증 강도 추이 분석 |
| **Pose** | `POST /api/pose-comparison/compare` | DTW 기반 전체 운동 영상 유사도 분석 |
| **Real-time** | `POST /api/pose-comparison/realtime-frame-check` | 웹캠 프레임 단위 실시간 자세 교정 피드백 |
| **Infra** | `GET /infra/status` | 실시간 트래픽 상태 및 24시간 예측 데이터 조회 |
| **Dashboard** | `GET /dashboard/summary` | 통증 부위 분포 및 기간별 성취도 종합 시각화 |

---

## 🏗️ 시스템 구조 (Project Structure)

```text
app/
├── api/routers/      # API 엔드포인트 (Rehab, Pose, Infra, Analytics 등)
├── services/         # 핵심 비즈니스 로직 (AI 추천, 전처리, 트래픽 예측)
├── models/           # SQLAlchemy 기반 정규화된 DB 모델
├── schemas/          # Pydantic 기반 데이터 검증 및 직렬화
└── database.py       # DB 연결 및 세션 관리