from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .dtw import FEATURE_NAMES


@dataclass
class VideoPoseResult:
    sequence: list[list[float]]
    data_quality: float
    metrics: dict


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    first = a - b
    second = c - b
    denom = np.linalg.norm(first) * np.linalg.norm(second)
    if denom < 1e-8:
        return 0.0
    cosine = np.clip(np.dot(first, second) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def _point(landmark) -> np.ndarray:
    return np.array([landmark.x, landmark.y, landmark.z], dtype=float)


def extract_right_wrist_features(video_path: str | Path, sample_rate: int = 3) -> VideoPoseResult:
    """
    Extract Pose + Hands features. Imports are lazy so demo mode runs without
    native vision packages. Raw video is never persisted by this function.
    """
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError(
            "Vision dependencies are unavailable. Install requirements-vision.txt "
            "or use the deterministic demo endpoint."
        ) from exc

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("업로드한 영상을 열 수 없습니다.")

    sequence: list[list[float]] = []
    quality_values: list[float] = []
    sampled_frames = 0
    detected_frames = 0

    holistic_module = mp.solutions.holistic
    pose_index = mp.solutions.pose.PoseLandmark
    with holistic_module.Holistic(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.55,
        min_tracking_confidence=0.55,
    ) as holistic:
        frame_idx = 0
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % max(sample_rate, 1) != 0:
                frame_idx += 1
                continue

            sampled_frames += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = holistic.process(rgb)
            frame_idx += 1

            if not result.pose_landmarks or not result.right_hand_landmarks:
                continue

            pose = result.pose_landmarks.landmark
            hand = result.right_hand_landmarks.landmark
            shoulder = _point(pose[pose_index.RIGHT_SHOULDER.value])
            elbow = _point(pose[pose_index.RIGHT_ELBOW.value])
            wrist = _point(pose[pose_index.RIGHT_WRIST.value])
            middle_mcp = _point(hand[9])
            index_mcp = _point(hand[5])
            pinky_mcp = _point(hand[17])

            elbow_angle = _angle(shoulder, elbow, wrist)
            wrist_extension = _angle(elbow, wrist, middle_mcp)
            palm_opening = _angle(index_mcp, _point(hand[0]), pinky_mcp)
            hand_span = float(np.linalg.norm(index_mcp - pinky_mcp))

            visibility = np.mean(
                [
                    pose[pose_index.RIGHT_SHOULDER.value].visibility,
                    pose[pose_index.RIGHT_ELBOW.value].visibility,
                    pose[pose_index.RIGHT_WRIST.value].visibility,
                ]
            )
            quality_values.append(float(visibility))
            sequence.append(
                [
                    elbow_angle,
                    wrist_extension,
                    palm_opening,
                    float(wrist[0]),
                    float(wrist[1]),
                    hand_span,
                ]
            )
            detected_frames += 1

    cap.release()
    detection_rate = detected_frames / sampled_frames if sampled_frames else 0.0
    visibility_quality = float(np.mean(quality_values)) if quality_values else 0.0
    data_quality = round(0.55 * detection_rate + 0.45 * visibility_quality, 3)

    if len(sequence) < 8:
        raise ValueError(
            "손과 팔이 함께 감지된 프레임이 부족합니다. 밝은 곳에서 오른손·팔꿈치·어깨가 "
            "한 화면에 보이도록 다시 촬영해 주세요."
        )

    return VideoPoseResult(
        sequence=sequence,
        data_quality=data_quality,
        metrics={
            "sampled_frames": sampled_frames,
            "detected_frames": detected_frames,
            "detection_rate": round(detection_rate, 3),
            "visibility_quality": round(visibility_quality, 3),
            "feature_names": FEATURE_NAMES,
        },
    )

