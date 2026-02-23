# app/services/hf_models/rehab_json_generator.py
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


PAIN_AREA_CONTEXT = {
    "손목": "컴퓨터 작업/스마트폰 사용 등으로 인한 과사용",
    "어깨": "잘못된 자세/긴장으로 인한 근육 뭉침",
    "허리": "장시간 앉은 자세/코어 약화",
    "무릎": "계단/스쿼트 등 반복 부하",
    "목": "거북목/장시간 화면 시청",
    "발목": "접질림/불안정성",
}

PROMPT_TEMPLATE = """당신은 재활 운동 코치입니다.

[입력]
- 통증 부위: {pain_area}
- 통증 설명: {pain_description}
- 통증 강도: {severity}/10
- 참고(원인/맥락): {context}

[요구사항]
1) 3~5개의 스트레칭/운동을 추천하세요.
2) 각 운동은 다음 필드를 포함하세요:
   - name (문자열)
   - description (단계별, 줄바꿈 \\n 사용)
   - sets (정수)
   - reps (정수)
   - duration_seconds (정수)
   - cautions (문자열 배열)
   - difficulty (쉬움/보통/어려움)
   - youtube_keywords (한글+영어 키워드 배열)
3) 통증 강도를 고려한 general_advice를 작성하세요.

[출력]
반드시 아래 JSON 스키마를 만족하는 '유효한 JSON만' 출력하세요. 마크다운 금지.
{{
  "exercises": [
    {{
      "name": "...",
      "description": "1. ...\\n2. ...",
      "sets": 3,
      "reps": 10,
      "duration_seconds": 15,
      "cautions": ["..."],
      "difficulty": "쉬움",
      "youtube_keywords": ["손목 스트레칭", "wrist stretch"]
    }}
  ],
  "general_advice": "...",
  "estimated_duration_minutes": 10
}}
"""


class LocalRehabModelUnavailable(RuntimeError):
    pass


class LocalRehabGenerationError(RuntimeError):
    pass


_SINGLETON: Optional[Tuple[Any, Any, Any, Any]] = None  # (torch, device, tokenizer, model)
_LOAD_ERROR: Optional[str] = None


def _build_prompt(pain_area: str, pain_description: str, severity: int) -> str:
    context = PAIN_AREA_CONTEXT.get(pain_area, "일반적인 근육 통증")
    return PROMPT_TEMPLATE.format(
        pain_area=pain_area,
        pain_description=pain_description or "특별한 설명 없음",
        severity=int(severity),
        context=context,
    )


