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

## 2) 파인튜닝/로컬 모델 기능

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

### D)  LoRA 학습을 돌리고 adapter 저장 확인


- 합성 데이터셋(SFT JSONL) 준비 → LoRA 학습 실행 → **adapter 저장 성공**
- 로컬 추론(LoRA adapter 로드 + `generate`) 실행 → 출력이 **엄격 JSON**을 만족하지 않아 파싱 실패 케이스 확인
- 원인 분석 후 아래 개선/완화 적용:
  - `app/services/__init__.py`의 **import side-effect 제거(lazy import)**: 로컬 추론이 Claude/pose(cv2) 의존성 없이 실행되도록 수정
  - 프롬프트 템플릿 `{`/`}` 이스케이프 처리(`{{`, `}}`)
  - GPT-2 계열(특히 distilgpt2) **컨텍스트 1024 토큰 제한** 대응: 입력 truncation + 남은 길이만 생성하도록 제한
  - “닫는 괄호가 늦게/안 나오는” 케이스를 위해 JSON 추출 로직 개선(문자열 내부 중괄호 무시한 brace balancing)
  - 반복 억제 옵션(repetition_penalty / no_repeat_ngram_size) 적용

> ⚠️ 결론: **학습 자체는 성공**(loss/eval_loss 개선 및 adapter 저장)했지만,  
> distilgpt2(소형/영어 중심) 기반에서 **한국어 + strict JSON 스키마 출력**은 안정적으로 수렴하지 않아  
> 로컬 추론 단계에서 **유효 JSON 파싱 실패율이 높게 관찰**되었습니다.

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

> 권장: 가상환경(venv/conda) 사용  
> - Windows PowerShell: `python -m venv .venv` → `.\.venv\Scripts\Activate.ps1`

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
  - ✅ (추가) Compact 데이터 변환: `scripts/make_compact_dataset.py`
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

## 8) 실제 실행 재현(Windows PowerShell 기준)

> 아래 커맨드는 **로컬 CPU 환경에서도** 실행 가능한 형태로 구성되어 있습니다.  
> (GPU가 있으면 더 빠릅니다.)

### 8.1 합성 데이터셋(이미 레포에 넣어둔 경우 생략 가능)
- 예시 경로:
  - `02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/train.jsonl`
  - `02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/valid.jsonl`

### 8.2 Compact 데이터셋 생성(권장)
JSON이 길어지면 학습이 “닫는 괄호”를 충분히 못 보고 배울 수 있어, **응답을 짧게 압축한 compact dataset**으로 먼저 안정성을 높입니다.

```powershell
python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/make_compact_dataset.py --inp 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/train.jsonl --outp 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/train_compact.jsonl
python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/make_compact_dataset.py --inp 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/valid.jsonl --outp 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/valid_compact.jsonl --max_items 500
```

### 8.3 LoRA 학습(distilgpt2, CPU-friendly)
```powershell
python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/train_rehab_json_lora.py --model_name distilgpt2 --train_jsonl 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/train_compact.jsonl --valid_jsonl 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/valid_compact.jsonl --output_dir artifacts/rehab_json_lora_compact --epochs 1 --batch_size 1 --grad_accum 16 --max_length 384
```

완료 시 예:
- `artifacts/rehab_json_lora_compact/adapter/` 생성

### 8.4 로컬 추론(1-shot)
```powershell
$env:REHAB_LOCAL_LORA_DIR="artifacts\rehab_json_lora_compact\adapter"; python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/quick_infer_rehab_json.py --pain_area 손목 --pain_description "마우스 오래 쓰면 손목이 찌릿해요" --severity 6
```

> ⚠️ 현재 distilgpt2 기반에서는 JSON strict 출력이 불안정할 수 있습니다(파싱 실패/문법 붕괴/반복).

### 8.5 오프라인 평가 리포트(PR-F1)
```powershell
python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/eval_rehab_json_generator.py --jsonl 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/synth/valid_compact.jsonl --mode local --out_json artifacts/rehab_json_lora_eval/report.json --failures_jsonl artifacts/rehab_json_lora_eval/failures.jsonl --max_samples 200
```

---

## 9) 산출물(Artifacts) 설명

### 9.1 LoRA adapter 폴더(중요)
예: `artifacts/rehab_json_lora_compact/adapter/`

- `adapter_config.json`
  - LoRA 설정(랭크, 타깃 모듈, base model 경로 등 메타데이터)
- `adapter_model.safetensors` (또는 `.bin`)
  - 실제 학습된 LoRA 가중치(“델타”)
- 참고: adapter만으로는 추론 불가하며, **base model + adapter** 조합으로 로드합니다.

### 9.2 체크포인트/Trainer 산출물(있을 수 있음)
- `checkpoint-*` 폴더: 중간 저장(재개 학습용)
- `trainer_state.json`, `training_args.bin`: 학습 기록/설정 저장

---

## 10) 트러블슈팅(자주 만나는 오류)

### A) `ModuleNotFoundError: torch / peft`
```bash
pip install -r requirements.txt -r requirements-ml.txt
```

### B) `TrainingArguments ... evaluation_strategy` 에러
- Transformers 버전에 따라 `evaluation_strategy` → `eval_strategy`로 바뀐 경우가 있습니다.
- 스크립트가 최신 버전과 맞지 않으면, 파라미터 이름을 맞추거나 transformers 버전을 고정하세요.

### C) 로컬 추론에서 `anthropic` / `cv2` import 에러
- 원인: `app/services/__init__.py`에서 서비스들을 “자동 import”하면, 로컬 추론에도 불필요한 의존성이 강제됩니다.
- 해결: `__init__.py`는 가볍게 유지하고, 필요한 곳에서 직접 import 하거나 lazy import로 전환하세요.

### D) `IndexError: index out of range` (1024 토큰 초과)
- GPT-2 계열은 컨텍스트 길이 제한이 있어 프롬프트+생성 길이가 1024를 넘으면 터질 수 있습니다.
- 해결: 입력 truncation + `max_new_tokens` 자동 제한(코드에 반영)

---

## 11) 현재 상태 & 다음 개선 방향

현재 상태:
- ✅ LoRA 학습 파이프라인(데이터 → 학습 → adapter 저장) 검증 완료
- ✅ 로컬 추론 실행/디버깅 완료(실제 `generate` 출력 확인)
- ⚠️ distilgpt2 기반에서 **한국어 + strict JSON** 출력 안정성이 낮아 파싱 실패 케이스 존재

다음 단계(권장):
1) **한국어 베이스 모델로 교체**(예: KoGPT2 계열) 후 동일 파이프라인 재학습
2) 디코딩 제약 강화(beam search, no-repeat 강화) + 실패 시 재시도(1~2회)
3) 오프라인 평가 리포트(PR-F1)를 기준으로 개선 전/후 비교

---

## 12) 안전/주의사항

- 본 프로젝트의 추천은 **의료 조언이 아닙니다.** 
- DB에서 학습 데이터를 Export할 경우, 개인정보/민감정보가 섞이지 않도록 주의하세요.
- `artifacts/`, `datasets/generated/` 는 커밋하지 않도록 `.gitignore`로 관리하는 것을 권장합니다.
