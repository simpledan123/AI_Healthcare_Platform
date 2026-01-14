# app/services/__init__.py

"""
Services Module

비즈니스 로직, 데이터 분석 및 외부 API 호출을 담당하는 서비스 레이어
"""

# 기존 서비스 임포트
from app.services.rehabilitation_ai import RehabilitationAI
from app.services.pose_similarity import (
    PoseSimilarityAnalyzer,
    ReferenceVideoDatabase
)

# 신규 추가된 서비스 임포트
from app.services.traffic_prediction import TrafficPredictor
from app.services.pose_analytics import PoseAnalytics
from app.services.pose_preprocessing import PoseDataProcessor

__all__ = [
    "RehabilitationAI",
    "PoseSimilarityAnalyzer",
    "ReferenceVideoDatabase",
    "TrafficPredictor",  # 트래픽 예측 서비스
    "PoseAnalytics",     # 자세 데이터 분석 서비스
    "PoseDataProcessor", # 자세 데이터 전처리 서비스
]