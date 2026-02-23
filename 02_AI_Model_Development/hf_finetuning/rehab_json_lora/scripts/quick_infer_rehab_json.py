# 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/quick_infer_rehab_json.py
import os
import sys
import json
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, PROJECT_ROOT)

from app.services.hf_models.rehab_json_generator import generate_local_rehab_recommendation  # noqa


def main(pain_area: str, pain_description: str, severity: int):
    out = generate_local_rehab_recommendation(
        pain_area=pain_area,
        pain_description=pain_description,
        severity=severity,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pain_area", type=str, required=True)
    p.add_argument("--pain_description", type=str, required=True)
    p.add_argument("--severity", type=int, required=True)
    args = p.parse_args()

    main(args.pain_area, args.pain_description, args.severity)