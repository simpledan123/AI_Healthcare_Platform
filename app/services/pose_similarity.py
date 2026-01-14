# app/services/pose_similarity.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import json
import logging

# 전처리 파이프라인 import
from .pose_preprocessing import PoseDataProcessor

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoseSimilarityAnalyzer:
    """
    참조 영상과 사용자 동작의 유사도 비교 시스템 (전처리 강화 버전)
    
    핵심 기능:
    1. MediaPipe로 포즈 추출
    2. 데이터 전처리 (이상치 제거, 스무딩)
    3. DTW로 시간 정렬
    4. 코사인 유사도 계산
    """
    
    def __init__(self, enable_preprocessing: bool = True):
        """
        Args:
            enable_preprocessing: 전처리 파이프라인 활성화 여부
        """
        self.pose_detector = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 전처리 파이프라인
        self.enable_preprocessing = enable_preprocessing
        if enable_preprocessing:
            self.preprocessor = PoseDataProcessor(confidence_threshold=0.5)
            logger.info("Preprocessing pipeline enabled")
        else:
            self.preprocessor = None
            logger.info("Preprocessing pipeline disabled")
    
    def extract_pose_landmarks(
        self, 
        frame: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        프레임에서 포즈 랜드마크 추출
        
        Returns:
            landmarks: 33개 랜드마크 × 3차원 = 99차원 벡터
            visibility_scores: 각 랜드마크의 신뢰도 점수
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose_detector.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None, None
        
        # 랜드마크를 numpy 배열로 변환
        landmarks = []
        visibility_scores = []
        
        for landmark in results.pose_landmarks.landmark:
            landmarks.extend([landmark.x, landmark.y, landmark.z])
            visibility_scores.append(landmark.visibility)
        
        return np.array(landmarks), np.array(visibility_scores)
    
    def extract_video_pose_sequence(
        self, 
        video_path: str,
        sample_rate: int = 5,
        apply_preprocessing: bool = True
    ) -> Dict:
        """
        영상에서 포즈 시퀀스 추출 (전처리 포함)
        
        Args:
            video_path: 영상 파일 경로
            sample_rate: N프레임마다 샘플링
            apply_preprocessing: 전처리 적용 여부
        
        Returns:
            결과 딕셔너리 (원본, 정제, 스무딩 시퀀스 포함)
        """
        cap = cv2.VideoCapture(video_path)
        
        raw_sequence = []
        visibility_sequence = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 샘플링
            if frame_count % sample_rate == 0:
                pose, visibility = self.extract_pose_landmarks(frame)
                if pose is not None:
                    raw_sequence.append(pose)
                    visibility_sequence.append(visibility)
            
            frame_count += 1
        
        cap.release()
        
        logger.info(f"Extracted {len(raw_sequence)} raw frames from {frame_count} total frames")
        
        # 전처리 적용
        result = {
            "raw_sequence": raw_sequence,
            "n_raw_frames": len(raw_sequence)
        }
        
        if apply_preprocessing and self.preprocessor and len(raw_sequence) > 0:
            # 1. 정제 (이상치 제거)
            cleaned_sequence, cleaning_stats = self.preprocessor.clean_sequence(
                raw_sequence,
                visibility_sequence
            )
            
            # 2. 스무딩
            smoothed_sequence = self.preprocessor.smooth_sequence(
                cleaned_sequence,
                window_length=5,
                polyorder=2
            )
            
            # 3. 정규화
            normalized_sequence = [
                self.preprocessor.normalize_pose(pose) 
                for pose in smoothed_sequence
            ]
            
            # 4. 특징 추출
            features = self.preprocessor.extract_features(normalized_sequence)
            
            result.update({
                "cleaned_sequence": cleaned_sequence,
                "smoothed_sequence": smoothed_sequence,
                "normalized_sequence": normalized_sequence,
                "n_cleaned_frames": len(cleaned_sequence),
                "n_smoothed_frames": len(smoothed_sequence),
                "cleaning_stats": cleaning_stats,
                "features": {
                    "n_frames": features.get("n_frames", 0),
                    "angles_mean": features.get("angles_mean", {}),
                    "angles_std": features.get("angles_std", {}),
                }
            })
            
            logger.info(f"Preprocessing complete: {cleaning_stats}")
        else:
            # 전처리 없이 정규화만
            result["normalized_sequence"] = [
                self.normalize_pose(pose) for pose in raw_sequence
            ]
        
        return result
    
    def normalize_pose(self, pose: np.ndarray) -> np.ndarray:
        """
        포즈 정규화 (전처리 파이프라인 사용 또는 기본 정규화)
        """
        if self.preprocessor:
            return self.preprocessor.normalize_pose(pose)
        
        # 기본 정규화
        pose_reshaped = pose.reshape(-1, 3)
        left_shoulder = pose_reshaped[11]
        right_shoulder = pose_reshaped[12]
        center = (left_shoulder + right_shoulder) / 2
        pose_reshaped = pose_reshaped - center
        shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
        if shoulder_width > 0:
            pose_reshaped = pose_reshaped / shoulder_width
        return pose_reshaped.flatten()
    
    def calculate_pose_similarity(
        self,
        pose1: np.ndarray,
        pose2: np.ndarray
    ) -> float:
        """
        두 포즈 간 유사도 계산 (코사인 유사도)
        
        Returns:
            0.0 ~ 1.0 (1.0 = 완전히 동일)
        """
        # 정규화
        pose1_norm = self.normalize_pose(pose1)
        pose2_norm = self.normalize_pose(pose2)
        
        # 코사인 유사도
        similarity = cosine_similarity(
            pose1_norm.reshape(1, -1),
            pose2_norm.reshape(1, -1)
        )[0][0]
        
        # 0~1 범위로 조정
        similarity = (similarity + 1) / 2
        
        return float(similarity)
    
    def dtw_distance(
        self,
        sequence1: List[np.ndarray],
        sequence2: List[np.ndarray]
    ) -> float:
        """
        Dynamic Time Warping으로 시퀀스 간 거리 계산
        """
        n, m = len(sequence1), len(sequence2)
        
        # DTW 매트릭스 초기화
        dtw_matrix = np.full((n + 1, m + 1), np.inf)
        dtw_matrix[0, 0] = 0
        
        # DTW 계산
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = 1 - self.calculate_pose_similarity(
                    sequence1[i - 1],
                    sequence2[j - 1]
                )
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i - 1, j],      # insertion
                    dtw_matrix[i, j - 1],      # deletion
                    dtw_matrix[i - 1, j - 1]   # match
                )
        
        # 정규화된 DTW 거리
        normalized_distance = dtw_matrix[n, m] / (n + m)
        
        return float(normalized_distance)
    
    def compare_with_reference(
        self,
        user_sequence: List[np.ndarray],
        reference_sequence: List[np.ndarray],
        include_preprocessing_stats: bool = True
    ) -> Dict:
        """
        사용자 동작과 참조 영상 비교
        
        Returns:
            유사도 점수, 상세 피드백, 전처리 통계
        """
        if len(user_sequence) == 0:
            return {
                "success": False,
                "message": "동작을 감지할 수 없습니다."
            }
        
        if len(reference_sequence) == 0:
            return {
                "success": False,
                "message": "참조 영상 데이터가 없습니다."
            }
        
        # DTW 거리 계산
        dtw_dist = self.dtw_distance(user_sequence, reference_sequence)
        
        # 유사도 점수 (0~100)
        similarity_score = int((1 - dtw_dist) * 100)
        similarity_score = max(0, min(100, similarity_score))
        
        # 프레임별 유사도 계산
        frame_similarities = []
        min_length = min(len(user_sequence), len(reference_sequence))
        
        for i in range(min_length):
            sim = self.calculate_pose_similarity(
                user_sequence[i],
                reference_sequence[i]
            )
            frame_similarities.append(sim)
        
        # 가장 유사도가 낮은 구간
        if frame_similarities:
            worst_frame_idx = np.argmin(frame_similarities)
            worst_similarity = frame_similarities[worst_frame_idx]
        else:
            worst_frame_idx = 0
            worst_similarity = 0
        
        # 피드백 생성
        feedback = self._generate_feedback(
            similarity_score,
            worst_frame_idx,
            worst_similarity,
            len(user_sequence),
            len(reference_sequence)
        )
        
        result = {
            "success": True,
            "overall_similarity": similarity_score,
            "dtw_distance": dtw_dist,
            "frame_similarities": frame_similarities,
            "worst_frame_index": worst_frame_idx,
            "feedback": feedback,
            "speed_ratio": len(user_sequence) / len(reference_sequence)
        }
        
        # 전처리 통계 추가
        if include_preprocessing_stats and self.preprocessor:
            result["preprocessing_enabled"] = True
        
        return result
    
    def _generate_feedback(
        self,
        similarity: int,
        worst_idx: int,
        worst_sim: float,
        user_frames: int,
        ref_frames: int
    ) -> List[str]:
        """유사도 기반 피드백 생성"""
        feedback = []
        
        # 전체 유사도 피드백
        if similarity >= 85:
            feedback.append("✅ 훌륭합니다! 참조 영상과 거의 동일하게 수행하고 있습니다.")
        elif similarity >= 70:
            feedback.append("👍 잘하고 있습니다! 조금만 더 정확하게 따라해보세요.")
        elif similarity >= 50:
            feedback.append("⚠️ 동작이 참조 영상과 다릅니다. 영상을 다시 확인해주세요.")
        else:
            feedback.append("❌ 동작이 많이 다릅니다. 영상을 천천히 보며 연습해보세요.")
        
        # 속도 피드백
        speed_ratio = user_frames / ref_frames if ref_frames > 0 else 1
        if speed_ratio > 1.3:
            feedback.append("🐌 동작이 너무 느립니다. 조금 더 빠르게 수행해보세요.")
        elif speed_ratio < 0.7:
            feedback.append("🏃 동작이 너무 빠릅니다. 천천히 정확하게 수행해보세요.")
        
        # 특정 구간 피드백
        if worst_sim < 0.6:
            time_point = int((worst_idx / user_frames) * 100) if user_frames > 0 else 0
            feedback.append(f"🎯 {time_point}% 지점에서 자세가 많이 틀렸습니다. 해당 부분을 집중적으로 연습하세요.")
        
        return feedback


