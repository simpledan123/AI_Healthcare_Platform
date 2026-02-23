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