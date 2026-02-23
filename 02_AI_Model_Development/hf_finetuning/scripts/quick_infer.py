# 02_AI_Model_Development/hf_finetuning/scripts/quick_infer.py
import os
import argparse

from app.services.hf_models.pain_area_classifier import predict_pain_area


def main(text: str, top_k: int):
    pred = predict_pain_area(text, top_k=top_k)
    print(f"engine: {pred.engine}")
    print(f"predicted_label: {pred.predicted_label}")
    for c in pred.candidates:
        print(f"- {c.label}: {c.score:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=str, required=True)
    parser.add_argument("--top_k", type=int, default=3)
    args = parser.parse_args()

    main(args.text, args.top_k)