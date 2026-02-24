# app/services/hf_models/rehab_json_generator.py
from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Tuple


PAIN_AREA_CONTEXT = {
    "손목": "컴퓨터 작업/스마트폰 사용 등으로 인한 과사용",
    "어깨": "잘못된 자세/긴장으로 인한 근육 뭉침",
    "허리": "장시간 앉은 자세/코어 약화",
    "무릎": "계단/스쿼트 등 반복 부하",
    "목": "거북목/장시간 화면 시청",
    "발목": "접질림/불안정성",
}

# ✅ 학습(특히 compact dataset)과 동일하게 "짧은 지시"로 맞춤 (스켈레톤 제거)
PROMPT_TEMPLATE = """당신은 재활 운동 코치입니다.
통증 부위: {pain_area}
통증 설명: {pain_description}
통증 강도: {severity}/10

반드시 유효한 JSON만 출력하세요.
키: exercises, general_advice, estimated_duration_minutes
exercises 항목 키: name, description, sets, reps, duration_seconds, cautions, difficulty, youtube_keywords
difficulty는 "쉬움"/"보통"/"어려움" 중 하나.

출력은 반드시 '{{' 로 시작하고 '}}' 로 끝나야 합니다. 다른 텍스트 금지.
"""


class LocalRehabModelUnavailable(RuntimeError):
    pass


class LocalRehabGenerationError(RuntimeError):
    pass


_SINGLETON: Optional[Tuple[Any, Any, Any, Any]] = None  # (torch, device, tokenizer, model)
_LOAD_ERROR: Optional[str] = None


def _build_prompt(pain_area: str, pain_description: str, severity: int) -> str:
    return PROMPT_TEMPLATE.format(
        pain_area=(pain_area or "").strip(),
        pain_description=(pain_description or "특별한 설명 없음").strip(),
        severity=int(severity),
    )


def _try_load(adapter_dir: str):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel, PeftConfig

    if not os.path.isdir(adapter_dir):
        raise FileNotFoundError(
            f"REHAB_LOCAL_LORA_DIR='{adapter_dir}' 디렉토리가 없습니다. "
            f"(학습 후 adapter 경로를 지정하세요.)"
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


def _extract_json_balanced(text: str) -> Dict[str, Any]:
    """
    ✅ 문자열 내부의 { } 는 무시하고, 실제 JSON 객체의 시작~끝을 찾아 파싱한다.
    """
    t = (text or "").strip()
    t = t.replace("```json", "").replace("```", "").strip()

    start = t.find("{")
    if start == -1:
        raise LocalRehabGenerationError("모델 출력에서 JSON 시작 '{'를 찾지 못했습니다.")

    depth = 0
    in_string = False
    escape = False
    end = None

    for i in range(start, len(t)):
        ch = t[i]

        if in_string:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = False
            continue

        # not in string
        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end is None:
        # 마지막 '}'라도 있으면 시도
        last = t.rfind("}")
        if last == -1 or last <= start:
            raise LocalRehabGenerationError("모델 출력에서 JSON 객체를 찾지 못했습니다(닫는 '}' 없음).")
        end = last

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

        def to_int(x, d):
            try:
                return int(x)
            except Exception:
                return d

        out_ex = {
            "name": name or "기본 스트레칭",
            "description": desc or "1) 천천히 진행\n2) 통증 시 중단\n3) 호흡 유지",
            "sets": to_int(ex.get("sets"), 3),
            "reps": to_int(ex.get("reps"), 10),
            "duration_seconds": to_int(ex.get("duration_seconds"), 15),
            "cautions": ex.get("cautions") if isinstance(ex.get("cautions"), list) else ["통증 증가 시 중단"],
            "difficulty": ex.get("difficulty") if ex.get("difficulty") in {"쉬움", "보통", "어려움"} else "쉬움",
            "youtube_keywords": ex.get("youtube_keywords") if isinstance(ex.get("youtube_keywords"), list) else ["스트레칭", "stretch"],
        }

        if out_ex["youtube_keywords"]:
            out_ex["youtube_search_url"] = _youtube_search_url(out_ex["youtube_keywords"][0])
        else:
            out_ex["youtube_search_url"] = None

        norm_ex.append(out_ex)

    if not norm_ex:
        raise LocalRehabGenerationError("정상화 이후 exercises가 비었습니다.")

    general_advice = str(obj.get("general_advice") or "").strip()
    if not general_advice:
        general_advice = "무리하지 않는 범위에서 하루 1~2회 반복하세요. 통증이 지속되면 전문가 상담이 필요합니다."

    est = obj.get("estimated_duration_minutes", 10)
    try:
        est = int(est)
    except Exception:
        est = 10

    return {
        "pain_area": (pain_area or "").strip(),
        "severity": int(severity),
        "exercises": norm_ex,
        "general_advice": general_advice,
        "estimated_duration_minutes": est,
    }


def generate_local_rehab_recommendation(
    pain_area: str,
    pain_description: str,
    severity: int,
    max_new_tokens: int = 256,
    temperature: float = 0.0,   # ✅ 기본은 결정적 생성
    top_p: float = 1.0,
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

    # GPT2 계열 컨텍스트 제한(보통 1024)
    max_ctx = getattr(model.config, "n_positions", 1024) or 1024

    with torch.inference_mode():
        reserve = min(256, max(64, int(max_new_tokens)))
        max_input_len = max(64, max_ctx - reserve)

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max_input_len,
        ).to(device)

        prompt_len = inputs["input_ids"].shape[1]
        remaining = max_ctx - prompt_len - 1
        if remaining < 32:
            raise LocalRehabGenerationError(
                f"프롬프트가 너무 길어서 생성 여유가 없습니다. (prompt_len={prompt_len}, max_ctx={max_ctx})"
            )

        do_sample = temperature is not None and float(temperature) > 0.0

        gen_kwargs = dict(
            max_new_tokens=min(int(max_new_tokens), remaining),
            do_sample=do_sample,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3,
        )

        if do_sample:
            gen_kwargs["temperature"] = float(temperature)
            gen_kwargs["top_p"] = float(top_p)

        gen_ids = model.generate(**inputs, **gen_kwargs)
        new_tokens = gen_ids[0][prompt_len:]
        gen_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    try:
        obj = _extract_json_balanced(gen_text)
    except LocalRehabGenerationError:
        print("=== RAW GEN TEXT (first 1500 chars) ===")
        print(gen_text[:1500])
        raise

    return _normalize_output(obj, pain_area=pain_area, severity=severity)