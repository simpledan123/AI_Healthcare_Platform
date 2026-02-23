# 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/eval_rehab_json_generator.py
import os
import sys
import json
import argparse
import random
from datetime import datetime
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

# scripts 폴더에서 실행해도 app import 되도록
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, PROJECT_ROOT)

# Pydantic 스키마 검증(서빙 스키마와 동일 기준)
from app.schemas.rehabilitation import RehabilitationRecommendation  # noqa

# 로컬 생성 모델(옵션 평가 모드)
try:
    from app.services.hf_models.rehab_json_generator import generate_local_rehab_recommendation  # noqa
    _LOCAL_AVAILABLE = True
except Exception:
    # requirements-ml.txt 설치 안 되어도 dataset 평가 모드는 돌 수 있게
    _LOCAL_AVAILABLE = False


ALLOWED_DIFFICULTY = {"쉬움", "보통", "어려움"}


def _norm_text(x: Any) -> str:
    return str(x or "").strip()


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _safe_json_loads(s: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    response가 JSON 문자열일 때 파싱.
    """
    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            return None, "response_not_dict"
        return obj, None
    except Exception:
        return None, "response_json_parse_fail"


def _validate_output_dict(
    out: Dict[str, Any],
    min_exercises: int = 3,
    max_exercises: int = 5,
) -> Optional[str]:
    """
    PR-F2 수준의 '실사용 검증'과 유사한 규칙으로 결과를 체크.
    통과면 None, 실패면 reason 문자열.
    """
    if not isinstance(out, dict):
        return "out_not_dict"

    # 최종 서빙 스키마 기준: pain_area/severity 존재해야 함
    if not _norm_text(out.get("pain_area")):
        return "missing_pain_area"
    if not isinstance(out.get("severity"), int) or not (1 <= out["severity"] <= 10):
        return "severity_invalid"

    if "exercises" not in out or "general_advice" not in out or "estimated_duration_minutes" not in out:
        return "missing_top_keys"

    exs = out.get("exercises")
    if not isinstance(exs, list):
        return "exercises_not_list"
    if len(exs) < min_exercises:
        return "exercises_too_few"
    if len(exs) > max_exercises:
        return "exercises_too_many"

    for ex in exs:
        if not isinstance(ex, dict):
            return "exercise_not_dict"

        required = {
            "name",
            "description",
            "sets",
            "reps",
            "duration_seconds",
            "cautions",
            "difficulty",
            "youtube_keywords",
        }
        if not required.issubset(set(ex.keys())):
            return "exercise_missing_keys"

        if not isinstance(ex["cautions"], list):
            return "cautions_not_list"
        if not isinstance(ex["youtube_keywords"], list):
            return "youtube_keywords_not_list"

        if not isinstance(ex["sets"], int) or not (1 <= ex["sets"] <= 10):
            return "sets_out_of_range"
        if not isinstance(ex["reps"], int) or not (1 <= ex["reps"] <= 50):
            return "reps_out_of_range"
        if not isinstance(ex["duration_seconds"], int) or not (5 <= ex["duration_seconds"] <= 300):
            return "duration_out_of_range"

        if _norm_text(ex["difficulty"]) not in ALLOWED_DIFFICULTY:
            return "difficulty_invalid"

        if len(_norm_text(ex["name"])) < 2:
            return "name_too_short"
        if len(_norm_text(ex["description"])) < 10:
            return "description_too_short"

    if len(_norm_text(out.get("general_advice"))) < 5:
        return "general_advice_too_short"

    edm = out.get("estimated_duration_minutes")
    if not isinstance(edm, int) or not (5 <= edm <= 60):
        return "estimated_duration_invalid"

    return None


def _pydantic_validate(out: Dict[str, Any]) -> Optional[str]:
    """
    FastAPI 응답 스키마(Pydantic) 기준 검증.
    통과면 None, 실패면 reason 문자열.
    """
    try:
        RehabilitationRecommendation(**out)
        return None
    except Exception:
        return "pydantic_schema_fail"


def _summarize_output(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    리포트용으로 출력 일부만 요약(너무 커지는 것 방지)
    """
    exs = out.get("exercises") or []
    return {
        "pain_area": out.get("pain_area"),
        "severity": out.get("severity"),
        "num_exercises": len(exs) if isinstance(exs, list) else None,
        "exercise_names": [ex.get("name") for ex in exs[:5] if isinstance(ex, dict)],
        "estimated_duration_minutes": out.get("estimated_duration_minutes"),
    }


def evaluate(
    jsonl_path: str,
    mode: str,
    out_json: str,
    failures_jsonl: Optional[str],
    max_failures: int,
    max_samples: int,
    seed: int,
    min_exercises: int,
    max_exercises: int,
):
    """
    mode:
      - dataset: jsonl의 response(정답/라벨) 자체를 검증
      - local: jsonl의 입력(pain_area, pain_description, severity)으로 로컬 모델 출력 생성 후 검증
    """
    items = _read_jsonl(jsonl_path)
    rng = random.Random(seed)
    rng.shuffle(items)

    if max_samples > 0:
        items = items[:max_samples]

    total = len(items)

    # counters
    json_parse_ok = 0
    rule_ok = 0
    schema_ok = 0

    reasons = Counter()
    exercise_count_hist = Counter()
    pain_area_hist = Counter()

    # failures
    failure_rows: List[Dict[str, Any]] = []

    if mode == "local" and not _LOCAL_AVAILABLE:
        raise RuntimeError(
            "mode=local 이지만 로컬 생성 모듈 import에 실패했습니다.\n"
            "- requirements-ml.txt 설치 여부\n"
            "- app/services/hf_models/rehab_json_generator.py 존재 여부\n"
            "를 확인하세요."
        )

    for idx, item in enumerate(items):
        pain_area = _norm_text(item.get("pain_area"))
        severity = item.get("severity")
        pain_description = _norm_text(item.get("pain_description"))

        try:
            if mode == "dataset":
                # dataset response는 pain_area/severity가 없을 수 있어 merge해서 검증
                resp_str = item.get("response")
                if not isinstance(resp_str, str):
                    reasons["response_not_string"] += 1
                    if len(failure_rows) < max_failures:
                        failure_rows.append(
                            {"idx": idx, "reason": "response_not_string", "item_meta": {"pain_area": pain_area}}
                        )
                    continue

                resp_obj, err = _safe_json_loads(resp_str)
                if err:
                    reasons[err] += 1
                    if len(failure_rows) < max_failures:
                        failure_rows.append(
                            {"idx": idx, "reason": err, "item_meta": {"pain_area": pain_area}}
                        )
                    continue

                json_parse_ok += 1

                # merge
                try:
                    sev_int = int(severity)
                except Exception:
                    sev_int = 5

                out = {
                    "pain_area": pain_area,
                    "severity": sev_int,
                    **resp_obj,
                }

            elif mode == "local":
                # 로컬 모델 생성 결과는 이미 dict 형태
                try:
                    sev_int = int(severity)
                except Exception:
                    sev_int = 5

                out = generate_local_rehab_recommendation(
                    pain_area=pain_area,
                    pain_description=pain_description,
                    severity=sev_int,
                )
                json_parse_ok += 1

            else:
                raise ValueError("mode must be one of: dataset, local")

            # 규칙 검증
            rule_reason = _validate_output_dict(out, min_exercises=min_exercises, max_exercises=max_exercises)
            if rule_reason is None:
                rule_ok += 1
            else:
                reasons[rule_reason] += 1
                if len(failure_rows) < max_failures:
                    failure_rows.append(
                        {
                            "idx": idx,
                            "reason": rule_reason,
                            "item_meta": {
                                "pain_area": pain_area,
                                "severity": severity,
                                "pain_description": pain_description[:120],
                            },
                            "out_summary": _summarize_output(out),
                        }
                    )
                continue

            # Pydantic 스키마 검증
            schema_reason = _pydantic_validate(out)
            if schema_reason is None:
                schema_ok += 1
            else:
                reasons[schema_reason] += 1
                if len(failure_rows) < max_failures:
                    failure_rows.append(
                        {
                            "idx": idx,
                            "reason": schema_reason,
                            "item_meta": {
                                "pain_area": pain_area,
                                "severity": severity,
                                "pain_description": pain_description[:120],
                            },
                            "out_summary": _summarize_output(out),
                        }
                    )
                continue

            # distributions
            exs = out.get("exercises") or []
            if isinstance(exs, list):
                exercise_count_hist[len(exs)] += 1
            if pain_area:
                pain_area_hist[pain_area] += 1

        except Exception as e:
            reasons["exception"] += 1
            if len(failure_rows) < max_failures:
                failure_rows.append(
                    {
                        "idx": idx,
                        "reason": "exception",
                        "error": str(e),
                        "item_meta": {
                            "pain_area": pain_area,
                            "severity": severity,
                            "pain_description": pain_description[:120],
                        },
                    }
                )

    report = {
        "mode": mode,
        "jsonl_path": jsonl_path,
        "evaluated_samples": total,
        "seed": seed,
        "min_exercises": min_exercises,
        "max_exercises": max_exercises,
        "json_parse_ok": json_parse_ok,
        "rule_ok": rule_ok,
        "schema_ok": schema_ok,
        "json_parse_ok_rate": round(json_parse_ok / total, 4) if total else 0.0,
        "rule_ok_rate": round(rule_ok / total, 4) if total else 0.0,
        "schema_ok_rate": round(schema_ok / total, 4) if total else 0.0,
        "exercise_count_hist": dict(exercise_count_hist),
        "pain_area_hist": dict(pain_area_hist),
        "fail_reasons": dict(reasons),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if failures_jsonl:
        os.makedirs(os.path.dirname(failures_jsonl), exist_ok=True)
        with open(failures_jsonl, "w", encoding="utf-8") as f:
            for row in failure_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[OK] wrote report: {out_json}")
    if failures_jsonl:
        print(f"[OK] wrote failures: {failures_jsonl}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", type=str, required=True)
    p.add_argument("--mode", type=str, default="dataset", choices=["dataset", "local"])

    # 리포트는 artifacts 아래로(기본 .gitignore)
    p.add_argument("--out_json", type=str, default="artifacts/rehab_json_lora_eval/report.json")
    p.add_argument("--failures_jsonl", type=str, default="artifacts/rehab_json_lora_eval/failures.jsonl")
    p.add_argument("--max_failures", type=int, default=50)

    p.add_argument("--max_samples", type=int, default=200)  # 0이면 전체
    p.add_argument("--seed", type=int, default=42)

    p.add_argument("--min_exercises", type=int, default=3)
    p.add_argument("--max_exercises", type=int, default=5)

    args = p.parse_args()

    evaluate(
        jsonl_path=args.jsonl,
        mode=args.mode,
        out_json=args.out_json,
        failures_jsonl=args.failures_jsonl,
        max_failures=args.max_failures,
        max_samples=args.max_samples,
        seed=args.seed,
        min_exercises=args.min_exercises,
        max_exercises=args.max_exercises,
    )