class ReferenceVideoDatabase:
    """참조 영상 관리 시스템"""
    
    def __init__(self):
        self.reference_videos = {
            "wrist_stretch_1": {
                "title": "손목 신전 스트레칭",
                "difficulty": "초급",
                "duration_seconds": 30,
                "video_url": "placeholder_for_future_data",
                "pose_sequence_path": None,
                "description": "손목을 앞으로 뻗고 반대 손으로 당기는 동작"
            },
            "shoulder_stretch_1": {
                "title": "어깨 회전 스트레칭",
                "difficulty": "초급",
                "duration_seconds": 45,
                "video_url": "placeholder_for_future_data",
                "pose_sequence_path": None,
                "description": "양팔을 옆으로 벌려 원을 그리는 동작"
            }
        }
    
    def get_reference_video(self, exercise_id: str) -> Optional[Dict]:
        """참조 영상 정보 가져오기"""
        return self.reference_videos.get(exercise_id)
    
    def list_exercises_by_area(self, pain_area: str) -> List[Dict]:
        """부위별 운동 목록"""
        area_mapping = {
            "손목": ["wrist_stretch_1"],
            "어깨": ["shoulder_stretch_1"],
        }
        
        exercise_ids = area_mapping.get(pain_area, [])
        return [
            {
                "id": ex_id,
                **self.reference_videos[ex_id]
            }
            for ex_id in exercise_ids
        ]