def _try_load(adapter_dir: str):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel, PeftConfig

    if not os.path.isdir(adapter_dir):
        raise FileNotFoundError(
            f"REHAB_LOCAL_LORA_DIR='{adapter_dir}' 디렉토리가 없습니다. "
            f"(학습 후 artifacts/rehab_json_lora/adapter 를 지정하세요.)"
        )

    peft_cfg = PeftConfig.from_pretrained(adapter_dir)
    base_name = os.getenv("REHAB_LOCAL_BASE_MODEL", peft_cfg.base_model_name_or_path)

    trust_remote_code = os.getenv("REHAB_TRUST_REMOTE_CODE", "false").lower() == "true"

    tokenizer = AutoTokenizer.from_pretrained(base_name, use_fast=True, trust_remote_code=trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token

    model = AutoModelForCausalLM.from_pretrained(base_name, trust_remote_code=trust_remote_code)

    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.pad_token_id

    model = PeftModel.from_pretrained(model, adapter_dir)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    return torch, device, tokenizer, model


def get_local_rehab_generator():
    global _SINGLETON, _LOAD_ERROR
    if _SINGLETON is not None:
        return _SINGLETON, _LOAD_ERROR

    adapter_dir = os.getenv("REHAB_LOCAL_LORA_DIR", "artifacts/rehab_json_lora/adapter")
    try:
        _SINGLETON = _try_load(adapter_dir)
        _LOAD_ERROR = None
        return _SINGLETON, _LOAD_ERROR
    except Exception as e:
        _SINGLETON = None
        _LOAD_ERROR = str(e)
        return None, _LOAD_ERROR


def _extract_json(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    t = t.replace("```json", "").replace("```", "").strip()

    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LocalRehabGenerationError("모델 출력에서 JSON 객체를 찾지 못했습니다.")

    payload = t[start : end + 1]
    try:
        return json.loads(payload)
    except Exception as e:
        raise LocalRehabGenerationError(f"JSON 파싱 실패: {e}")


def _youtube_search_url(primary_keyword: str) -> str:
    q = (primary_keyword or "").strip().replace(" ", "+")
    return f"https://www.youtube.com/results?search_query={q}"


def _normalize_output(obj: Dict[str, Any], pain_area: str, severity: int) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise LocalRehabGenerationError("출력 JSON이 dict가 아닙니다.")

    exercises = obj.get("exercises")
    if not isinstance(exercises, list) or len(exercises) < 1:
        raise LocalRehabGenerationError("exercises가 비어있거나 올바르지 않습니다.")

    norm_ex: List[Dict[str, Any]] = []
    for ex in exercises[:5]:
        if not isinstance(ex, dict):
            continue

        name = str(ex.get("name") or "").strip()
        desc = str(ex.get("description") or "").strip()

        sets = ex.get("sets", 3)
        reps = ex.get("reps", 10)
        duration = ex.get("duration_seconds", 15)

        # int 강제 (서버/DB 저장 안정성)
        try:
            sets = int(sets)
        except Exception:
            sets = 3
        try:
            reps = int(reps)
        except Exception:
            reps = 10
        try:
            duration = int(duration)
        except Exception:
            duration = 15

        cautions = ex.get("cautions") or []
        if not isinstance(cautions, list):
            cautions = [str(cautions)]

        difficulty = str(ex.get("difficulty") or "쉬움").strip()
        if difficulty not in {"쉬움", "보통", "어려움"}:
            # 흔한 표현 보정
            mapping = {"초급": "쉬움", "중급": "보통", "고급": "어려움"}
            difficulty = mapping.get(difficulty, "쉬움")

        youtube_keywords = ex.get("youtube_keywords") or []
        if not isinstance(youtube_keywords, list):
            youtube_keywords = [str(youtube_keywords)]

        out_ex = {
            "name": name or "기본 스트레칭",
            "description": desc or "1. 편안한 자세로 시작하세요\n2. 천천히 진행하세요\n3. 통증이 심해지면 중단하세요",
            "sets": sets,
            "reps": reps,
            "duration_seconds": duration,
            "cautions": [str(x) for x in cautions],
            "difficulty": difficulty,
            "youtube_keywords": [str(x) for x in youtube_keywords],
        }

        # Claude 구현과 동일한 방식으로 youtube_search_url 생성(키워드 1개라도 있으면)
        if out_ex["youtube_keywords"]:
            out_ex["youtube_search_url"] = _youtube_search_url(out_ex["youtube_keywords"][0])
        else:
            out_ex["youtube_search_url"] = None

        norm_ex.append(out_ex)

    if not norm_ex:
        raise LocalRehabGenerationError("정상화 이후 exercises가 비었습니다.")

    general_advice = str(obj.get("general_advice") or "").strip()
    if not general_advice:
        general_advice = f"무리하지 않는 범위에서 하루 1~2회 반복하세요. 통증이 지속되면 전문가 상담이 필요합니다."

    est = obj.get("estimated_duration_minutes", 10)
    try:
        est = int(est)
    except Exception:
        est = 10

    # 서버가 pain_area/severity는 입력 기준으로 최종 고정
    return {
        "pain_area": pain_area,
        "severity": int(severity),
        "exercises": norm_ex,
        "general_advice": general_advice,
        "estimated_duration_minutes": est,
    }


def generate_local_rehab_recommendation(
    pain_area: str,
    pain_description: str,
    severity: int,
    max_new_tokens: int = 700,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> Dict[str, Any]:
    bundle, err = get_local_rehab_generator()
    if bundle is None:
        raise LocalRehabModelUnavailable(
            "로컬 LoRA 모델을 사용할 수 없습니다. "
            f"(원인: {err}) "
            "requirements-ml.txt 설치 + REHAB_LOCAL_LORA_DIR 설정을 확인하세요."
        )

    torch, device, tokenizer, model = bundle

    prompt = _build_prompt(pain_area, pain_description, severity)

    with torch.inference_mode():
        inputs = tokenizer(prompt, return_tensors="pt").to(device)

        do_sample = temperature is not None and float(temperature) > 0.0
        gen_ids = model.generate(
            **inputs,
            max_new_tokens=int(max_new_tokens),
            do_sample=do_sample,
            temperature=float(temperature),
            top_p=float(top_p),
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

        # 프롬프트 이후만 디코딩
        prompt_len = inputs["input_ids"].shape[1]
        new_tokens = gen_ids[0][prompt_len:]
        gen_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    obj = _extract_json(gen_text)
    return _normalize_output(obj, pain_area=pain_area, severity=severity)