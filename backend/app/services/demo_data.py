from __future__ import annotations

import math

from .dtw import FEATURE_NAMES


def reference_wrist_sequence(frames: int = 42) -> list[list[float]]:
    """Deterministic synthetic expert motion used only by demo mode."""
    sequence: list[list[float]] = []
    for idx in range(frames):
        phase = idx / max(frames - 1, 1)
        wave = math.sin(phase * math.pi)
        sequence.append(
            [
                154.0 - 7.0 * wave,
                166.0 - 58.0 * wave,
                76.0 + 9.0 * wave,
                0.66 + 0.025 * wave,
                0.48 - 0.035 * wave,
                0.18 + 0.025 * wave,
            ]
        )
    return sequence


def user_wrist_sequence(frames: int = 49) -> list[list[float]]:
    """A repeatable user attempt with timing and wrist-angle deviations."""
    sequence: list[list[float]] = []
    for idx in range(frames):
        phase = idx / max(frames - 1, 1)
        wave = math.sin(phase * math.pi)
        local_error = 1.0 if 0.38 <= phase <= 0.62 else 0.25
        sequence.append(
            [
                151.0 - 4.5 * wave,
                164.0 - 42.0 * wave + 14.0 * local_error,
                73.0 + 6.0 * wave,
                0.65 + 0.019 * wave,
                0.49 - 0.021 * wave,
                0.16 + 0.018 * wave,
            ]
        )
    return sequence


def demo_reference_payload() -> dict:
    return {
        "id": "wrist_extension_demo",
        "name": "손목 신전 스트레칭",
        "body_part": "손목",
        "description": "팔을 편 상태에서 손목을 천천히 굽혀 전완부를 늘리는 동작입니다.",
        "version": "demo-1.0",
        "sequence": reference_wrist_sequence(),
        "feature_names": FEATURE_NAMES,
        "source_type": "synthetic_demo",
        "approved": False,
    }

