from __future__ import annotations

from dataclasses import dataclass

import numpy as np


FEATURE_NAMES = [
    "right_elbow_angle",
    "right_wrist_extension",
    "right_palm_opening",
    "right_wrist_x",
    "right_wrist_y",
    "right_hand_span",
]

FEATURE_LABELS = {
    "right_elbow_angle": "오른쪽 팔꿈치",
    "right_wrist_extension": "오른쪽 손목",
    "right_palm_opening": "오른쪽 손바닥",
    "right_wrist_x": "오른쪽 손목 위치(X)",
    "right_wrist_y": "오른쪽 손목 위치(Y)",
    "right_hand_span": "오른쪽 손 펼침",
}

# Each feature is normalized by a meaningful difference before DTW cost is
# calculated. Angular features are degrees; positional features are normalized
# image coordinates.
FEATURE_SCALES = np.array([45.0, 35.0, 35.0, 0.22, 0.22, 0.20], dtype=float)


@dataclass
class ComparisonResult:
    similarity: float
    distance: float
    speed_ratio: float
    path: list[tuple[int, int]]
    worst_segments: list[dict]
    metrics: dict


def _frame_cost(a: np.ndarray, b: np.ndarray) -> float:
    normalized = np.abs(a - b) / FEATURE_SCALES
    return float(np.mean(np.clip(normalized, 0.0, 2.0)))


def _warping_path(user: np.ndarray, reference: np.ndarray) -> tuple[float, list[tuple[int, int]]]:
    n, m = len(user), len(reference)
    if n == 0 or m == 0:
        raise ValueError("Both pose sequences must contain at least one frame.")

    matrix = np.full((n + 1, m + 1), np.inf, dtype=float)
    matrix[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            matrix[i, j] = _frame_cost(user[i - 1], reference[j - 1]) + min(
                matrix[i - 1, j],
                matrix[i, j - 1],
                matrix[i - 1, j - 1],
            )

    i, j = n, m
    path: list[tuple[int, int]] = []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        options = (
            (matrix[i - 1, j - 1], i - 1, j - 1),
            (matrix[i - 1, j], i - 1, j),
            (matrix[i, j - 1], i, j - 1),
        )
        _, i, j = min(options, key=lambda item: item[0])
    path.reverse()
    return float(matrix[n, m] / max(len(path), 1)), path


def _build_worst_segments(
    user: np.ndarray,
    reference: np.ndarray,
    path: list[tuple[int, int]],
    limit: int = 3,
) -> list[dict]:
    candidates: list[dict] = []
    user_last = max(len(user) - 1, 1)

    for user_idx, ref_idx in path:
        raw_diff = np.abs(user[user_idx] - reference[ref_idx])
        normalized = raw_diff / FEATURE_SCALES
        feature_idx = int(np.argmax(normalized))
        candidates.append(
            {
                "user_frame": user_idx,
                "reference_frame": ref_idx,
                "start_percent": int(round(user_idx / user_last * 100)),
                "end_percent": min(100, int(round(user_idx / user_last * 100)) + 5),
                "joint": FEATURE_NAMES[feature_idx],
                "joint_label": FEATURE_LABELS[FEATURE_NAMES[feature_idx]],
                "difference": round(float(raw_diff[feature_idx]), 2),
                "unit": "deg" if feature_idx < 3 else "normalized",
                "normalized_error": round(float(normalized[feature_idx]), 3),
            }
        )

    # Avoid showing the same joint and near-identical time point repeatedly.
    candidates.sort(key=lambda item: item["normalized_error"], reverse=True)
    selected: list[dict] = []
    for candidate in candidates:
        duplicate = any(
            item["joint"] == candidate["joint"]
            and abs(item["start_percent"] - candidate["start_percent"]) < 10
            for item in selected
        )
        if not duplicate:
            selected.append(candidate)
        if len(selected) == limit:
            break
    return selected


def compare_sequences(user_sequence: list[list[float]], reference_sequence: list[list[float]]) -> ComparisonResult:
    user = np.asarray(user_sequence, dtype=float)
    reference = np.asarray(reference_sequence, dtype=float)

    if user.ndim != 2 or reference.ndim != 2:
        raise ValueError("Pose sequences must be two-dimensional.")
    if user.shape[1] != len(FEATURE_NAMES) or reference.shape[1] != len(FEATURE_NAMES):
        raise ValueError(f"Each frame must contain {len(FEATURE_NAMES)} features.")

    distance, path = _warping_path(user, reference)
    similarity = float(np.clip(np.exp(-1.45 * distance) * 100.0, 0.0, 100.0))
    worst = _build_worst_segments(user, reference, path)

    aligned_errors = [_frame_cost(user[i], reference[j]) for i, j in path]
    metrics = {
        "user_frames": len(user),
        "reference_frames": len(reference),
        "aligned_pairs": len(path),
        "mean_aligned_error": round(float(np.mean(aligned_errors)), 4),
        "p95_aligned_error": round(float(np.percentile(aligned_errors, 95)), 4),
        "feature_names": FEATURE_NAMES,
    }

    return ComparisonResult(
        similarity=round(similarity, 2),
        distance=round(distance, 5),
        speed_ratio=round(len(user) / len(reference), 3),
        path=path,
        worst_segments=worst,
        metrics=metrics,
    )

