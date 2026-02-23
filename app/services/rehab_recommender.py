# app/services/rehab_recommender.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from app.services.rehabilitation_ai import RehabilitationAI
from app.services.hf_models.rehab_json_generator import (
    generate_local_rehab_recommendation,
    LocalRehabModelUnavailable,
    LocalRehabGenerationError,
)

# 환경변수:
# - REHAB_REC_ENGINE (default: claude)
#   - claude
#   - local
#   - claude_then_local
#   - local_then_claude


class RehabRecommendationEngineError(RuntimeError):
    pass


def _normalize_engine(engine: Optional[str]) -> str:
    e = (engine or os.getenv("REHAB_REC_ENGINE", "claude")).strip().lower()
    aliases = {
        "anthropic": "claude",
        "claude_only": "claude",
        "local_lora": "local",
        "lora": "local",
        "hf": "local",
        "claude_fallback_local": "claude_then_local",
        "local_fallback_claude": "local_then_claude",
    }
    return aliases.get(e, e)


def generate_rehab_recommendation(
    pain_area: str,
    pain_description: str,
    severity: int,
    engine: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Claude 기본 유지 + 로컬 LoRA는 옵션으로 붙이는 추천 생성 오케스트레이터.

    - 기본(default): REHAB_REC_ENGINE=claude  -> 기존 동작 100% 동일
    - local: 로컬 LoRA만 사용 (없으면 예외)
    - claude_then_local: Claude 시도 후 실패 시 local
    - local_then_claude: local 시도 후 실패 시 Claude
    """
    e = _normalize_engine(engine)

    # 1) claude only (default)
    if e == "claude":
        # RehabilitationAI 내부에서 실패 시 fallback 반환할 수도 있음
        return RehabilitationAI.generate_recommendation(
            pain_area=pain_area,
            pain_description=pain_description or "",
            severity=severity,
        )

    # 2) local only
    if e == "local":
        return generate_local_rehab_recommendation(
            pain_area=pain_area,
            pain_description=pain_description or "",
            severity=severity,
        )

    # 3) claude -> local
    if e == "claude_then_local":
        try:
            out = RehabilitationAI.generate_recommendation(
                pain_area=pain_area,
                pain_description=pain_description or "",
                severity=severity,
            )
            # out이 비정상 형태면 local로 떨어뜨리고 싶으면 여기서 검사 가능
            return out
        except Exception:
            # claude가 예외를 던지는 케이스만 local fallback
            return generate_local_rehab_recommendation(
                pain_area=pain_area,
                pain_description=pain_description or "",
                severity=severity,
            )

    # 4) local -> claude
    if e == "local_then_claude":
        try:
            return generate_local_rehab_recommendation(
                pain_area=pain_area,
                pain_description=pain_description or "",
                severity=severity,
            )
        except (LocalRehabModelUnavailable, LocalRehabGenerationError, Exception):
            return RehabilitationAI.generate_recommendation(
                pain_area=pain_area,
                pain_description=pain_description or "",
                severity=severity,
            )

    # unknown -> safe default
    return RehabilitationAI.generate_recommendation(
        pain_area=pain_area,
        pain_description=pain_description or "",
        severity=severity,
    )