# app/api/routers/infra.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.services.traffic_prediction import TrafficPredictor, TrafficDataGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# 전역 예측기 (서버 시작 시 한 번 초기화)
predictor = None
last_training_time = None
TRAINING_INTERVAL_HOURS = 6  # 6시간마다 재학습


def get_or_train_predictor(db: Session) -> TrafficPredictor:
    """
    예측기 가져오기 또는 새로 학습
    """
    global predictor, last_training_time
    
    current_time = datetime.now()
    
    # 첫 실행이거나 재학습 시간이 지났을 때
    if predictor is None or \
       last_training_time is None or \
       (current_time - last_training_time).total_seconds() > TRAINING_INTERVAL_HOURS * 3600:
        
        logger.info("Initializing or retraining Prophet model...")
        
        # 실제 데이터 가져오기 (현재는 시뮬레이션)
        training_data = get_training_data(db)
        
        # 새 예측기 생성 및 학습
        new_predictor = TrafficPredictor(
            base_capacity=1000,
            server_capacity_per_unit=500
        )
        
        new_predictor.train(
            training_data,
            seasonality_mode='multiplicative',
            daily_seasonality=True,
            weekly_seasonality=True
        )
        
        predictor = new_predictor
        last_training_time = current_time
        
        logger.info(f"Model trained successfully at {current_time}")
    
    return predictor


def get_training_data(db: Session):
    """
    실제 트래픽 데이터 가져오기
    
    TODO: DB에서 실제 사용자 활동 로그 조회
    현재는 시뮬레이션 데이터 사용
    """
    # 실제 구현 시:
    # query = db.query(UserActivity).filter(
    #     UserActivity.timestamp >= datetime.now() - timedelta(days=30)
    # )
    # ...
    
    # 임시: 시뮬레이션 데이터
    generator = TrafficDataGenerator()
    return generator.generate_realistic_traffic(
        days=30,
        base_traffic=500,
        peak_hours=[9, 12, 18, 21]
    )


def get_current_traffic(db: Session) -> int:
    """
    현재 실시간 트래픽 조회
    
    TODO: DB에서 현재 활성 세션 수 조회
    """
    # 실제 구현 시:
    # active_sessions = db.query(UserSession).filter(
    #     UserSession.is_active == True
    # ).count()
    # return active_sessions
    
    # 임시: 시뮬레이션
    from app.crud.posts import get_all_posts
    posts = get_all_posts(db)
    
    # 게시물 수 기반 트래픽 추정
    base = 300
    post_multiplier = min(len(posts) * 2, 500)
    
    return base + post_multiplier


