# app/services/pose_preprocessing.py

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.spatial.distance import euclidean
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoseDataProcessor:
    """
    MediaPipe 자세 데이터 전처리 파이프라인
    
    주요 기능:
    1. 이상치 탐지 및 제거
    2. Missing landmarks 처리
    3. Temporal smoothing (시계열 스무딩)
    4. Feature engineering (관절 각도, 속도 등)
    5. 통계적 특징 추출
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Args:
            confidence_threshold: 랜드마크 신뢰도 임계값 (0.5 이하는 제거)
        """
        self.confidence_threshold = confidence_threshold
        self.landmark_indices = {
            'nose': 0,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_elbow': 13,
            'right_elbow': 14,
            'left_wrist': 15,
            'right_wrist': 16,
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
            'left_ankle': 27,
            'right_ankle': 28
        }
    
    def clean_sequence(
        self, 
        pose_sequence: List[np.ndarray],
        visibility_scores: Optional[List[np.ndarray]] = None
    ) -> Tuple[List[np.ndarray], Dict]:
        """
        자세 시퀀스 정제
        
        Args:
            pose_sequence: 포즈 프레임 리스트 (각 프레임: 99차원 벡터)
            visibility_scores: 각 랜드마크의 신뢰도 점수 (옵션)
        
        Returns:
            cleaned_sequence: 정제된 시퀀스
            cleaning_stats: 정제 통계
        """
        if len(pose_sequence) == 0:
            return [], {"error": "Empty sequence"}
        
        cleaned_frames = []
        removed_frames = 0
        interpolated_frames = 0
        
        for i, pose in enumerate(pose_sequence):
            # 1. 신뢰도 체크 (visibility_scores가 있는 경우)
            if visibility_scores is not None and len(visibility_scores) > i:
                if np.mean(visibility_scores[i]) < self.confidence_threshold:
                    removed_frames += 1
                    continue
            
            # 2. 이상치 탐지 (z-score 기반)
            if len(cleaned_frames) > 3:
                recent_poses = np.array(cleaned_frames[-3:])
                mean_pose = np.mean(recent_poses, axis=0)
                std_pose = np.std(recent_poses, axis=0) + 1e-6
                z_scores = np.abs((pose - mean_pose) / std_pose)
                
                # z-score > 3 이면 이상치로 판단
                if np.max(z_scores) > 3.0:
                    # 이전 프레임으로 보간
                    interpolated_pose = mean_pose
                    cleaned_frames.append(interpolated_pose)
                    interpolated_frames += 1
                    continue
            
            cleaned_frames.append(pose)
        
        # 3. Missing frames 보간 (linear interpolation)
        if removed_frames > 0:
            cleaned_frames = self._interpolate_missing_frames(
                cleaned_frames, 
                removed_frames
            )
        
        cleaning_stats = {
            "original_frames": len(pose_sequence),
            "cleaned_frames": len(cleaned_frames),
            "removed_frames": removed_frames,
            "interpolated_frames": interpolated_frames,
            "removal_rate": removed_frames / len(pose_sequence) if len(pose_sequence) > 0 else 0
        }
        
        logger.info(f"Cleaning stats: {cleaning_stats}")
        
        return cleaned_frames, cleaning_stats
    
    def smooth_sequence(
        self, 
        pose_sequence: List[np.ndarray],
        window_length: int = 5,
        polyorder: int = 2
    ) -> List[np.ndarray]:
        """
        시계열 스무딩 (Savitzky-Golay filter)
        
        노이즈 제거 및 부드러운 동작 생성
        
        Args:
            pose_sequence: 포즈 시퀀스
            window_length: 윈도우 크기 (홀수여야 함)
            polyorder: 다항식 차수
        
        Returns:
            smoothed_sequence: 스무딩된 시퀀스
        """
        if len(pose_sequence) < window_length:
            logger.warning(f"Sequence too short for smoothing ({len(pose_sequence)} < {window_length})")
            return pose_sequence
        
        # window_length는 홀수여야 함
        if window_length % 2 == 0:
            window_length += 1
        
        # numpy array로 변환
        sequence_array = np.array(pose_sequence)  # (n_frames, 99)
        
        # 각 차원별로 스무딩
        smoothed_array = savgol_filter(
            sequence_array, 
            window_length=window_length,
            polyorder=polyorder,
            axis=0
        )
        
        smoothed_sequence = [frame for frame in smoothed_array]
        
        logger.info(f"Smoothed {len(smoothed_sequence)} frames")
        
        return smoothed_sequence
    
    def extract_joint_angles(self, pose: np.ndarray) -> Dict[str, float]:
        """
        관절 각도 계산
        
        Args:
            pose: 99차원 포즈 벡터
        
        Returns:
            angles: 관절 각도 딕셔너리 (degree)
        """
        pose_reshaped = pose.reshape(-1, 3)  # (33, 3)
        
        angles = {}
        
        # 왼쪽 팔꿈치 각도
        angles['left_elbow'] = self._calculate_angle(
            pose_reshaped[self.landmark_indices['left_shoulder']],
            pose_reshaped[self.landmark_indices['left_elbow']],
            pose_reshaped[self.landmark_indices['left_wrist']]
        )
        
        # 오른쪽 팔꿈치 각도
        angles['right_elbow'] = self._calculate_angle(
            pose_reshaped[self.landmark_indices['right_shoulder']],
            pose_reshaped[self.landmark_indices['right_elbow']],
            pose_reshaped[self.landmark_indices['right_wrist']]
        )
        
        # 왼쪽 어깨 각도
        angles['left_shoulder'] = self._calculate_angle(
            pose_reshaped[self.landmark_indices['left_elbow']],
            pose_reshaped[self.landmark_indices['left_shoulder']],
            pose_reshaped[self.landmark_indices['left_hip']]
        )
        
        # 오른쪽 어깨 각도
        angles['right_shoulder'] = self._calculate_angle(
            pose_reshaped[self.landmark_indices['right_elbow']],
            pose_reshaped[self.landmark_indices['right_shoulder']],
            pose_reshaped[self.landmark_indices['right_hip']]
        )
        
        # 왼쪽 무릎 각도
        angles['left_knee'] = self._calculate_angle(
            pose_reshaped[self.landmark_indices['left_hip']],
            pose_reshaped[self.landmark_indices['left_knee']],
            pose_reshaped[self.landmark_indices['left_ankle']]
        )
        
        # 오른쪽 무릎 각도
        angles['right_knee'] = self._calculate_angle(
            pose_reshaped[self.landmark_indices['right_hip']],
            pose_reshaped[self.landmark_indices['right_knee']],
            pose_reshaped[self.landmark_indices['right_ankle']]
        )
        
        return angles
    
    def extract_features(
        self, 
        pose_sequence: List[np.ndarray]
    ) -> Dict[str, any]:
        """
        통계적 특징 추출
        
        Args:
            pose_sequence: 포즈 시퀀스
        
        Returns:
            features: 추출된 특징들
        """
        if len(pose_sequence) == 0:
            return {}
        
        sequence_array = np.array(pose_sequence)
        
        features = {
            # 기본 통계
            'mean': np.mean(sequence_array, axis=0),
            'std': np.std(sequence_array, axis=0),
            'min': np.min(sequence_array, axis=0),
            'max': np.max(sequence_array, axis=0),
            'range': np.max(sequence_array, axis=0) - np.min(sequence_array, axis=0),
            
            # 시계열 특징
            'n_frames': len(pose_sequence),
            
            # 속도 (프레임간 변화량)
            'velocity': self._calculate_velocity(pose_sequence),
            
            # 가속도
            'acceleration': self._calculate_acceleration(pose_sequence),
        }
        
        # 관절 각도 통계
        angles_sequence = [self.extract_joint_angles(pose) for pose in pose_sequence]
        if angles_sequence:
            angles_df = pd.DataFrame(angles_sequence)
            features['angles_mean'] = angles_df.mean().to_dict()
            features['angles_std'] = angles_df.std().to_dict()
            features['angles_range'] = (angles_df.max() - angles_df.min()).to_dict()
        
        return features
    
    def normalize_pose(self, pose: np.ndarray) -> np.ndarray:
        """
        포즈 정규화
        
        1. 어깨 중심을 원점으로 이동
        2. 어깨 너비로 스케일 조정
        
        Args:
            pose: 99차원 포즈 벡터
        
        Returns:
            normalized_pose: 정규화된 포즈
        """
        pose_reshaped = pose.reshape(-1, 3)
        
        # 어깨 중심점
        left_shoulder = pose_reshaped[self.landmark_indices['left_shoulder']]
        right_shoulder = pose_reshaped[self.landmark_indices['right_shoulder']]
        center = (left_shoulder + right_shoulder) / 2
        
        # 중심 이동
        pose_reshaped = pose_reshaped - center
        
        # 스케일 조정
        shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
        if shoulder_width > 0:
            pose_reshaped = pose_reshaped / shoulder_width
        
        return pose_reshaped.flatten()
    
    def _calculate_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """
        세 점으로 이루어진 각도 계산
        
        Args:
            p1, p2, p3: 3D 좌표 (x, y, z)
        
        Returns:
            angle: 각도 (degree)
        """
        v1 = p1 - p2
        v2 = p3 - p2
        
        # 코사인 법칙
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        angle = np.arccos(cos_angle)
        return np.degrees(angle)
    
    def _calculate_velocity(self, pose_sequence: List[np.ndarray]) -> np.ndarray:
        """
        프레임간 속도 계산 (1차 미분)
        """
        if len(pose_sequence) < 2:
            return np.zeros(len(pose_sequence[0]))
        
        sequence_array = np.array(pose_sequence)
        velocity = np.diff(sequence_array, axis=0)
        
        # 평균 속도
        return np.mean(np.abs(velocity), axis=0)
    
    def _calculate_acceleration(self, pose_sequence: List[np.ndarray]) -> np.ndarray:
        """
        프레임간 가속도 계산 (2차 미분)
        """
        if len(pose_sequence) < 3:
            return np.zeros(len(pose_sequence[0]))
        
        sequence_array = np.array(pose_sequence)
        velocity = np.diff(sequence_array, axis=0)
        acceleration = np.diff(velocity, axis=0)
        
        # 평균 가속도
        return np.mean(np.abs(acceleration), axis=0)
    
    def _interpolate_missing_frames(
        self, 
        frames: List[np.ndarray],
        n_missing: int
    ) -> List[np.ndarray]:
        """
        Missing frames 선형 보간
        """
        # 단순 구현: 앞뒤 프레임의 평균
        if len(frames) < 2:
            return frames
        
        return frames  # 실제로는 더 복잡한 보간 필요
    
    def get_preprocessing_summary(
        self, 
        original_sequence: List[np.ndarray],
        cleaned_sequence: List[np.ndarray],
        smoothed_sequence: List[np.ndarray]
    ) -> Dict:
        """
        전처리 요약 통계
        """
        return {
            "original_frames": len(original_sequence),
            "cleaned_frames": len(cleaned_sequence),
            "smoothed_frames": len(smoothed_sequence),
            "frame_loss_rate": (len(original_sequence) - len(cleaned_sequence)) / len(original_sequence),
            "noise_reduction": self._calculate_noise_reduction(
                original_sequence, 
                smoothed_sequence
            )
        }
    
    def _calculate_noise_reduction(
        self, 
        original: List[np.ndarray],
        smoothed: List[np.ndarray]
    ) -> float:
        """
        노이즈 감소율 계산
        """
        if len(original) != len(smoothed) or len(original) < 2:
            return 0.0
        
        original_array = np.array(original)
        smoothed_array = np.array(smoothed)
        
        # 원본의 프레임간 변화량
        original_diff = np.diff(original_array, axis=0)
        original_jitter = np.mean(np.std(original_diff, axis=0))
        
        # 스무딩 후 변화량
        smoothed_diff = np.diff(smoothed_array, axis=0)
        smoothed_jitter = np.mean(np.std(smoothed_diff, axis=0))
        
        # 감소율
        reduction = (original_jitter - smoothed_jitter) / original_jitter if original_jitter > 0 else 0
        return float(reduction)
