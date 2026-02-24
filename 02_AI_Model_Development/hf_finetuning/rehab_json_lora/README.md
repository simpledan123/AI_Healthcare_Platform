# Rehab JSON LoRA SFT Dataset (Export + Validate)

이 폴더는 "통증 정보 → 재활 운동 추천 JSON" 생성 모델을 LoRA로 파인튜닝하기 위한
SFT(Instruction Fine-tuning) 데이터 준비 단계입니다.

> Claude 기반 /recommend 기능은 그대로 두고,
> 로컬 LoRA 모델은 별도 엔드포인트(/recommend-local)에서만 사용하도록 설계합니다.

---

## 데이터 포맷 (JSONL)
한 줄에 1개 샘플:

- prompt: 모델 입력 프롬프트(지시문 + 입력)
- response: "유효한 JSON 문자열" (exercises/general_advice/estimated_duration_minutes)

예시:
```json
{"record_id": 1, "pain_area":"손목", "severity":6, "pain_description":"...", "prompt":"...", "response":"{...json...}"}

## PR-G1: 오프라인 평가 리포트(Demo 모드)

> Demo 모드는 모델/torch 없이도 “추천 생성 → 평가 리포트”가 동작하도록 만든 포트폴리오용 실행 모드입니다.

### 1) Demo 입력으로 평가 실행(모델 없이 가능)
```bash
python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/offline_eval_report.py \
  --inputs_jsonl 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/demo/demo_inputs.jsonl \
  --mode demo \
  --out_dir artifacts/offline_eval_demo \
  --write_predictions