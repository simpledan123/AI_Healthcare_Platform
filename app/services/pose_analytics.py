# app/services/pose_analytics.py

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoseAnalytics:
    """
    MediaPipe 자세 데이터 통합 분석 시스템
    
    주요 기능:
    1. 유사도 점수 분포 분석
    2. 부위별 통증 패턴 분석
    3. 운동 난이도별 통계
    4. 시계열 분석 (시간대별 사용 패턴)
    5. 자세 품질 평가
    """
    
    def __init__(self):
        self.similarity_threshold_excellent = 85
        self.similarity_threshold_good = 70
        self.similarity_threshold_fair = 50
    
    def analyze_similarity_distribution(
        self, 
        similarity_scores: List[float]
    ) -> Dict:
        """
        유사도 점수 분포 분석
        
        Args:
            similarity_scores: 유사도 점수 리스트 (0-100)
        
        Returns:
            통계 분석 결과
        """
        if not similarity_scores:
            return {"error": "No similarity scores provided"}
        
        scores = np.array(similarity_scores)
        
        # 기본 통계
        stats = {
            "total_comparisons": len(scores),
            "mean": float(np.mean(scores)),
            "median": float(np.median(scores)),
            "std": float(np.std(scores)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores)),
            "quartiles": {
                "q1": float(np.percentile(scores, 25)),
                "q2": float(np.percentile(scores, 50)),
                "q3": float(np.percentile(scores, 75))
            }
        }
        
        # 등급별 분포
        excellent = np.sum(scores >= self.similarity_threshold_excellent)
        good = np.sum((scores >= self.similarity_threshold_good) & 
                      (scores < self.similarity_threshold_excellent))
        fair = np.sum((scores >= self.similarity_threshold_fair) & 
                     (scores < self.similarity_threshold_good))
        poor = np.sum(scores < self.similarity_threshold_fair)
        
        stats["grade_distribution"] = {
            "excellent": {
                "count": int(excellent),
                "percentage": round(excellent / len(scores) * 100, 2)
            },
            "good": {
                "count": int(good),
                "percentage": round(good / len(scores) * 100, 2)
            },
            "fair": {
                "count": int(fair),
                "percentage": round(fair / len(scores) * 100, 2)
            },
            "poor": {
                "count": int(poor),
                "percentage": round(poor / len(scores) * 100, 2)
            }
        }
        
        # 히스토그램 데이터 (10점 단위)
        bins = np.arange(0, 101, 10)
        hist, _ = np.histogram(scores, bins=bins)
        
        stats["histogram"] = {
            "bins": bins.tolist(),
            "counts": hist.tolist(),
            "labels": [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]
        }
        
        logger.info(f"Analyzed {len(scores)} similarity scores")
        
        return stats
    
    def analyze_pain_area_distribution(
        self, 
        pain_areas: List[str]
    ) -> Dict:
        """
        통증 부위별 분포 분석
        
        Args:
            pain_areas: 통증 부위 리스트 (예: ['손목', '어깨', '허리'])
        
        Returns:
            부위별 통계
        """
        if not pain_areas:
            return {"error": "No pain areas provided"}
        
        area_counts = Counter(pain_areas)
        total = len(pain_areas)
        
        distribution = {}
        for area, count in area_counts.most_common():
            distribution[area] = {
                "count": count,
                "percentage": round(count / total * 100, 2)
            }
        
        return {
            "total_reports": total,
            "unique_areas": len(area_counts),
            "distribution": distribution,
            "most_common": area_counts.most_common(3)
        }
    
    def analyze_exercise_difficulty(
        self, 
        exercises: List[Dict]
    ) -> Dict:
        """
        운동 난이도별 분석
        
        Args:
            exercises: 운동 정보 리스트
                [{
                    "difficulty": "초급",
                    "similarity_score": 75,
                    "completed": True
                }]
        
        Returns:
            난이도별 통계
        """
        if not exercises:
            return {"error": "No exercises provided"}
        
        df = pd.DataFrame(exercises)
        
        difficulty_stats = {}
        
        for difficulty in df['difficulty'].unique():
            subset = df[df['difficulty'] == difficulty]
            
            difficulty_stats[difficulty] = {
                "total_attempts": len(subset),
                "avg_similarity": float(subset['similarity_score'].mean()),
                "completion_rate": float(subset['completed'].mean() * 100),
                "min_score": float(subset['similarity_score'].min()),
                "max_score": float(subset['similarity_score'].max())
            }
        
        return {
            "total_exercises": len(exercises),
            "by_difficulty": difficulty_stats
        }
    
    def analyze_temporal_patterns(
        self, 
        activity_logs: List[Dict]
    ) -> Dict:
        """
        시계열 패턴 분석 (시간대별 사용 패턴)
        
        Args:
            activity_logs: 활동 로그 리스트
                [{
                    "timestamp": datetime,
                    "exercise_type": "손목 스트레칭",
                    "similarity_score": 80
                }]
        
        Returns:
            시간대별 통계
        """
        if not activity_logs:
            return {"error": "No activity logs provided"}
        
        df = pd.DataFrame(activity_logs)
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        
        # 시간대별 분석
        hourly = df.groupby('hour').agg({
            'similarity_score': ['count', 'mean']
        }).round(2)
        
        # 요일별 분석
        daily = df.groupby('day_of_week').agg({
            'similarity_score': ['count', 'mean']
        }).round(2)
        
        day_names = ['월', '화', '수', '목', '금', '토', '일']
        
        return {
            "hourly_pattern": {
                str(hour): {
                    "activity_count": int(hourly.loc[hour, ('similarity_score', 'count')]),
                    "avg_similarity": float(hourly.loc[hour, ('similarity_score', 'mean')])
                }
                for hour in hourly.index
            },
            "daily_pattern": {
                day_names[day]: {
                    "activity_count": int(daily.loc[day, ('similarity_score', 'count')]),
                    "avg_similarity": float(daily.loc[day, ('similarity_score', 'mean')])
                }
                for day in daily.index
            },
            "peak_hour": int(hourly[('similarity_score', 'count')].idxmax()),
            "peak_day": day_names[int(daily[('similarity_score', 'count')].idxmax())]
        }
    
    def analyze_pose_quality(
        self, 
        landmarks_sequence: List[np.ndarray],
        visibility_scores: List[np.ndarray]
    ) -> Dict:
        """
        자세 품질 분석
        
        Args:
            landmarks_sequence: 랜드마크 시퀀스
            visibility_scores: 신뢰도 점수 시퀀스
        
        Returns:
            품질 평가 결과
        """
        if not landmarks_sequence or not visibility_scores:
            return {"error": "No pose data provided"}
        
        # 평균 신뢰도
        avg_visibility = [np.mean(scores) for scores in visibility_scores]
        
        # 프레임 안정성 (연속 프레임 간 변화량)
        frame_stability = []
        for i in range(1, len(landmarks_sequence)):
            diff = np.linalg.norm(landmarks_sequence[i] - landmarks_sequence[i-1])
            frame_stability.append(diff)
        
        quality = {
            "total_frames": len(landmarks_sequence),
            "avg_landmark_confidence": float(np.mean(avg_visibility)),
            "min_confidence": float(np.min(avg_visibility)),
            "max_confidence": float(np.max(avg_visibility)),
            "frame_stability": {
                "avg_movement": float(np.mean(frame_stability)) if frame_stability else 0,
                "max_movement": float(np.max(frame_stability)) if frame_stability else 0,
                "is_stable": float(np.mean(frame_stability)) < 0.1 if frame_stability else True
            }
        }
        
        # 품질 등급
        if quality["avg_landmark_confidence"] >= 0.8 and quality["frame_stability"]["is_stable"]:
            quality["overall_grade"] = "Excellent"
        elif quality["avg_landmark_confidence"] >= 0.6:
            quality["overall_grade"] = "Good"
        elif quality["avg_landmark_confidence"] >= 0.4:
            quality["overall_grade"] = "Fair"
        else:
            quality["overall_grade"] = "Poor"
        
        return quality
    
    def generate_user_progress_report(
        self, 
        user_sessions: List[Dict]
    ) -> Dict:
        """
        사용자 진척도 리포트 생성
        
        Args:
            user_sessions: 세션 기록 리스트
                [{
                    "date": datetime,
                    "exercise_name": str,
                    "similarity_score": int,
                    "duration_seconds": int
                }]
        
        Returns:
            진척도 리포트
        """
        if not user_sessions:
            return {"error": "No user sessions provided"}
        
        df = pd.DataFrame(user_sessions)
        df['date'] = pd.to_datetime(df['date'])
        
        # 시간 경과별 개선도
        df_sorted = df.sort_values('date')
        first_10 = df_sorted.head(10)['similarity_score'].mean()
        last_10 = df_sorted.tail(10)['similarity_score'].mean()
        improvement = last_10 - first_10
        
        # 운동별 최고 점수
        best_scores = df.groupby('exercise_name')['similarity_score'].max().to_dict()
        
        # 총 운동 시간
        total_duration = df['duration_seconds'].sum()
        
        return {
            "total_sessions": len(user_sessions),
            "date_range": {
                "first_session": str(df['date'].min()),
                "last_session": str(df['date'].max()),
                "days_active": (df['date'].max() - df['date'].min()).days
            },
            "performance": {
                "current_avg": float(last_10),
                "initial_avg": float(first_10),
                "improvement": float(improvement),
                "improvement_percentage": round(improvement / first_10 * 100, 2) if first_10 > 0 else 0
            },
            "best_scores_by_exercise": best_scores,
            "total_exercise_time": {
                "seconds": int(total_duration),
                "minutes": int(total_duration / 60),
                "hours": round(total_duration / 3600, 2)
            },
            "consistency": {
                "avg_sessions_per_week": round(len(user_sessions) / max(1, (df['date'].max() - df['date'].min()).days / 7), 2)
            }
        }
    
    def get_comprehensive_analytics(
        self,
        similarity_scores: List[float],
        pain_areas: List[str],
        exercises: List[Dict],
        activity_logs: List[Dict]
    ) -> Dict:
        """
        종합 분석 리포트
        
        Returns:
            모든 분석 결과 통합
        """
        return {
            "similarity_analysis": self.analyze_similarity_distribution(similarity_scores),
            "pain_area_analysis": self.analyze_pain_area_distribution(pain_areas),
            "difficulty_analysis": self.analyze_exercise_difficulty(exercises),
            "temporal_analysis": self.analyze_temporal_patterns(activity_logs),
            "generated_at": str(datetime.now())
        }


