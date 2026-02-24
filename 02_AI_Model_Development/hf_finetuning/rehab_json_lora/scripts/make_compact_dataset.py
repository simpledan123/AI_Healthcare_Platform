import json
import argparse

def compact_exercise(ex):
    # 필수 키 보장 + 너무 긴 description 줄이기
    name = (ex.get("name") or "스트레칭").strip()
    desc = (ex.get("description") or "1) 천천히 진행\n2) 통증 시 중단\n3) 호흡 유지").strip()
    # 3줄만 남기기
    lines = [l.strip() for l in desc.splitlines() if l.strip()][:3]
    desc = "\\n".join(lines) if lines else "1) 천천히 진행\\n2) 통증 시 중단\\n3) 호흡 유지"

    def to_int(x, d):
        try: return int(x)
        except: return d

    return {
        "name": name,
        "description": desc,
        "sets": to_int(ex.get("sets"), 3),
        "reps": to_int(ex.get("reps"), 10),
        "duration_seconds": to_int(ex.get("duration_seconds"), 15),
        "cautions": (ex.get("cautions") or ["통증 증가 시 중단"])[:2],
        "difficulty": ex.get("difficulty") if ex.get("difficulty") in ["쉬움","보통","어려움"] else "쉬움",
        "youtube_keywords": (ex.get("youtube_keywords") or ["스트레칭","stretch"])[:2],
    }

def compact_prompt(pa, desc, sev):
    return (
        "당신은 재활 운동 코치입니다.\n"
        f"통증 부위: {pa}\n"
        f"통증 설명: {desc}\n"
        f"통증 강도: {sev}/10\n\n"
        "반드시 유효한 JSON만 출력하세요.\n"
        "키: exercises, general_advice, estimated_duration_minutes\n"
    )

def main(inp, outp, max_items=0):
    n = 0
    with open(inp, "r", encoding="utf-8") as fin, open(outp, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line: 
                continue
            obj = json.loads(line)

            pa = obj.get("pain_area","")
            sev = obj.get("severity",5)
            pd = obj.get("pain_description","")

            # response(JSON 문자열) 파싱
            resp = json.loads(obj["response"])
            exs = resp.get("exercises", [])[:3]  # 3개 고정
            exs = [compact_exercise(e) for e in exs]

            resp2 = {
                "exercises": exs,
                "general_advice": (resp.get("general_advice") or "무리하지 않는 범위에서 진행하세요.")[:120],
                "estimated_duration_minutes": int(resp.get("estimated_duration_minutes", 10)),
            }

            out = {
                "record_id": obj.get("record_id", n),
                "pain_area": pa,
                "severity": int(sev),
                "pain_description": pd[:120],
                "prompt": compact_prompt(pa, pd[:120], int(sev)),
                "response": json.dumps(resp2, ensure_ascii=False),
            }

            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
            if max_items and n >= max_items:
                break

    print(f"[OK] wrote {n} items -> {outp}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True)
    ap.add_argument("--outp", required=True)
    ap.add_argument("--max_items", type=int, default=0, help="0이면 전체")
    args = ap.parse_args()
    main(args.inp, args.outp, args.max_items)