from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

from anthropic import Anthropic
from pydantic import ValidationError

from ..config import Settings
from ..schemas import AIReviewPayload, Correction


PROMPT_VERSION = "pose-review-v1.0"
RED_FLAG_WORDS = ("마비", "감각이 없", "심한 부종", "골절", "출혈", "극심한 통증")


@dataclass
class ReviewResult:
    payload: AIReviewPayload
    provider: str
    model: str
    validation_status: str
    latency_ms: int
    fallback_used: bool
    input_snapshot: dict
    output_snapshot: dict


def _segment_evidence(segment: dict) -> str:
    unit = "도" if segment["unit"] == "deg" else "정규화 좌표"
    return (
        f"{segment['start_percent']}~{segment['end_percent']}% 구간, "
        f"{segment['joint']} 차이 {segment['difference']} {unit}"
    )


def deterministic_review(snapshot: dict) -> AIReviewPayload:
    similarity = float(snapshot["overall_similarity"])
    quality = float(snapshot["data_quality"])
    severity = int(snapshot["severity"])
    description = str(snapshot.get("pain_description") or "")
    safety_flags = [word for word in RED_FLAG_WORDS if word in description]

    if severity >= 8:
        safety_flags.append("높은 통증 강도")

    requires_review = quality < 0.62 or bool(safety_flags)
    if requires_review:
        verdict = "REVIEW"
        summary = "분석 신뢰도 또는 안전 조건을 확인하기 전에는 동작 교정을 확정하지 않습니다."
    elif similarity >= 86:
        verdict = "PASS"
        summary = "전문가 기준 동작과 높은 유사도를 보였습니다."
    else:
        verdict = "RETRY"
        summary = "측정 근거가 가장 큰 구간부터 자세를 조정한 뒤 다시 비교해 보세요."

    corrections: list[Correction] = []
    for segment in snapshot.get("worst_segments", [])[:3]:
        unit = "도" if segment["unit"] == "deg" else "만큼"
        corrections.append(
            Correction(
                segment=f"동작 {segment['start_percent']}~{segment['end_percent']}% 구간",
                joint=segment["joint"],
                feedback=(
                    f"{segment['joint_label']}의 기준 동작 차이가 {segment['difference']}{unit}입니다. "
                    "전문가 영상을 해당 구간에서 멈춰 확인하고 통증이 없는 범위에서 천천히 맞춰 보세요."
                ),
                evidence=_segment_evidence(segment),
            )
        )

    return AIReviewPayload(
        verdict=verdict,
        confidence=round(min(0.97, max(0.35, quality * 0.94)), 2),
        summary=summary,
        corrections=corrections,
        safety_flags=sorted(set(safety_flags)),
        requires_review=requires_review,
    )


def _extract_json(text: str) -> dict:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("AI response did not contain a JSON object.")
    return json.loads(match.group(0))


def _validate_evidence(payload: AIReviewPayload, snapshot: dict) -> None:
    allowed = {
        (item["joint"], item["start_percent"], item["end_percent"])
        for item in snapshot.get("worst_segments", [])
    }
    for correction in payload.corrections:
        matching = [
            item
            for item in snapshot.get("worst_segments", [])
            if item["joint"] == correction.joint
            and str(item["difference"]) in correction.evidence
        ]
        if not matching:
            raise ValueError(f"Correction lacks measured evidence: {correction.joint}")
        item = matching[0]
        if (item["joint"], item["start_percent"], item["end_percent"]) not in allowed:
            raise ValueError("Correction references an unknown segment.")


def _live_review(snapshot: dict, settings: Settings) -> AIReviewPayload:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required in live mode.")

    system = (
        "You review a wrist-rehabilitation motion comparison. Use only supplied measured evidence. "
        "Do not diagnose or prescribe treatment. Return one JSON object with keys verdict "
        "(PASS|RETRY|REVIEW), confidence (0..1), summary, corrections, safety_flags, "
        "requires_review. Each correction needs segment, joint, feedback, evidence. "
        "The evidence string must copy the measured joint and numeric difference."
    )
    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1200,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": json.dumps(snapshot, ensure_ascii=False)}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    payload = AIReviewPayload.model_validate(_extract_json(text))
    _validate_evidence(payload, snapshot)
    return payload


def review_pose(snapshot: dict, settings: Settings) -> ReviewResult:
    started = time.perf_counter()
    fallback_used = False

    if settings.ai_review_mode.lower() == "live":
        provider = "anthropic"
        model = settings.anthropic_model
        try:
            payload = _live_review(snapshot, settings)
            validation_status = "VALIDATED"
        except (RuntimeError, ValueError, ValidationError, json.JSONDecodeError):
            payload = deterministic_review(snapshot)
            provider = "policy-engine"
            model = "deterministic-fallback-v1"
            validation_status = "FALLBACK_VALIDATED"
            fallback_used = True
    else:
        payload = deterministic_review(snapshot)
        provider = "demo-policy-engine"
        model = "deterministic-review-v1"
        validation_status = "DEMO_VALIDATED"

    latency_ms = int((time.perf_counter() - started) * 1000)
    output = payload.model_dump(mode="json")
    return ReviewResult(
        payload=payload,
        provider=provider,
        model=model,
        validation_status=validation_status,
        latency_ms=latency_ms,
        fallback_used=fallback_used,
        input_snapshot=snapshot,
        output_snapshot=output,
    )

