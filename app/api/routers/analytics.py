
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.services.pose_analytics import PoseAnalytics

router = APIRouter()
logger = logging.getLogger(__name__)

# 전역 분석기
analytics = PoseAnalytics()


def get_similarity_scores_from_db(db: Session, days: int = 30) -> List[float]:
    """
    DB에서 유사도 점수 조회
    
    TODO: 실제 DB 모델에서 조회
    """
    # 실제 구현 시:
    # from app.models.rehabilitation import RehabilitationSession
    # sessions = db.query(RehabilitationSession).filter(
    #     RehabilitationSession.created_at >= datetime.now() - timedelta(days=days)
    # ).all()
    # return [session.similarity_score for session in sessions]
    
    # 임시: 시뮬레이션 데이터
    import numpy as np
    np.random.seed(42)
    return list(np.random.normal(75, 15, 100).clip(0, 100))


def get_pain_areas_from_db(db: Session, days: int = 30) -> List[str]:
    """
    DB에서 통증 부위 조회
    """
    # 실제 구현 시:
    # from app.models.rehabilitation import RehabilitationRequest
    # requests = db.query(RehabilitationRequest).filter(
    #     RehabilitationRequest.created_at >= datetime.now() - timedelta(days=days)
    # ).all()
    # return [req.pain_area for req in requests]
    
    # 임시: 시뮬레이션
    import random
    areas = ['손목', '어깨', '허리', '목', '무릎', '발목']
    weights = [0.3, 0.25, 0.2, 0.15, 0.07, 0.03]
    return random.choices(areas, weights=weights, k=150)


def get_exercises_from_db(db: Session, days: int = 30) -> List[Dict]:
    """
    DB에서 운동 기록 조회
    """
    # 실제 구현 시:
    # from app.models.rehabilitation import ExerciseSession
    # sessions = db.query(ExerciseSession).filter(
    #     ExerciseSession.created_at >= datetime.now() - timedelta(days=days)
    # ).all()
    # return [
    #     {
    #         "difficulty": s.difficulty,
    #         "similarity_score": s.similarity_score,
    #         "completed": s.completed
    #     }
    #     for s in sessions
    # ]
    
    # 임시: 시뮬레이션
    import random
    import numpy as np
    
    exercises = []
    difficulties = ['초급', '중급', '고급']
    
    for _ in range(100):
        diff = random.choice(difficulties)
        
        # 난이도별 점수 분포
        if diff == '초급':
            score = np.random.normal(80, 10)
        elif diff == '중급':
            score = np.random.normal(70, 15)
        else:
            score = np.random.normal(60, 20)
        
        exercises.append({
            "difficulty": diff,
            "similarity_score": int(np.clip(score, 0, 100)),
            "completed": score >= 60
        })
    
    return exercises


def get_activity_logs_from_db(db: Session, days: int = 30) -> List[Dict]:
    """
    DB에서 활동 로그 조회
    """
    # 실제 구현 시:
    # from app.models.rehabilitation import ActivityLog
    # logs = db.query(ActivityLog).filter(
    #     ActivityLog.timestamp >= datetime.now() - timedelta(days=days)
    # ).all()
    # return [
    #     {
    #         "timestamp": log.timestamp,
    #         "exercise_type": log.exercise_type,
    #         "similarity_score": log.similarity_score
    #     }
    #     for log in logs
    # ]
    
    # 임시: 시뮬레이션
    import random
    import numpy as np
    
    logs = []
    exercises = ['손목 스트레칭', '어깨 회전', '허리 운동', '목 스트레칭']
    
    for day in range(days):
        # 하루에 3-8회 활동
        n_activities = random.randint(3, 8)
        
        for _ in range(n_activities):
            timestamp = datetime.now() - timedelta(
                days=day,
                hours=random.randint(0, 23)
            )
            
            logs.append({
                "timestamp": timestamp,
                "exercise_type": random.choice(exercises),
                "similarity_score": int(np.random.normal(75, 15).clip(0, 100))
            })
    
    return logs


