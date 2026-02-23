# Physical AI Healthcare Platform

> **AI 기반 맞춤형 재활 가이드 & 실시간 인프라 최적화 시스템**  
> 기본 추천은 **Claude(Anthropic)** 기반으로 동작하며, **Hugging Face/LoRA 파인튜닝 기능은 옵션(Add-on)** 으로 붙습니다.

---

## 1) 프로젝트 소개

본 프로젝트는 아래 3개의 축으로 구성된 통합 헬스케어 플랫폼입니다.

1. **재활 운동 추천(Rehabilitation AI)**
   - Claude 기반의 운동 추천 생성
   - 백엔드/DB 처리를 위해 **JSON Strict Mode**로 응답 형식을 강제
   - API 실패 시 **Fallback(내장 추천)** 으로 서비스 연속성 보장
   - 추천 키워드 기반 **YouTube 검색 URL 자동 생성**

2. **자세 분석(Pose Analytics)**
   - MediaPipe 기반 포즈 추출/수치화
   - DTW(Dynamic Time Warping) 기반 유사도 비교
   - 프레임 단위 실시간 피드백(웹캠) 제공

3. **지능형 인프라 제어(Physical AI / Infra)**
   - Prophet 기반 트래픽 예측(24시간)
   - 급증 탐지(Spike Detection) 및 서버 권장 대수 산출
   - 주기적 재학습(6시간) 컨셉 적용

---

## 2) 옵션(Add-on): 파인튜닝/로컬 모델 기능

> ✅ **기본 기능(Claude 추천)은 그대로 유지**됩니다.  
> 아래 기능들은 **기업에서 요구하는 “모델 파인튜닝 경험”을 프로젝트에 덧붙이기 위한 확장**입니다.

### A) 통증 부위 분류 모델(HF Fine-tuning)
- 사용자의 `pain_description` → `pain_area` 자동 분류
- FastAPI 엔드포인트 제공: `POST /api/rehabilitation/pain-area/predict`
- `/recommend` 요청에서 `pain_area="AUTO"` 사용 시 자동 분류 결과로 보정 가능

### B) 로컬 LoRA JSON 생성 모델(옵션)
- “통증 정보 → 운동 추천 JSON”을 생성하는 로컬 모델(LoRA SFT)
- Claude를 대체하는 것이 아니라,
  - **별도 엔드포인트(`/recommend-local`)** 로 제공하거나
  - **환경변수로만 엔진 선택(REHAB_REC_ENGINE)** 하도록 설계
- 결과는 서버에서 JSON 파싱/정규화 후 DB 저장(안정성 강화)

### C) 데이터/학습/평가 파이프라인
- DB → SFT(JSONL) Export
- 품질 필터링(PR-F2): 짧은 텍스트 제거, exercise 최소 개수, 필드/범위 검증 등
- 평가(PR-F1): JSON 파싱 성공률 / 규칙 통과율 / Pydantic 스키마 통과율 리포트 출력

---

## 3) 설치 & 실행(백엔드)

### 3.1 필수(기본 서버 기능)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API 문서: `http://localhost:8000/docs`

### 3.2 선택(파인튜닝/로컬 모델 기능)
```bash
pip install -r requirements.txt -r requirements-ml.txt
```

---

## 4) 주요 환경변수

### (기본) Claude 추천
- `ANTHROPIC_API_KEY` : Claude API 키

### (옵션) 통증 부위 분류 모델
- `PAIN_AREA_MODEL_DIR` : HF 분류 모델 경로 (예: `artifacts/pain_area_classifier/best`)

### (옵션) 로컬 LoRA 추천 모델
- `REHAB_LOCAL_LORA_DIR` : LoRA adapter 경로 (예: `artifacts/rehab_json_lora/adapter`)
- `REHAB_LOCAL_BASE_MODEL` : (선택) base model override
- `REHAB_TRUST_REMOTE_CODE` : (선택) `true/false`

### (옵션) 추천 엔진 선택(기본은 Claude 유지)
- `REHAB_REC_ENGINE` (default: `claude`)
  - `claude`
  - `local`
  - `claude_then_local`
  - `local_then_claude`

---

## 5) 주요 API 엔드포인트

> ⚠️ 라우팅 prefix는 라우터 include 방식에 따라 달라질 수 있습니다.  
> 정확한 경로는 **`/docs`에서 최종 확인**하세요.

| 카테고리 | 경로 | 주요 기능 |
| --- | --- | --- |
| Healthcare | `POST /api/rehabilitation/recommend` | 기본 추천(Claude/Fallback) 생성 + DB 저장 (`pain_area="AUTO"` 지원 가능) |
| Healthcare (Add-on) | `POST /api/rehabilitation/recommend-local` | 로컬 LoRA 추천 생성 + DB 저장(옵션) |
| Healthcare (Add-on) | `POST /api/rehabilitation/pain-area/predict` | 통증 설명 → 통증 부위 예측(HF/휴리스틱) |
| Analytics | `GET /api/rehabilitation/statistics/{id}` | 추천/완료율/통증강도/운동 TOP3 등 통계 |
| Pose | `POST /api/pose-comparison/compare` | 사용자 영상 vs 참조 영상 DTW 유사도 분석 |
| Real-time | `POST /api/pose-comparison/realtime-frame-check` | 웹캠 프레임 단위 실시간 자세 피드백 |
| Infra | `GET /infra/status` | 실시간 트래픽 상태 + 24시간 예측 + 서버 권장 |
| Dashboard | `GET /dashboard/summary` | 분석 요약(차트/지표용) |

---

## 6) 파인튜닝/로컬 모델 폴더 안내

### 6.1 통증 부위 분류(HF Fine-tuning)
- 위치: `02_AI_Model_Development/hf_finetuning/`
- 구성(예시):
  - 데이터: `datasets/sample/`, `datasets/generated/`
  - 학습: `scripts/train_pain_area_classifier.py`
  - 추론: `app/services/hf_models/pain_area_classifier.py`

### 6.2 로컬 LoRA JSON 생성(옵션)
- 위치: `02_AI_Model_Development/hf_finetuning/rehab_json_lora/`
- 구성(예시):
  - DB Export: `scripts/export_rehab_sft_from_db.py`
  - 데이터 검증: `scripts/validate_rehab_sft_dataset.py`
  - LoRA 학습: `scripts/train_rehab_json_lora.py`
  - 평가(PR-F1): `scripts/eval_rehab_json_generator.py`
  - 로컬 추론: `app/services/hf_models/rehab_json_generator.py`

---

## 7) 시스템 구조(Project Structure)

```text
app/
├── api/routers/      # API 엔드포인트 (Rehab, Pose, Infra, Analytics 등)
├── services/         # 핵심 비즈니스 로직 (AI 추천, 전처리, 트래픽 예측)
├── models/           # SQLAlchemy 기반 정규화된 DB 모델
├── schemas/          # Pydantic 기반 데이터 검증 및 직렬화
└── database.py       # DB 연결 및 세션 관리

02_AI_Model_Development/
└── hf_finetuning/    # (옵션) Hugging Face / LoRA 학습·평가 파이프라인
```

---

## 8) 안전/주의사항

- 본 프로젝트의 추천은 **의료 조언이 아닙니다.** 
- DB에서 학습 데이터를 Export할 경우, 개인정보/민감정보가 섞이지 않도록 주의하세요.
- `artifacts/`, `datasets/generated/` 는 커밋하지 않도록 `.gitignore`로 관리하는 것을 권장합니다.
