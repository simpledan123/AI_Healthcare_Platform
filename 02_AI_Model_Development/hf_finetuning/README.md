# HF Fine-tuning (Pain Area Classifier)

## 1) 설치
```bash
pip install -r requirements.txt -r requirements-ml.txt

## 평가(PR-F1)
학습 데이터(또는 로컬 생성 결과)를 기준으로 JSON 품질을 정량화합니다.

### A) dataset 모드 (모델 없이도 가능)
jsonl 안에 들어있는 response(JSON 문자열)를 파싱/규칙검증/Pydantic 스키마 검증합니다.

```bash
python 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/eval_rehab_json_generator.py \
  --jsonl 02_AI_Model_Development/hf_finetuning/rehab_json_lora/datasets/sample_rehab_sft.jsonl \
  --mode dataset