@router.get("/similarity/distribution")
def get_similarity_distribution(
    days: int = Query(30, ge=1, le=365, description="분석 기간 (일)"),
    db: Session = Depends(get_db)
) -> Dict:
    """
    유사도 점수 분포 분석
    
    Returns:
        - 기본 통계 (평균, 중앙값, 표준편차)
        - 등급별 분포 (Excellent, Good, Fair, Poor)
        - 히스토그램 데이터
    """
    try:
        scores = get_similarity_scores_from_db(db, days)
        
        if not scores:
            raise HTTPException(status_code=404, detail="No similarity data found")
        
        distribution = analytics.analyze_similarity_distribution(scores)
        
        return {
            "status": "success",
            "period_days": days,
            "data": distribution,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_similarity_distribution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pain-areas/distribution")
def get_pain_area_distribution(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    통증 부위별 분포 분석
    
    Returns:
        - 부위별 건수 및 비율
        - 가장 많은 통증 부위 TOP 3
    """
    try:
        pain_areas = get_pain_areas_from_db(db, days)
        
        if not pain_areas:
            raise HTTPException(status_code=404, detail="No pain area data found")
        
        distribution = analytics.analyze_pain_area_distribution(pain_areas)
        
        return {
            "status": "success",
            "period_days": days,
            "data": distribution,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_pain_area_distribution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exercises/difficulty")
def get_exercise_difficulty_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    운동 난이도별 통계
    
    Returns:
        - 난이도별 평균 점수
        - 완료율
        - 최고/최저 점수
    """
    try:
        exercises = get_exercises_from_db(db, days)
        
        if not exercises:
            raise HTTPException(status_code=404, detail="No exercise data found")
        
        stats = analytics.analyze_exercise_difficulty(exercises)
        
        return {
            "status": "success",
            "period_days": days,
            "data": stats,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_exercise_difficulty_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/temporal")
def get_temporal_usage_patterns(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    시간대별 사용 패턴 분석
    
    Returns:
        - 시간대별 활동 건수 및 평균 점수
        - 요일별 활동 패턴
        - 피크 시간/요일
    """
    try:
        activity_logs = get_activity_logs_from_db(db, days)
        
        if not activity_logs:
            raise HTTPException(status_code=404, detail="No activity log found")
        
        patterns = analytics.analyze_temporal_patterns(activity_logs)
        
        return {
            "status": "success",
            "period_days": days,
            "data": patterns,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_temporal_usage_patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/summary")
def get_dashboard_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    대시보드 종합 요약
    
    모든 분석 데이터를 한 번에 반환 (차트용)
    """
    try:
        # 데이터 수집
        scores = get_similarity_scores_from_db(db, days)
        pain_areas = get_pain_areas_from_db(db, days)
        exercises = get_exercises_from_db(db, days)
        activity_logs = get_activity_logs_from_db(db, days)
        
        # 종합 분석
        comprehensive = analytics.get_comprehensive_analytics(
            similarity_scores=scores,
            pain_areas=pain_areas,
            exercises=exercises,
            activity_logs=activity_logs
        )
        
        # 추가 KPI
        kpi = {
            "total_sessions": len(scores),
            "avg_similarity": round(sum(scores) / len(scores), 2) if scores else 0,
            "total_exercises": len(exercises),
            "completion_rate": round(
                sum(1 for e in exercises if e['completed']) / len(exercises) * 100, 2
            ) if exercises else 0,
            "active_days": len(set(log['timestamp'].date() for log in activity_logs)) if activity_logs else 0
        }
        
        return {
            "status": "success",
            "period_days": days,
            "kpi": kpi,
            "analytics": comprehensive,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_dashboard_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/similarity-histogram")
def get_similarity_histogram(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    유사도 히스토그램 차트 데이터
    
    Chart.js/Recharts용 형식
    """
    try:
        scores = get_similarity_scores_from_db(db, days)
        distribution = analytics.analyze_similarity_distribution(scores)
        
        histogram = distribution['histogram']
        
        # Chart.js 형식
        chart_data = {
            "labels": histogram['labels'],
            "datasets": [{
                "label": "유사도 분포",
                "data": histogram['counts'],
                "backgroundColor": "rgba(75, 192, 192, 0.6)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1
            }]
        }
        
        return {
            "status": "success",
            "chart_data": chart_data,
            "chart_type": "bar"
        }
    
    except Exception as e:
        logger.error(f"Error in get_similarity_histogram: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/pain-area-pie")
def get_pain_area_pie(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    통증 부위 파이 차트 데이터
    """
    try:
        pain_areas = get_pain_areas_from_db(db, days)
        distribution = analytics.analyze_pain_area_distribution(pain_areas)
        
        # Chart.js 형식
        labels = list(distribution['distribution'].keys())
        data = [distribution['distribution'][area]['count'] for area in labels]
        
        chart_data = {
            "labels": labels,
            "datasets": [{
                "label": "통증 부위 분포",
                "data": data,
                "backgroundColor": [
                    "rgba(255, 99, 132, 0.6)",
                    "rgba(54, 162, 235, 0.6)",
                    "rgba(255, 206, 86, 0.6)",
                    "rgba(75, 192, 192, 0.6)",
                    "rgba(153, 102, 255, 0.6)",
                    "rgba(255, 159, 64, 0.6)"
                ],
                "borderWidth": 1
            }]
        }
        
        return {
            "status": "success",
            "chart_data": chart_data,
            "chart_type": "pie"
        }
    
    except Exception as e:
        logger.error(f"Error in get_pain_area_pie: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/hourly-usage")
def get_hourly_usage_chart(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
) -> Dict:
    """
    시간대별 사용량 라인 차트
    """
    try:
        activity_logs = get_activity_logs_from_db(db, days)
        patterns = analytics.analyze_temporal_patterns(activity_logs)
        
        hourly = patterns['hourly_pattern']
        
        # Chart.js 형식
        hours = sorted(hourly.keys())
        activity_counts = [hourly[h]['activity_count'] for h in hours]
        avg_similarities = [hourly[h]['avg_similarity'] for h in hours]
        
        chart_data = {
            "labels": [f"{h}시" for h in hours],
            "datasets": [
                {
                    "label": "활동 건수",
                    "data": activity_counts,
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "yAxisID": "y"
                },
                {
                    "label": "평균 유사도",
                    "data": avg_similarities,
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "yAxisID": "y1"
                }
            ]
        }
        
        return {
            "status": "success",
            "chart_data": chart_data,
            "chart_type": "line"
        }
    
    except Exception as e:
        logger.error(f"Error in get_hourly_usage_chart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/difficulty-bar")
def get_difficulty_bar_chart(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    난이도별 평균 점수 바 차트
    """
    try:
        exercises = get_exercises_from_db(db, days)
        stats = analytics.analyze_exercise_difficulty(exercises)
        
        difficulties = list(stats['by_difficulty'].keys())
        avg_scores = [stats['by_difficulty'][d]['avg_similarity'] for d in difficulties]
        completion_rates = [stats['by_difficulty'][d]['completion_rate'] for d in difficulties]
        
        chart_data = {
            "labels": difficulties,
            "datasets": [
                {
                    "label": "평균 유사도",
                    "data": avg_scores,
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderWidth": 1
                },
                {
                    "label": "완료율 (%)",
                    "data": completion_rates,
                    "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    "borderWidth": 1
                }
            ]
        }
        
        return {
            "status": "success",
            "chart_data": chart_data,
            "chart_type": "bar"
        }
    
    except Exception as e:
        logger.error(f"Error in get_difficulty_bar_chart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
def export_analytics_csv(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict:
    """
    분석 데이터 CSV 내보내기
    
    TODO: 실제 CSV 파일 생성 및 다운로드
    """
    try:
        scores = get_similarity_scores_from_db(db, days)
        
        # CSV 데이터 준비
        csv_data = {
            "filename": f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "rows": len(scores),
            "download_url": "/analytics/export/csv/download"  # TODO: 실제 구현
        }
        
        return {
            "status": "success",
            "csv_info": csv_data
        }
    
    except Exception as e:
        logger.error(f"Error in export_analytics_csv: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
