# 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/export_rehab_sft_from_db.py
import os
import sys
import json
import argparse
from typing import Any, Dict, List, Optional
from collections import Counter

from sklearn.model_selection import train_test_split

# scripts 폴더에서 실행해도 app import 되도록
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm import joinedload  # noqa
from app.database import SessionLocal  # noqa
from app.models.rehabilitation import RehabilitationRecord  # noqa


PAIN_AREA_CONTEXT = {
    "손목": "컴퓨터 작업/스마트폰 사용 등으로 인한 과사용",
    "어깨": "잘못된 자세/긴장으로 인한 근육 뭉침",
    "허리": "장시간 앉은 자세/코어 약화",
    "무릎": "계단/스쿼트 등 반복 부하",
    "목": "거북목/장시간 화면 시청",
    "발목": "접질림/불안정성",
}

# 흔한 표기 흔들림 보정(DB 라벨이 들쑥날쑥한 경우 대비)
PAIN_AREA_ALIASES = {
    "팔목": "손목",
    "손": "손목",
    "요통": "허리",
    "경추": "목",
    "슬관절": "무릎",
    "족관절": "발목",
}

ALLOWED_DIFFICULTY = {"쉬움", "보통", "어려움"}
DIFFICULTY_ALIASES = {
    "초급": "쉬움",
    "중급": "보통",
    "고급": "어려움",
    "낮음": "쉬움",
    "중간": "보통",
    "높음": "어려움",
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


# -----------------------------
# Helpers (quality rules)
# -----------------------------
def _norm_text(s: Any) -> str:
    return str(s or "").strip()


def _norm_pain_area(pa: str) -> str:
    pa = _norm_text(pa)
    if not pa:
        return ""
    return PAIN_AREA_ALIASES.get(pa, pa)


def _clamp_int(x: Any, default: int, lo: int, hi: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = int(default)
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x if str(i).strip()]
    # DB에 문자열로 들어온 경우 대비
    s = str(x).strip()
    if not s:
        return []
    return [s]


def _norm_difficulty(x: Any) -> str:
    d = _norm_text(x)
    if not d:
        return "쉬움"
    d = DIFFICULTY_ALIASES.get(d, d)
    return d if d in ALLOWED_DIFFICULTY else "쉬움"


def _valid_description(desc: str, min_len: int) -> bool:
    d = _norm_text(desc)
    if len(d) < min_len:
        return False
    # 너무 의미 없는 반복/한 글자 반복 방지(간단)
    if len(set(d)) <= 2 and len(d) >= min_len:
        return False
    return True


def _make_general_advice(severity: int) -> str:
    if severity >= 8:
        return (
            f"통증 강도가 높은 편입니다({severity}/10). 무리한 운동은 피하고, "
            f"통증이 날카롭게 증가하거나 저림/방사통이 있으면 의료 전문가 상담이 필요합니다."
        )
    if severity >= 5:
        return (
            f"통증 강도가 중간 정도입니다({severity}/10). 무리하지 않는 범위에서 "
            f"가볍게 반복하고, 작업/일상 중 휴식을 자주 가져주세요."
        )
    return (
        f"통증 강도가 낮은 편입니다({severity}/10). 통증이 악화되지 않는 범위에서 "
        f"꾸준히 스트레칭을 반복하세요."
    )


def _estimate_duration_minutes(num_exercises: int, severity: int) -> int:
    base = 10
    base += max(0, num_exercises - 3) * 2
    if severity >= 8:
        base += 2
    return _clamp_int(base, 10, 5, 60)


def _normalize_exercise(ex: Any, pain_area: str, min_desc_len: int) -> Optional[Dict[str, Any]]:
    """
    ExerciseRecommendation(SQLAlchemy) -> dict
    품질 규칙에 맞지 않으면 None 반환.
    """
    name = _norm_text(getattr(ex, "name", ""))
    desc = _norm_text(getattr(ex, "description", ""))

    if len(name) < 2:
        return None
    if not _valid_description(desc, min_desc_len=min_desc_len):
        return None

    difficulty = getattr(ex, "difficulty", None)
    if hasattr(difficulty, "value"):
        difficulty = difficulty.value
    difficulty = _norm_difficulty(difficulty)

    sets = _clamp_int(getattr(ex, "sets", None), default=3, lo=1, hi=10)
    reps = _clamp_int(getattr(ex, "reps", None), default=10, lo=1, hi=50)
    duration = _clamp_int(getattr(ex, "duration_seconds", None), default=15, lo=5, hi=300)

    cautions = _as_list(getattr(ex, "cautions", None))
    youtube_keywords = _as_list(getattr(ex, "youtube_keywords", None))

    # youtube_keywords가 비면 최소한 생성(학습 안정성)
    if not youtube_keywords:
        youtube_keywords = [f"{pain_area} {name}", f"{pain_area} 스트레칭"]

    return {
        "name": name,
        "description": desc,
        "sets": sets,
        "reps": reps,
        "duration_seconds": duration,
        "cautions": cautions,
        "difficulty": difficulty,
        "youtube_keywords": youtube_keywords,
    }


def _validate_response_obj(obj: Dict[str, Any], min_exercises: int, max_exercises: int) -> Optional[str]:
    """
    Export 단계에서 '실사용 검증'을 돌려서
    학습 데이터가 JSON 스키마 관점에서 안정적인지 확인.
    실패 사유 문자열을 반환, 통과면 None.
    """
    if not isinstance(obj, dict):
        return "resp_not_dict"

    if "exercises" not in obj or "general_advice" not in obj or "estimated_duration_minutes" not in obj:
        return "missing_top_keys"

    exs = obj.get("exercises")
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

    if len(_norm_text(obj.get("general_advice", ""))) < 5:
        return "general_advice_too_short"

    edm = obj.get("estimated_duration_minutes")
    if not isinstance(edm, int) or not (5 <= edm <= 60):
        return "estimated_duration_invalid"

    return None


def main(
    out_dir: str,
    valid_ratio: float,
    seed: int,
    min_description_len: int,
    min_exercises: int,
    max_exercises: int,
    strict_pain_areas: bool,
    dedupe: bool,
):
    os.makedirs(out_dir, exist_ok=True)
    reasons = Counter()
    label_counter = Counter()

    db = SessionLocal()
    try:
        records: List[RehabilitationRecord] = (
            db.query(RehabilitationRecord)
            .options(joinedload(RehabilitationRecord.exercises))
            .all()
        )

        samples: List[Dict[str, Any]] = []
        seen = set()

        for r in records:
            pain_area = _norm_pain_area(getattr(r, "pain_area", ""))
            pain_description = _norm_text(getattr(r, "pain_description", ""))
            severity = _clamp_int(getattr(r, "severity", None), default=5, lo=1, hi=10)

            if not pain_area:
                reasons["skip_no_pain_area"] += 1
                continue

            if strict_pain_areas and pain_area not in PAIN_AREA_CONTEXT:
                reasons["skip_unknown_pain_area"] += 1
                continue

            # 통증 설명 너무 짧으면 버림(생성 학습 품질)
            if len(pain_description) < min_description_len:
                reasons["skip_short_description"] += 1
                continue

            # 운동 정규화/필터링
            norm_exercises: List[Dict[str, Any]] = []
            used_names = set()

            for ex in (getattr(r, "exercises", None) or []):
                nx = _normalize_exercise(ex, pain_area=pain_area, min_desc_len=min_description_len)
                if not nx:
                    reasons["skip_bad_exercise"] += 1
                    continue
                # 동일 이름 중복 제거
                if nx["name"] in used_names:
                    continue
                used_names.add(nx["name"])
                norm_exercises.append(nx)

            # 3~5개 규칙(기본)
            if len(norm_exercises) < min_exercises:
                reasons["skip_too_few_exercises"] += 1
                continue

            norm_exercises = norm_exercises[:max_exercises]

            context = PAIN_AREA_CONTEXT.get(pain_area, "일반적인 근육 통증")

            prompt = PROMPT_TEMPLATE.format(
                pain_area=pain_area,
                pain_description=pain_description,
                severity=severity,
                context=context,
            )

            response_obj = {
                "exercises": norm_exercises,
                "general_advice": _make_general_advice(severity),
                "estimated_duration_minutes": _estimate_duration_minutes(len(norm_exercises), severity),
            }

            # 실사용 검증 루프: JSON 스키마/타입/범위 체크
            fail_reason = _validate_response_obj(response_obj, min_exercises=min_exercises, max_exercises=max_exercises)
            if fail_reason is not None:
                reasons[f"skip_invalid_response_{fail_reason}"] += 1
                continue

            # 최종 line
            line_obj = {
                "record_id": int(getattr(r, "id")),
                "pain_area": pain_area,
                "severity": severity,
                "pain_description": pain_description,
                "prompt": prompt,
                "response": json.dumps(response_obj, ensure_ascii=False),
            }

            # dedupe: 같은 pain_area/description/severity 조합은 1개만
            if dedupe:
                key = (pain_area, severity, pain_description)
                if key in seen:
                    reasons["skip_duplicate"] += 1
                    continue
                seen.add(key)

            samples.append(line_obj)
            label_counter[pain_area] += 1

        if len(samples) < 5:
            raise RuntimeError(
                f"Export 가능한 샘플이 너무 적습니다: {len(samples)}개.\n"
                f"- strict_pain_areas={strict_pain_areas} 인지\n"
                f"- min_description_len={min_description_len} 이 너무 큰지\n"
                f"- min_exercises={min_exercises} 가 너무 큰지\n"
                f"확인하세요."
            )

        train_samples, valid_samples = train_test_split(
            samples, test_size=valid_ratio, random_state=seed, shuffle=True
        )

        train_path = os.path.join(out_dir, "train.jsonl")
        valid_path = os.path.join(out_dir, "valid.jsonl")

        with open(train_path, "w", encoding="utf-8") as f:
            for s in train_samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        with open(valid_path, "w", encoding="utf-8") as f:
            for s in valid_samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        print(f"[OK] train: {train_path} ({len(train_samples)})")
        print(f"[OK] valid: {valid_path} ({len(valid_samples)})")

        # 요약 출력(실행 안 해도 코드상 남겨둠)
        print("\n[Label distribution]")
        for k, v in label_counter.most_common():
            print(f"- {k}: {v}")

        if reasons:
            print("\n[Skipped reasons]")
            for k, v in reasons.most_common():
                print(f"- {k}: {v}")

    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out_dir", type=str, required=True)
    p.add_argument("--valid_ratio", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)

    # 품질 규칙(기본값은 “좀 엄격”하게)
    p.add_argument("--min_description_len", type=int, default=10)
    p.add_argument("--min_exercises", type=int, default=3)
    p.add_argument("--max_exercises", type=int, default=5)

    p.add_argument("--strict_pain_areas", action="store_true", help="PAIN_AREA_CONTEXT에 있는 라벨만 사용")
    p.add_argument("--no_dedupe", action="store_true", help="중복 제거 끄기")

    args = p.parse_args()

    main(
        out_dir=args.out_dir,
        valid_ratio=args.valid_ratio,
        seed=args.seed,
        min_description_len=args.min_description_len,
        min_exercises=args.min_exercises,
        max_exercises=args.max_exercises,
        strict_pain_areas=bool(args.strict_pain_areas),
        dedupe=not bool(args.no_dedupe),
    )