@router.get("/status")
def get_infra_status(db: Session = Depends(get_db)) -> Dict:
    """
    인프라 상태 및 트래픽 예측
    
    Returns:
        - 현재 트래픽 상태
        - Prophet 기반 24시간 예측
        - 서버 증설 권장 사항
        - 트래픽 급증 경보
    """
    try:
        # 1. 예측기 가져오기
        traffic_predictor = get_or_train_predictor(db)
        
        # 2. 24시간 예측
        forecast = traffic_predictor.predict_future(hours_ahead=24)
        
        # 3. 예측 요약
        prediction_summary = traffic_predictor.get_prediction_summary(forecast)
        
        # 4. 현재 트래픽
        current_traffic = get_current_traffic(db)
        
        # 5. 트래픽 급증 탐지
        baseline_traffic = prediction_summary['next_24h']['avg_predicted_users']
        spike_detection = traffic_predictor.detect_traffic_spike(
            current_traffic=current_traffic,
            baseline_traffic=baseline_traffic,
            threshold_multiplier=1.5
        )
        
        # 6. 서버 권장 사항
        current_servers = traffic_predictor.calculate_required_servers(current_traffic)
        peak_servers = prediction_summary['server_recommendation']['required_servers']
        
        # 7. 상태 결정
        if spike_detection['is_spike']:
            load_status = f"Traffic Spike Detected ({spike_detection['severity']})"
            alert_level = "critical" if spike_detection['severity'] in ["Critical", "Emergency"] else "warning"
        elif current_traffic > baseline_traffic * 1.2:
            load_status = "High Load"
            alert_level = "warning"
        else:
            load_status = "Stable"
            alert_level = "normal"
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "current_state": {
                "load_status": load_status,
                "alert_level": alert_level,
                "current_users": current_traffic,
                "current_servers": current_servers
            },
            "ai_prediction": {
                "model": "Prophet (Facebook)",
                "next_24h_forecast": {
                    "avg_predicted_users": prediction_summary['next_24h']['avg_predicted_users'],
                    "peak_predicted_users": prediction_summary['next_24h']['peak_predicted_users'],
                    "peak_time": prediction_summary['next_24h']['peak_time'],
                    "confidence_interval": prediction_summary['next_24h']['confidence_interval']
                },
                "server_recommendation": {
                    "needed_servers": peak_servers,
                    "peak_load_time": prediction_summary['server_recommendation']['peak_load_time'],
                    "recommendation": f"Prepare {peak_servers} servers before {prediction_summary['server_recommendation']['peak_load_time']}"
                }
            },
            "spike_detection": spike_detection,
            "infrastructure": {
                "rack_temperature_avg": 24.5,  # TODO: 실제 센서 데이터
                "power_usage_watt": 1200 + (current_servers * 150)
            },
            "model_info": {
                "last_training": last_training_time.isoformat() if last_training_time else None,
                "next_training": (last_training_time + timedelta(hours=TRAINING_INTERVAL_HOURS)).isoformat() if last_training_time else None
            }
        }
    
    except Exception as e:
        logger.error(f"Error in get_infra_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Infrastructure monitoring error: {str(e)}")


@router.get("/forecast/hourly")
def get_hourly_forecast(
    hours: int = 24,
    db: Session = Depends(get_db)
) -> Dict:
    """
    시간별 상세 예측 데이터 (차트용)
    
    Args:
        hours: 예측 시간 (기본 24시간)
    
    Returns:
        시간별 예측 리스트
    """
    try:
        traffic_predictor = get_or_train_predictor(db)
        forecast = traffic_predictor.predict_future(hours_ahead=hours)
        
        hourly_data = traffic_predictor.generate_hourly_forecast_data(
            forecast, 
            hours=hours
        )
        
        return {
            "status": "success",
            "forecast_hours": hours,
            "data": hourly_data,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_hourly_forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain")
def retrain_model(db: Session = Depends(get_db)) -> Dict:
    """
    수동으로 Prophet 모델 재학습
    """
    global predictor, last_training_time
    
    try:
        logger.info("Manual retrain requested...")
        
        training_data = get_training_data(db)
        
        new_predictor = TrafficPredictor()
        train_stats = new_predictor.train(training_data)
        
        predictor = new_predictor
        last_training_time = datetime.now()
        
        return {
            "status": "success",
            "message": "Model retrained successfully",
            "training_stats": train_stats,
            "retrained_at": last_training_time.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in retrain_model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/summary")
def get_metrics_summary(db: Session = Depends(get_db)) -> Dict:
    """
    인프라 메트릭 요약
    """
    try:
        current_traffic = get_current_traffic(db)
        traffic_predictor = get_or_train_predictor(db)
        forecast = traffic_predictor.predict_future(hours_ahead=24)
        summary = traffic_predictor.get_prediction_summary(forecast)
        
        return {
            "current_metrics": {
                "active_users": current_traffic,
                "timestamp": datetime.now().isoformat()
            },
            "predictions": {
                "next_hour": int(forecast.iloc[-1]['yhat']),
                "next_24h_peak": summary['next_24h']['peak_predicted_users'],
                "trend": "increasing" if forecast.iloc[-1]['yhat'] > current_traffic else "decreasing"
            },
            "capacity": {
                "current_utilization": round(current_traffic / 1000 * 100, 2),
                "peak_utilization_24h": round(summary['next_24h']['peak_predicted_users'] / 1000 * 100, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"Error in get_metrics_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))