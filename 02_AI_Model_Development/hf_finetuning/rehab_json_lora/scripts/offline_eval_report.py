# 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/offline_eval_report.py
import os
import sys
import json
import csv
import argparse
import random
from datetime import datetime
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# scripts 폴더에서 실행해도 app import 되도록
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, PROJECT_ROOT)

# 서빙 스키마와 동일 기준으로 검증(있으면 강력)
try:
    from app.schemas.rehabilitation import RehabilitationRecommendation  # type: ignore
    _HAS_PYDANTIC_SCHEMA = True
except Exception:
    RehabilitationRecommendation = None
    _HAS_PYDANTIC_SCHEMA = False

# 로컬 LoRA 생성(옵션)
try:
    from app.services.hf_models.rehab_json_generator import generate_local_rehab_recommendation  # type: ignore
    _HAS_LOCAL_GENERATOR = True
except Exception:
    generate_local_rehab_recommendation = None
    _HAS_LOCAL_GENERATOR = False


ALLOWED_DIFFICULTY = {"쉬움", "보통", "어려움"}

EN_SYNONYM = {
    "손목": "wrist",
    "어깨": "shoulder",
    "허리": "lower back",
    "목": "neck",
    "무릎": "knee",
    "발목": "ankle",
}

EXERCISE_LIBRARY = {
    "손목": [
        ("손목 신전 스트레칭", "1. 팔을 앞으로 펴세요\n2. 반대 손으로 손등을 부드럽게 당기세요\n3. 15초 유지"),
        ("손목 굴곡 스트레칭", "1. 손바닥이 위로 오게 팔을 펴세요\n2. 손가락을 아래로 부드럽게 눌러주세요\n3. 15초 유지"),
        ("전완근 이완 마사지", "1. 팔뚝 근육을 천천히 문질러주세요\n2. 뭉친 부위를 10~20초 압박\n3. 통증이 심하면 중단"),
        ("손목 회전 가동성", "1. 손목을 천천히 원을 그리듯 돌리세요\n2. 통증 없는 범위에서 반복\n3. 양방향 진행"),
        ("손가락/손목 펌핑", "1. 손을 가볍게 쥐었다 펴세요\n2. 호흡을 유지하며 반복\n3. 통증이 증가하면 중단"),
    ],
    "어깨": [
        ("어깨 원그리기", "1. 어깨를 천천히 앞으로 돌리세요\n2. 뒤로도 반복\n3. 반동 없이 진행"),
        ("흉근 스트레칭", "1. 문틀에 팔을 올리세요\n2. 가슴이 늘어나도록 상체를 이동\n3. 15초 유지"),
        ("견갑골 리트랙션", "1. 어깨를 내리고\n2. 날개뼈를 뒤로 모으세요\n3. 2초 유지 후 풀기"),
        ("승모근 스트레칭", "1. 고개를 옆으로 기울이세요\n2. 반대 손으로 가볍게 당기기\n3. 15초 유지"),
        ("밴드 외회전", "1. 팔꿈치를 몸통에 붙이고\n2. 바깥으로 천천히 회전\n3. 통증 없는 범위"),
    ],
    "허리": [
        ("무릎 당기기", "1. 등을 대고 눕기\n2. 한쪽 무릎을 가슴으로 당기기\n3. 15초 유지"),
        ("고양이-소 자세", "1. 네발기기\n2. 등을 둥글게 말기\n3. 허리를 부드럽게 펴기"),
        ("햄스트링 스트레칭", "1. 다리를 앞으로 뻗기\n2. 엉덩이를 접어 상체 숙이기\n3. 15초 유지"),
        ("브릿지", "1. 무릎 굽혀 눕기\n2. 엉덩이를 들어 올리기\n3. 2초 유지 후 내리기"),
        ("맥켄지 익스텐션", "1. 엎드려 상체만 들어 올리기\n2. 허리 과신전 주의\n3. 통증 시 중단"),
    ],
    "목": [
        ("턱 당기기", "1. 턱을 뒤로 당기기\n2. 목 뒤를 길게 만들기\n3. 2초 유지"),
        ("상부 승모근 스트레칭", "1. 고개를 옆으로 기울이기\n2. 15초 유지\n3. 반대쪽도 반복"),
        ("흉추 신전", "1. 등받이에 기대기\n2. 가슴을 열며 확장\n3. 호흡 유지"),
        ("목 가동성 회전", "1. 고개를 천천히 좌/우로 돌리기\n2. 통증 없는 범위\n3. 반동 금지"),
        ("견갑 안정화", "1. 어깨를 내리고\n2. 날개뼈를 뒤로 모으기\n3. 2초 유지"),
    ],
    "무릎": [
        ("대퇴사두근 스트레칭", "1. 서서 발목을 잡기\n2. 무릎을 모으기\n3. 15초 유지"),
        ("햄스트링 스트레칭", "1. 다리를 뻗고\n2. 상체를 천천히 숙이기\n3. 15초 유지"),
        ("힙 힌지 스쿼트(가벼움)", "1. 엉덩이를 뒤로\n2. 무릎 안쪽 붕괴 주의\n3. 통증 없는 범위"),
        ("종아리 스트레칭", "1. 벽에 손 대기\n2. 뒤꿈치 바닥 고정\n3. 15초 유지"),
        ("무릎 주변 근력 활성", "1. 허벅지에 힘주기\n2. 2초 유지\n3. 반복"),
    ],
    "발목": [
        ("발목 펌핑", "1. 발끝을 위/아래로 움직이기\n2. 천천히 반복\n3. 통증 시 중단"),
        ("발목 원그리기", "1. 발목을 천천히 회전\n2. 양방향 진행\n3. 범위 점진 증가"),
        ("종아리 스트레칭", "1. 벽에 손\n2. 뒤꿈치 고정\n3. 15초 유지"),
        ("밴드 저항 발목 운동", "1. 밴드로 저항\n2. 천천히 당기기\n3. 통증 없는 범위"),
        ("균형 잡기(가벼움)", "1. 한발 서기\n2. 10~20초 유지\n3. 필요 시 지지"),
    ],
}


