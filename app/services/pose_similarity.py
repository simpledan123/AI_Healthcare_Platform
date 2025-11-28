# app/services/pose_similarity.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import json

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


class PoseSimilarityAnalyzer:
    """
    참조 영상과 사용자 동작의 유사도 비교 시스템
    
    핵심 아이디어:
    1. 참조 영상(reference video)의 포즈 시퀀스 추출
    2. 사용자 웹캠 영상의 포즈 시퀀스 추출
    3. DTW(Dynamic Time Warping)로 시간 정렬 후 유사도 계산
    """
    
    def __init__(self):
        self.pose_detector = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def extract_pose_landmarks(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        프레임에서 포즈 랜드마크 추출
        
        Returns:
            33개 랜드마크 × 3차원(x, y, z) = 99차원 벡터
            None if 포즈 감지 실패
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose_detector.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None
        
        # 랜드마크를 numpy 배열로 변환
        landmarks = []
        for landmark in results.pose_landmarks.landmark:
            landmarks.extend([landmark.x, landmark.y, landmark.z])
        
        return np.array(landmarks)
    
    def extract_video_pose_sequence(
        self, 
        video_path: str,
        sample_rate: int = 5
    ) -> List[np.ndarray]:
        """
        영상에서 포즈 시퀀스 추출
        
        Args:
            video_path: 영상 파일 경로
            sample_rate: N프레임마다 샘플링 (5 = 매 5프레임)
        
        Returns:
            포즈 벡터 리스트
        """
        cap = cv2.VideoCapture(video_path)
        pose_sequence = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 샘플링 (모든 프레임 분석하면 너무 느림)
            if frame_count % sample_rate == 0:
                pose = self.extract_pose_landmarks(frame)
                if pose is not None:
                    pose_sequence.append(pose)
            
            frame_count += 1
        
        cap.release()
        return pose_sequence
    
    def normalize_pose(self, pose: np.ndarray) -> np.ndarray:
        """
        포즈 정규화 (크기, 위치 불변성)
        
        - 어깨 중심을 원점으로 이동
        - 어깨 너비로 스케일 조정
        """
        pose_reshaped = pose.reshape(-1, 3)
        
        # 어깨 중심점 (left shoulder: 11, right shoulder: 12)
        left_shoulder = pose_reshaped[11]
        right_shoulder = pose_reshaped[12]
        center = (left_shoulder + right_shoulder) / 2
        
        # 중심 이동
        pose_reshaped = pose_reshaped - center
        
        # 어깨 너비로 스케일 조정
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
        두 포즈 간 유사도 계산
        
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
        
        # 0~1 범위로 조정 (-1~1 → 0~1)
        similarity = (similarity + 1) / 2
        
        return float(similarity)
    
    def dtw_distance(
        self,
        sequence1: List[np.ndarray],
        sequence2: List[np.ndarray]
    ) -> float:
        """
        Dynamic Time Warping으로 시퀀스 간 거리 계산
        
        서로 다른 속도로 수행된 동작을 비교할 때 유용
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
        reference_sequence: List[np.ndarray]
    ) -> Dict:
        """
        사용자 동작과 참조 영상 비교
        
        Returns:
            유사도 점수 및 상세 피드백
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
        
        # 프레임별 유사도 계산 (피드백용)
        frame_similarities = []
        min_length = min(len(user_sequence), len(reference_sequence))
        
        for i in range(min_length):
            sim = self.calculate_pose_similarity(
                user_sequence[i],
                reference_sequence[i]
            )
            frame_similarities.append(sim)
        
        # 가장 유사도가 낮은 구간 찾기 (개선 필요 부분)
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
        
        return {
            "success": True,
            "overall_similarity": similarity_score,
            "dtw_distance": dtw_dist,
            "frame_similarities": frame_similarities,
            "worst_frame_index": worst_frame_idx,
            "feedback": feedback,
            "speed_ratio": len(user_sequence) / len(reference_sequence)
        }
    
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


# ============================================
# 참조 영상 데이터베이스 (추후 실제 데이터로 교체)
# ============================================

class ReferenceVideoDatabase:
    """
    참조 영상 관리 시스템
    
    추후 실제 헬스케어 데이터로 교체 예정:
    - 전문 물리치료사 시연 영상
    - 다양한 각도의 시점
    - 난이도별 분류
    """
    
    def __init__(self):
        # 현재는 플레이스홀더
        # 추후 S3, DB 등에서 불러옴
        self.reference_videos = {
            "wrist_stretch_1": {
                "title": "손목 신전 스트레칭",
                "difficulty": "초급",
                "duration_seconds": 30,
                "video_url": "placeholder_for_future_data",  # 추후 실제 데이터
                "pose_sequence_path": None,  # 미리 추출된 포즈 데이터 경로
                "description": "손목을 앞으로 뻗고 반대 손으로 당기는 동작"
            },
            "shoulder_stretch_1": {
                "title": "어깨 회전 스트레칭",
                "difficulty": "초급",
                "duration_seconds": 45,
                "video_url": "placeholder_for_future_data",
                "pose_sequence_path": None,
                "description": "양팔을 옆으로 벌려 원을 그리는 동작"
            },
            # 추후 수백 개의 운동 영상 추가
        }
    
    def get_reference_video(self, exercise_id: str) -> Optional[Dict]:
        """참조 영상 정보 가져오기"""
        return self.reference_videos.get(exercise_id)
    
    def list_exercises_by_area(self, pain_area: str) -> List[Dict]:
        """부위별 운동 목록"""
        # 추후 DB 쿼리로 교체
        area_mapping = {
            "손목": ["wrist_stretch_1"],
            "어깨": ["shoulder_stretch_1"],
            # ...
        }
        
        exercise_ids = area_mapping.get(pain_area, [])
        return [
            {
                "id": ex_id,
                **self.reference_videos[ex_id]
            }
            for ex_id in exercise_ids
        ]
    
    def precompute_reference_poses(self, video_path: str, exercise_id: str):
        """
        참조 영상의 포즈 시퀀스를 미리 계산하여 저장
        (실시간 비교 시 매번 계산하지 않도록)
        """
        analyzer = PoseSimilarityAnalyzer()
        pose_sequence = analyzer.extract_video_pose_sequence(video_path)
        
        # JSON 또는 pickle로 저장
        output_path = f"data/reference_poses/{exercise_id}.json"
        
        # numpy array를 list로 변환 (JSON 직렬화용)
        serializable_sequence = [pose.tolist() for pose in pose_sequence]
        
        with open(output_path, 'w') as f:
            json.dump(serializable_sequence, f)
        
        print(f"✅ {exercise_id} 참조 포즈 저장 완료: {len(pose_sequence)} 프레임")
        
        return output_path
