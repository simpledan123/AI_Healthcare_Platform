# app/api/routers/pose_comparison.py

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from typing import Optional
import tempfile
import os

# ⭐ 수정: 상대 경로로 import
from ...services.pose_similarity import (
    PoseSimilarityAnalyzer,
    ReferenceVideoDatabase
)

router = APIRouter(
    prefix="/api/pose-comparison",
    tags=["Pose Comparison"]
)

# 전역 인스턴스
pose_analyzer = PoseSimilarityAnalyzer()
reference_db = ReferenceVideoDatabase()


@router.get("/exercises/{pain_area}")
async def get_exercises_for_area(pain_area: str):
    """
    특정 부위에 대한 참조 운동 목록
    
    추후 실제 헬스케어 데이터로 교체됨
    """
    exercises = reference_db.list_exercises_by_area(pain_area)
    
    if not exercises:
        return {
            "pain_area": pain_area,
            "exercises": [],
            "message": "해당 부위에 대한 참조 영상이 아직 준비되지 않았습니다.",
            "note": "실제 헬스케어 데이터를 사용하여 수백 개의 운동이 추가될 예정입니다."
        }
    
    return {
        "pain_area": pain_area,
        "exercises": exercises
    }


@router.post("/compare")
async def compare_user_with_reference(
    user_video: UploadFile = File(...),
    exercise_id: str = Form(...),
    sample_rate: int = Form(default=5)
):
    """
    사용자 웹캠 영상과 참조 영상 비교
    
    Args:
        user_video: 사용자가 웹캠으로 촬영한 운동 영상
        exercise_id: 비교할 참조 운동 ID
        sample_rate: 프레임 샘플링 비율 (5 = 5프레임마다)
    
    Returns:
        유사도 점수, 프레임별 분석, 피드백
    """
    
    # 참조 영상 정보 확인
    reference_info = reference_db.get_reference_video(exercise_id)
    if not reference_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"운동 ID '{exercise_id}'를 찾을 수 없습니다."
        )
    
    # 사용자 영상 임시 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        content = await user_video.read()
        tmp_file.write(content)
        user_video_path = tmp_file.name
    
    try:
        # 사용자 영상에서 포즈 시퀀스 추출
        user_sequence = pose_analyzer.extract_video_pose_sequence(
            user_video_path,
            sample_rate=sample_rate
        )
        
        if len(user_sequence) == 0:
            return {
                "success": False,
                "message": "사용자 영상에서 포즈를 감지할 수 없습니다. 전신이 보이도록 촬영해주세요."
            }
        
        # TODO: 참조 영상 포즈 시퀀스 로드
        # 현재는 플레이스홀더 (추후 실제 데이터 사용)
        reference_sequence = _load_reference_sequence(exercise_id)
        
        if reference_sequence is None:
            return {
                "success": False,
                "message": "참조 영상 데이터가 아직 준비되지 않았습니다.",
                "note": "추후 실제 헬스케어 전문가 시연 영상으로 업데이트될 예정입니다."
            }
        
        # 유사도 비교
        comparison_result = pose_analyzer.compare_with_reference(
            user_sequence,
            reference_sequence
        )
        
        return comparison_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비교 중 오류 발생: {str(e)}"
        )
    
    finally:
        # 임시 파일 삭제
        if os.path.exists(user_video_path):
            os.remove(user_video_path)


@router.post("/realtime-frame-check")
async def check_realtime_frame(
    frame: UploadFile = File(...),
    exercise_id: str = Form(...),
    frame_index: int = Form(...)
):
    """
    실시간 프레임 단위 체크
    
    웹캠에서 프레임을 캡처하여 실시간으로 참조 영상과 비교
    
    Args:
        frame: 웹캠 캡처 이미지
        exercise_id: 참조 운동 ID
        frame_index: 현재 프레임 인덱스 (참조 영상의 어느 시점과 비교할지)
    """
    
    # 참조 영상 정보
    reference_info = reference_db.get_reference_video(exercise_id)
    if not reference_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"운동 ID '{exercise_id}'를 찾을 수 없습니다."
        )
    
    try:
        # 프레임 읽기
        content = await frame.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("이미지를 읽을 수 없습니다.")
        
        # 사용자 프레임에서 포즈 추출
        user_pose = pose_analyzer.extract_pose_landmarks(img)
        
        if user_pose is None:
            return {
                "success": False,
                "message": "포즈를 감지할 수 없습니다."
            }
        
        # 참조 포즈 로드
        reference_sequence = _load_reference_sequence(exercise_id)
        
        if reference_sequence is None or frame_index >= len(reference_sequence):
            return {
                "success": False,
                "message": "참조 데이터를 사용할 수 없습니다."
            }
        
        reference_pose = reference_sequence[frame_index]
        
        # 유사도 계산
        similarity = pose_analyzer.calculate_pose_similarity(
            user_pose,
            reference_pose
        )
        
        # 점수화 (0~100)
        similarity_score = int(similarity * 100)
        
        # 실시간 피드백
        if similarity_score >= 85:
            feedback = "✅ 완벽합니다!"
            color = "green"
        elif similarity_score >= 70:
            feedback = "👍 좋습니다!"
            color = "yellow"
        elif similarity_score >= 50:
            feedback = "⚠️ 조금 더 정확하게"
            color = "orange"
        else:
            feedback = "❌ 자세를 다시 확인하세요"
            color = "red"
        
        return {
            "success": True,
            "similarity_score": similarity_score,
            "feedback": feedback,
            "color": color,
            "frame_index": frame_index
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프레임 체크 중 오류: {str(e)}"
        )


def _load_reference_sequence(exercise_id: str) -> Optional[list]:
    """
    참조 포즈 시퀀스 로드
    
    추후 실제 구현:
    - S3/Cloud Storage에서 다운로드
    - 캐싱으로 성능 최적화
    - 다양한 각도의 영상 지원
    """
    
    # 현재는 플레이스홀더
    # 실제로는 미리 계산된 포즈 데이터를 로드
    
    import json
    reference_path = f"data/reference_poses/{exercise_id}.json"
    
    if not os.path.exists(reference_path):
        # 아직 데이터가 없음 - 추후 실제 데이터로 교체
        return None
    
    with open(reference_path, 'r') as f:
        sequence_data = json.load(f)
    
    # list를 numpy array로 변환
    return [np.array(pose) for pose in sequence_data]


@router.get("/reference-video-status")
async def get_reference_video_status():
    """
    참조 영상 데이터베이스 현황
    
    개발 현황을 투명하게 공개
    """
    return {
        "status": "placeholder_phase",
        "message": "현재는 플레이스홀더 데이터를 사용 중입니다.",
        "roadmap": {
            "phase_1": {
                "status": "current",
                "description": "시스템 아키텍처 구축 및 알고리즘 검증",
                "completion": "진행 중"
            },
            "phase_2": {
                "status": "planned",
                "description": "전문 물리치료사 시연 영상 촬영 (100개 운동)",
                "estimated_completion": "2개월 후"
            },
            "phase_3": {
                "status": "planned",
                "description": "다양한 각도 영상 추가 및 난이도별 분류",
                "estimated_completion": "4개월 후"
            },
            "phase_4": {
                "status": "planned",
                "description": "1000+ 운동 데이터베이스 구축",
                "estimated_completion": "6개월 후"
            }
        },
        "note": "실제 헬스케어 전문가와 협력하여 검증된 데이터를 제공할 예정입니다."
    }