def _norm_text(x: Any) -> str:
    return str(x or "").strip()


def _clamp_int(x: Any, default: int, lo: int, hi: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = int(default)
    return max(lo, min(hi, v))


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _safe_json_loads(s: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            return None, "response_not_dict"
        return obj, None
    except Exception:
        return None, "response_json_parse_fail"


def _estimate_duration_minutes(num_ex: int, severity: int) -> int:
    base = 10 + max(0, num_ex - 3) * 2
    if severity >= 8:
        base += 2
    return _clamp_int(base, 10, 5, 60)


def _general_advice(severity: int) -> str:
    if severity >= 8:
        return f"통증 강도가 높습니다({severity}/10). 무리한 운동은 피하고, 증상이 지속되면 전문가 상담이 필요합니다."
    if severity >= 5:
        return f"통증 강도가 중간입니다({severity}/10). 통증 없는 범위에서 가볍게 반복하고, 휴식을 자주 가져주세요."
    return f"통증 강도가 낮은 편입니다({severity}/10). 무리하지 않는 범위에서 꾸준히 반복하세요."


def demo_generate(
    pain_area: str,
    pain_description: str,
    severity: int,
    rng: random.Random,
    inject_error_rate: float = 0.0,
) -> Dict[str, Any]:
    """
    ML 없이도 '그럴듯한' 구조화 추천 JSON을 생성하는 데모 생성기.
    - 기본은 항상 valid output
    - inject_error_rate > 0이면 일부 샘플에 의도적 오류를 주입(평가 데모용)
    """
    pa = _norm_text(pain_area)
    sev = _clamp_int(severity, 5, 1, 10)

    # exercise 개수: severity 낮을수록 많게(데모)
    if sev <= 3:
        n_ex = 5
    elif sev <= 6:
        n_ex = 4
    else:
        n_ex = 3

    library = EXERCISE_LIBRARY.get(pa) or EXERCISE_LIBRARY["허리"]
    selected = library[:n_ex]

    # 난이도: 통증이 심할수록 쉬움 위주
    if sev >= 8:
        difficulty = "쉬움"
        sets, reps, dur = 2, 8, 15
    elif sev >= 5:
        difficulty = "보통"
        sets, reps, dur = 3, 10, 15
    else:
        difficulty = "보통"
        sets, reps, dur = 3, 12, 15

    en = EN_SYNONYM.get(pa, "stretch")

    exercises: List[Dict[str, Any]] = []
    for name, desc in selected:
        exercises.append(
            {
                "name": name,
                "description": desc,
                "sets": int(sets),
                "reps": int(reps),
                "duration_seconds": int(dur),
                "cautions": ["통증이 증가하면 즉시 중단하세요", "반동을 주지 말고 천천히 진행하세요"],
                "difficulty": difficulty,
                "youtube_keywords": [f"{pa} 스트레칭", en],
            }
        )

    out = {
        "pain_area": pa,
        "severity": sev,
        "exercises": exercises,
        "general_advice": _general_advice(sev),
        "estimated_duration_minutes": _estimate_duration_minutes(len(exercises), sev),
    }

    # 의도적 오류 주입(옵션)
    if inject_error_rate > 0 and rng.random() < inject_error_rate:
        err_type = rng.choice(["drop_key", "bad_range", "bad_difficulty", "too_few"])
        if err_type == "drop_key":
            out.pop("general_advice", None)
        elif err_type == "bad_range":
            out["exercises"][0]["sets"] = 0
        elif err_type == "bad_difficulty":
            out["exercises"][0]["difficulty"] = "중간"
        elif err_type == "too_few":
            out["exercises"] = out["exercises"][:2]

    return out


def _validate_rules(out: Dict[str, Any], min_ex: int, max_ex: int) -> Optional[str]:
    if not isinstance(out, dict):
        return "out_not_dict"

    if not _norm_text(out.get("pain_area")):
        return "missing_pain_area"
    if not isinstance(out.get("severity"), int) or not (1 <= out["severity"] <= 10):
        return "severity_invalid"

    required_top = {"exercises", "general_advice", "estimated_duration_minutes"}
    if not required_top.issubset(set(out.keys())):
        return "missing_top_keys"

    exs = out.get("exercises")
    if not isinstance(exs, list):
        return "exercises_not_list"
    if len(exs) < min_ex:
        return "exercises_too_few"
    if len(exs) > max_ex:
        return "exercises_too_many"

    required_ex = {
        "name",
        "description",
        "sets",
        "reps",
        "duration_seconds",
        "cautions",
        "difficulty",
        "youtube_keywords",
    }
    for ex in exs:
        if not isinstance(ex, dict):
            return "exercise_not_dict"
        if not required_ex.issubset(set(ex.keys())):
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


def _validate_pydantic(out: Dict[str, Any]) -> Optional[str]:
    if not _HAS_PYDANTIC_SCHEMA:
        return None
    try:
        RehabilitationRecommendation(**out)  # type: ignore
        return None
    except Exception:
        return "pydantic_schema_fail"


def _precision_at_k(out: Dict[str, Any], expected_keywords: List[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    - precision@k: k = #exercises, 각 exercise text에 expected_keywords 중 하나라도 포함되면 hit
    - coverage: expected_keywords 전체 중 출력에 한 번이라도 등장한 비율
    """
    if not expected_keywords:
        return None, None
    exs = out.get("exercises")
    if not isinstance(exs, list) or len(exs) == 0:
        return 0.0, 0.0

    expected = [k.lower() for k in expected_keywords if _norm_text(k)]
    if not expected:
        return None, None

    all_text = []
    hits = 0
    for ex in exs:
        if not isinstance(ex, dict):
            continue
        text = " ".join(
            [
                _norm_text(ex.get("name")),
                _norm_text(ex.get("description")),
                " ".join([_norm_text(x) for x in (ex.get("youtube_keywords") or [])]),
            ]
        ).lower()
        all_text.append(text)
        if any(k in text for k in expected):
            hits += 1

    precision = hits / max(1, len(exs))

    joined = " ".join(all_text)
    covered = sum(1 for k in expected if k in joined)
    coverage = covered / max(1, len(expected))

    return round(precision, 4), round(coverage, 4)


def write_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def write_jsonl(path: str, rows: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inputs_jsonl", type=str, required=True)

    # demo: 모델 없이 결과 생성 + 평가
    # local: 로컬 LoRA 생성 결과 평가(모델 준비 필요)
    # dataset: jsonl의 response(JSON 문자열) 자체 검증
    p.add_argument("--mode", type=str, default="demo", choices=["demo", "local", "dataset"])

    p.add_argument("--out_dir", type=str, default="artifacts/offline_eval")
    p.add_argument("--max_samples", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)

    p.add_argument("--min_exercises", type=int, default=3)
    p.add_argument("--max_exercises", type=int, default=5)

    # demo 전용
    p.add_argument("--inject_error_rate", type=float, default=0.0)

    # outputs
    p.add_argument("--write_predictions", action="store_true", help="predictions.jsonl도 저장")
    args = p.parse_args()

    rng = random.Random(args.seed)
    items = _read_jsonl(args.inputs_jsonl)
    rng.shuffle(items)
    if args.max_samples > 0:
        items = items[: args.max_samples]

    if args.mode == "local" and not _HAS_LOCAL_GENERATOR:
        raise RuntimeError(
            "mode=local 이지만 로컬 생성 모듈 import 실패.\n"
            "- requirements-ml.txt 설치 여부\n"
            "- app/services/hf_models/rehab_json_generator.py 존재 여부\n"
            "- REHAB_LOCAL_LORA_DIR 설정\n"
            "을 확인하세요."
        )

    total = len(items)
    reasons = Counter()

    json_ok = 0
    rule_ok = 0
    schema_ok = 0

    precision_vals: List[float] = []
    coverage_vals: List[float] = []
    num_ex_hist = Counter()
    avg_duration_vals: List[int] = []

    per_row_csv: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []

    for i, it in enumerate(items):
        sample_id = it.get("id", i)
        pain_area = _norm_text(it.get("pain_area"))
        pain_description = _norm_text(it.get("pain_description"))
        severity = _clamp_int(it.get("severity"), 5, 1, 10)
        expected_keywords = it.get("expected_keywords") or []
        if not isinstance(expected_keywords, list):
            expected_keywords = [str(expected_keywords)]

        out: Optional[Dict[str, Any]] = None
        err: Optional[str] = None

        try:
            if args.mode == "demo":
                out = demo_generate(
                    pain_area=pain_area,
                    pain_description=pain_description,
                    severity=severity,
                    rng=rng,
                    inject_error_rate=float(args.inject_error_rate),
                )
                json_ok += 1

            elif args.mode == "local":
                out = generate_local_rehab_recommendation(  # type: ignore
                    pain_area=pain_area,
                    pain_description=pain_description,
                    severity=severity,
                )
                json_ok += 1

            elif args.mode == "dataset":
                resp = it.get("response")
                if not isinstance(resp, str):
                    err = "response_not_string"
                else:
                    obj, parse_err = _safe_json_loads(resp)
                    if parse_err:
                        err = parse_err
                    else:
                        out = {
                            "pain_area": pain_area,
                            "severity": severity,
                            **obj,  # type: ignore
                        }
                        json_ok += 1

        except Exception as e:
            err = f"exception:{type(e).__name__}"

        # 실패(생성/파싱)
        if out is None:
            reasons[err or "unknown_error"] += 1
            failures.append(
                {
                    "id": sample_id,
                    "reason": err or "unknown_error",
                    "meta": {"pain_area": pain_area, "severity": severity, "pain_description": pain_description[:120]},
                }
            )
            per_row_csv.append(
                {
                    "id": sample_id,
                    "pain_area": pain_area,
                    "severity": severity,
                    "num_exercises": "",
                    "json_ok": 0,
                    "rule_ok": 0,
                    "schema_ok": 0,
                    "precision_at_k": "",
                    "coverage": "",
                    "failure_reason": err or "unknown_error",
                }
            )
            continue

        # 규칙 검증
        rule_reason = _validate_rules(out, min_ex=args.min_exercises, max_ex=args.max_exercises)
        if rule_reason is None:
            rule_ok += 1
            rule_ok_flag = 1
        else:
            reasons[rule_reason] += 1
            rule_ok_flag = 0

        # 스키마 검증
        schema_reason = _validate_pydantic(out)
        if schema_reason is None:
            schema_ok += 1
            schema_ok_flag = 1
        else:
            reasons[schema_reason] += 1
            schema_ok_flag = 0

        # precision@k / coverage
        p_at_k, cov = _precision_at_k(out, expected_keywords)
        if p_at_k is not None:
            precision_vals.append(float(p_at_k))
        if cov is not None:
            coverage_vals.append(float(cov))

        # 분포
        exs = out.get("exercises") or []
        n_ex = len(exs) if isinstance(exs, list) else 0
        num_ex_hist[n_ex] += 1

        edm = out.get("estimated_duration_minutes")
        if isinstance(edm, int):
            avg_duration_vals.append(edm)

        # 기록
        failure_reason = ""
        if rule_reason is not None:
            failure_reason = rule_reason
        elif schema_reason is not None:
            failure_reason = schema_reason

        per_row_csv.append(
            {
                "id": sample_id,
                "pain_area": pain_area,
                "severity": severity,
                "num_exercises": n_ex,
                "json_ok": 1,
                "rule_ok": rule_ok_flag,
                "schema_ok": schema_ok_flag,
                "precision_at_k": p_at_k if p_at_k is not None else "",
                "coverage": cov if cov is not None else "",
                "failure_reason": failure_reason,
            }
        )

        if failure_reason:
            failures.append(
                {
                    "id": sample_id,
                    "reason": failure_reason,
                    "meta": {"pain_area": pain_area, "severity": severity, "pain_description": pain_description[:120]},
                    "out_summary": {
                        "pain_area": out.get("pain_area"),
                        "severity": out.get("severity"),
                        "num_exercises": n_ex,
                        "estimated_duration_minutes": out.get("estimated_duration_minutes"),
                        "exercise_names": [e.get("name") for e in exs[:5] if isinstance(e, dict)],
                    },
                }
            )

        if args.write_predictions:
            predictions.append({"id": sample_id, "input": it, "output": out})

    # 집계 리포트
    def _mean(xs: List[float]) -> float:
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    avg_num_ex = 0.0
    if total > 0:
        total_ex = sum(k * v for k, v in num_ex_hist.items())
        avg_num_ex = round(total_ex / total, 4)

    avg_duration = round(sum(avg_duration_vals) / len(avg_duration_vals), 4) if avg_duration_vals else 0.0

    report = {
        "mode": args.mode,
        "inputs_jsonl": args.inputs_jsonl,
        "evaluated_samples": total,
        "seed": args.seed,
        "min_exercises": args.min_exercises,
        "max_exercises": args.max_exercises,
        "inject_error_rate": float(args.inject_error_rate) if args.mode == "demo" else None,
        "has_pydantic_schema": _HAS_PYDANTIC_SCHEMA,
        "has_local_generator": _HAS_LOCAL_GENERATOR,
        "json_ok_rate": round(json_ok / total, 4) if total else 0.0,
        "rule_ok_rate": round(rule_ok / total, 4) if total else 0.0,
        "schema_ok_rate": round(schema_ok / total, 4) if total else 0.0,
        "avg_precision_at_k": _mean(precision_vals),
        "avg_expected_keyword_coverage": _mean(coverage_vals),
        "avg_num_exercises": avg_num_ex,
        "exercise_count_hist": {str(k): int(v) for k, v in sorted(num_ex_hist.items(), key=lambda x: x[0])},
        "avg_estimated_duration_minutes": avg_duration,
        "fail_reasons": dict(reasons),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    out_json = os.path.join(args.out_dir, "report.json")
    out_csv = os.path.join(args.out_dir, "report.csv")
    out_fail = os.path.join(args.out_dir, "failures.jsonl")
    out_pred = os.path.join(args.out_dir, "predictions.jsonl")

    write_json(out_json, report)
    write_csv(
        out_csv,
        per_row_csv,
        fieldnames=[
            "id",
            "pain_area",
            "severity",
            "num_exercises",
            "json_ok",
            "rule_ok",
            "schema_ok",
            "precision_at_k",
            "coverage",
            "failure_reason",
        ],
    )
    write_jsonl(out_fail, failures)

    if args.write_predictions:
        write_jsonl(out_pred, predictions)

    print(f"[OK] report: {out_json}")
    print(f"[OK] csv: {out_csv}")
    print(f"[OK] failures: {out_fail}")
    if args.write_predictions:
        print(f"[OK] predictions: {out_pred}")


if __name__ == "__main__":
    main()