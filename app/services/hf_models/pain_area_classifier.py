# app/services/hf_models/pain_area_classifier.py
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


# -----------------------------
# Data structures
# -----------------------------
@dataclass
class PainAreaCandidate:
    label: str
    score: float


@dataclass
class PainAreaPrediction:
    predicted_label: str
    engine: str  # "hf" | "heuristic"
    candidates: List[PainAreaCandidate]


# -----------------------------
# Heuristic fallback (no torch needed)
# -----------------------------
# 한국어/영어 키워드 기반 아주 단순한 fallback
_KEYWORD_RULES: List[Tuple[str, str]] = [
    (r"(손목|손바닥|wrist|carpal|마우스|키보드)", "손목"),
    (r"(어깨|승모근|shoulder)", "어깨"),
    (r"(허리|요추|lower back|back pain|허리디스크)", "허리"),
    (r"(목|거북목|neck|cervical)", "목"),
    (r"(무릎|knee|슬개)", "무릎"),
    (r"(발목|ankle|접질)", "발목"),
]


def predict_pain_area_heuristic(text: str, top_k: int = 3) -> PainAreaPrediction:
    t = (text or "").strip()
    if not t:
        # 빈 텍스트면 기본값
        return PainAreaPrediction(
            predicted_label="허리",
            engine="heuristic",
            candidates=[PainAreaCandidate(label="허리", score=1.0)],
        )

    for pattern, label in _KEYWORD_RULES:
        if re.search(pattern, t, flags=re.IGNORECASE):
            return PainAreaPrediction(
                predicted_label=label,
                engine="heuristic",
                candidates=[PainAreaCandidate(label=label, score=1.0)],
            )

    # 아무것도 못 찾으면 기본값
    return PainAreaPrediction(
        predicted_label="허리",
        engine="heuristic",
        candidates=[PainAreaCandidate(label="허리", score=1.0)],
    )


# -----------------------------
# HF model loader (optional deps)
# -----------------------------
_MODEL_SINGLETON = None
_MODEL_ENGINE = None  # "hf" | "heuristic"
_MODEL_LOAD_ERROR: Optional[str] = None


def _try_load_hf_model(model_dir: str):
    """
    torch/transformers가 없거나 모델 디렉토리가 없으면 예외를 던짐.
    """
    import torch  # noqa
    from transformers import AutoTokenizer, AutoModelForSequenceClassification  # noqa

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
    model.eval()
    return torch, device, tokenizer, model


def get_pain_area_model():
    """
    싱글톤 로딩:
    - env: PAIN_AREA_MODEL_DIR 우선
    - 없으면 기본: artifacts/pain_area_classifier/best
    - 로딩 실패하면 heuristic로 fallback
    """
    global _MODEL_SINGLETON, _MODEL_ENGINE, _MODEL_LOAD_ERROR

    if _MODEL_ENGINE is not None:
        return _MODEL_SINGLETON, _MODEL_ENGINE, _MODEL_LOAD_ERROR

    model_dir = os.getenv("PAIN_AREA_MODEL_DIR", "artifacts/pain_area_classifier/best")

    try:
        if not os.path.isdir(model_dir):
            raise FileNotFoundError(
                f"PAIN_AREA_MODEL_DIR='{model_dir}' 디렉토리가 없습니다. "
                f"(학습 후 생성되는 artifacts/pain_area_classifier/best 를 사용하거나 env로 지정하세요.)"
            )
        _MODEL_SINGLETON = _try_load_hf_model(model_dir)
        _MODEL_ENGINE = "hf"
        _MODEL_LOAD_ERROR = None
        return _MODEL_SINGLETON, _MODEL_ENGINE, _MODEL_LOAD_ERROR

    except Exception as e:
        _MODEL_SINGLETON = None
        _MODEL_ENGINE = "heuristic"
        _MODEL_LOAD_ERROR = str(e)
        return _MODEL_SINGLETON, _MODEL_ENGINE, _MODEL_LOAD_ERROR


def predict_pain_area(text: str, top_k: int = 3) -> PainAreaPrediction:
    """
    1) HF 모델이 로드되면 HF로 예측
    2) 아니면 heuristic fallback
    """
    top_k = max(1, min(int(top_k or 3), 10))

    model_bundle, engine, _err = get_pain_area_model()

    if engine != "hf" or model_bundle is None:
        return predict_pain_area_heuristic(text, top_k=top_k)

    torch, device, tokenizer, model = model_bundle
    with torch.inference_mode():
        inputs = tokenizer(
            text or "",
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        logits = model(**inputs).logits  # (1, num_labels)
        probs = torch.softmax(logits, dim=-1).squeeze(0)  # (num_labels,)

        # label mapping
        id2label = model.config.id2label or {}
        # top-k
        values, indices = torch.topk(probs, k=min(top_k, probs.shape[0]))
        candidates: List[PainAreaCandidate] = []
        for v, i in zip(values.tolist(), indices.tolist()):
            label = id2label.get(int(i), str(int(i)))
            candidates.append(PainAreaCandidate(label=label, score=float(v)))

        predicted = candidates[0].label if candidates else "허리"
        return PainAreaPrediction(predicted_label=predicted, engine="hf", candidates=candidates)