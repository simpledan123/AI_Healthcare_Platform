# 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/validate_rehab_sft_dataset.py
import argparse
import json

REQUIRED_TOP_KEYS = {"exercises", "general_advice", "estimated_duration_minutes"}
REQUIRED_EX_KEYS = {
    "name",
    "description",
    "sets",
    "reps",
    "duration_seconds",
    "cautions",
    "difficulty",
    "youtube_keywords",
}

ALLOWED_DIFFICULTY = {"쉬움", "보통", "어려움"}


def validate_one(line_obj, min_exercises: int, max_exercises: int):
    # response는 JSON 문자열이어야 함
    resp_text = line_obj.get("response", "")
    if not isinstance(resp_text, str) or "{" not in resp_text:
        return False, "response_not_json_string"

    try:
        resp = json.loads(resp_text)
    except Exception:
        return False, "response_json_parse_fail"

    if not isinstance(resp, dict):
        return False, "response_not_dict"
    if not REQUIRED_TOP_KEYS.issubset(set(resp.keys())):
        return False, "missing_top_keys"

    exs = resp.get("exercises")
    if not isinstance(exs, list) or len(exs) < 1:
        return False, "exercises_invalid"

    if len(exs) < min_exercises:
        return False, "exercises_too_few"
    if len(exs) > max_exercises:
        return False, "exercises_too_many"

    for ex in exs:
        if not isinstance(ex, dict):
            return False, "exercise_not_dict"
        if not REQUIRED_EX_KEYS.issubset(set(ex.keys())):
            return False, "missing_exercise_keys"

        if not isinstance(ex.get("cautions"), list):
            return False, "cautions_not_list"
        if not isinstance(ex.get("youtube_keywords"), list):
            return False, "youtube_keywords_not_list"

        # 타입/범위 체크
        if not isinstance(ex.get("sets"), int) or not (1 <= ex["sets"] <= 10):
            return False, "sets_out_of_range"
        if not isinstance(ex.get("reps"), int) or not (1 <= ex["reps"] <= 50):
            return False, "reps_out_of_range"
        if not isinstance(ex.get("duration_seconds"), int) or not (5 <= ex["duration_seconds"] <= 300):
            return False, "duration_out_of_range"

        if ex.get("difficulty") not in ALLOWED_DIFFICULTY:
            return False, "difficulty_invalid"

        if not isinstance(ex.get("name"), str) or len(ex["name"].strip()) < 2:
            return False, "name_too_short"
        if not isinstance(ex.get("description"), str) or len(ex["description"].strip()) < 10:
            return False, "description_too_short"

    ga = resp.get("general_advice")
    if not isinstance(ga, str) or len(ga.strip()) < 5:
        return False, "general_advice_too_short"

    edm = resp.get("estimated_duration_minutes")
    if not isinstance(edm, int) or not (5 <= edm <= 60):
        return False, "estimated_duration_invalid"

    return True, "ok"


def main(path: str, min_exercises: int, max_exercises: int):
    total = 0
    ok = 0
    reasons = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                obj = json.loads(line)
            except Exception:
                reasons["line_json_parse_fail"] = reasons.get("line_json_parse_fail", 0) + 1
                continue

            is_ok, reason = validate_one(obj, min_exercises=min_exercises, max_exercises=max_exercises)
            if is_ok:
                ok += 1
            else:
                reasons[reason] = reasons.get(reason, 0) + 1

    print(f"file: {path}")
    print(f"total: {total}")
    print(f"ok: {ok}")
    print(f"fail: {total - ok}")
    if reasons:
        print("reasons:")
        for k, v in sorted(reasons.items(), key=lambda x: (-x[1], x[0])):
            print(f"- {k}: {v}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", type=str, required=True)
    p.add_argument("--min_exercises", type=int, default=3)
    p.add_argument("--max_exercises", type=int, default=5)
    args = p.parse_args()
    main(args.jsonl, min_exercises=args.min_exercises, max_exercises=args.max_exercises)