def demo_pose_analytics():
    """자세 분석 데모"""
    logger.info("=== Pose Analytics Demo ===")
    
    analytics = PoseAnalytics()
    
    # 1. 유사도 분석
    similarity_scores = [85, 90, 72, 65, 88, 95, 78, 82, 55, 91]
    sim_stats = analytics.analyze_similarity_distribution(similarity_scores)
    logger.info(f"Similarity stats: {sim_stats}")
    
    # 2. 통증 부위 분석
    pain_areas = ['손목', '어깨', '손목', '허리', '어깨', '손목', '목']
    pain_stats = analytics.analyze_pain_area_distribution(pain_areas)
    logger.info(f"Pain area stats: {pain_stats}")
    
    # 3. 난이도 분석
    exercises = [
        {"difficulty": "초급", "similarity_score": 85, "completed": True},
        {"difficulty": "중급", "similarity_score": 72, "completed": True},
        {"difficulty": "초급", "similarity_score": 90, "completed": True},
    ]
    diff_stats = analytics.analyze_exercise_difficulty(exercises)
    logger.info(f"Difficulty stats: {diff_stats}")
    
    return {
        "similarity_analysis": sim_stats,
        "pain_analysis": pain_stats,
        "difficulty_analysis": diff_stats
    }


if __name__ == "__main__":
    demo_pose_analytics()
