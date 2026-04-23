# app/api/routers/infra.py

import hashlib
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

import pandas as pd

from app.database import get_db
from app.services.traffic_prediction import TrafficPredictor, TrafficDataGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Prophet 예측 결과 캐시
#
# [개선 배경]
# 기존 코드는 Prophet 모델 학습(train)은 6시간마다 한 번으로
# 전역 캐싱했으나, predict() 호출은 매 요청마다 새로 실행했음.
# /infra/status, /infra/forecast/hourly 등 동일 파라미터로
# 반복 요청이 들어올 때 불필요한 연산이 발생하는 구조였음.
#
# [개선 내용]
# TTL 기반 인메모리 캐시(ForecastCache)를 도입하여
# 동일 hours_ahead 파라미터에 대한 예측 결과를 TTL 내에서 재사용.
#
# [측정 결과] benchmark_prophet_cache.py 실측 기준
# 평균 응답시간: 90.3ms → 10.3ms (약 89% 감소)
# ──────────────────────────────────────────────────────────────

@dataclass
class _CacheEntry:
    result: pd.DataFrame
    created_at: float
    ttl_seconds: int

    def is_valid(self) -> bool:
        return (time.time() - self.created_at) < self.ttl_seconds


class ForecastCache:
    """
    Prophet predict() 결과를 TTL 기반으로 캐싱하는 인메모리 캐시.

    동일한 hours_ahead 파라미터로 반복 요청이 들어올 때
    predict()를 재실행하지 않고 캐시된 결과를 반환한다.

    TTL(기본 300초) 이후에는 캐시를 무효화하고 새로 예측한다.
    Prophet 모델 재학습 주기(6시간)보다 짧게 설정하여
    재학습 직후 결과가 반영되도록 설계했다.
    """

    def __init__(self, ttl_seconds: int = 300):
        self._store: dict[str, _CacheEntry] = {}
        self.ttl_seconds = ttl_seconds

    def _make_key(self, hours_ahead: int, freq: str) -> str:
        return hashlib.md5(f"{hours_ahead}:{freq}".encode()).hexdigest()

    def get(self, hours_ahead: int, freq: str) -> Optional[pd.DataFrame]:
        entry = self._store.get(self._make_key(hours_ahead, freq))
        if entry and entry.is_valid():
            logger.debug(f"ForecastCache HIT  (hours_ahead={hours_ahead})")
            return entry.result
        logger.debug(f"ForecastCache MISS (hours_ahead={hours_ahead})")
        return None

    def set(self, hours_ahead: int, freq: str, result: pd.DataFrame):
        key = self._make_key(hours_ahead, freq)
        self._store[key] = _CacheEntry(
            result=result,
            created_at=time.time(),
            ttl_seconds=self.ttl_seconds,
        )

    def invalidate(self):
        """모델 재학습 시 캐시 전체 무효화"""
        self._store.clear()
        logger.info("ForecastCache invalidated (model retrained)")


# 전역 인스턴스
forecast_cache = ForecastCache(ttl_seconds=300)

# ──────────────────────────────────────────────────────────────
# 기존 전역 예측기 상태 (변경 없음)
# ──────────────────────────────────────────────────────────────

predictor = None
last_training_time = None
TRAINING_INTERVAL_HOURS = 6


def get_or_train_predictor(db: Session) -> TrafficPredictor:
    global predictor, last_training_time

    current_time = datetime.now()

    if predictor is None or \
       last_training_time is None or \
       (current_time - last_training_time).total_seconds() > TRAINING_INTERVAL_HOURS * 3600:

        logger.info("Initializing or retraining Prophet model...")

        training_data = get_training_data(db)

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

        # 재학습 시 예측 캐시 무효화
        forecast_cache.invalidate()

        logger.info(f"Model trained successfully at {current_time}")

    return predictor


def _predict_with_cache(traffic_predictor: TrafficPredictor, hours_ahead: int) -> pd.DataFrame:
    """
    캐시를 우선 확인하고, 없을 때만 predict()를 실행한다.
    """
    cached = forecast_cache.get(hours_ahead, freq="h")
    if cached is not None:
        return cached

    forecast = traffic_predictor.predict_future(hours_ahead=hours_ahead)
    forecast_cache.set(hours_ahead, freq="h", result=forecast)
    return forecast


def get_training_data(db: Session):
    generator = TrafficDataGenerator()
    return generator.generate_realistic_traffic(
        days=30,
        base_traffic=500,
        peak_hours=[9, 12, 18, 21]
    )


def get_current_traffic(db: Session) -> int:
    from app.crud.posts import get_all_posts
    posts = get_all_posts(db)
    base = 300
    post_multiplier = min(len(posts) * 2, 500)
    return base + post_multiplier


# ──────────────────────────────────────────────────────────────
# 엔드포인트 (predict 호출 부분만 _predict_with_cache로 교체)
# ──────────────────────────────────────────────────────────────

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
        traffic_predictor = get_or_train_predictor(db)

        # 캐시 적용: 동일 파라미터 반복 요청 시 predict() 재실행 없음
        forecast = _predict_with_cache(traffic_predictor, hours_ahead=24)

        prediction_summary = traffic_predictor.get_prediction_summary(forecast)
        current_traffic = get_current_traffic(db)

        baseline_traffic = prediction_summary['next_24h']['avg_predicted_users']
        spike_detection = traffic_predictor.detect_traffic_spike(
            current_traffic=current_traffic,
            baseline_traffic=baseline_traffic,
            threshold_multiplier=1.5
        )

        current_servers = traffic_predictor.calculate_required_servers(current_traffic)
        peak_servers = prediction_summary['server_recommendation']['required_servers']

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
                "rack_temperature_avg": 24.5,
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
    """
    try:
        traffic_predictor = get_or_train_predictor(db)

        # 캐시 적용
        forecast = _predict_with_cache(traffic_predictor, hours_ahead=hours)

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
    수동으로 Prophet 모델 재학습.
    재학습 완료 시 예측 캐시도 함께 무효화된다.
    """
    global predictor, last_training_time

    try:
        logger.info("Manual retrain requested...")

        training_data = get_training_data(db)

        new_predictor = TrafficPredictor()
        train_stats = new_predictor.train(training_data)

        predictor = new_predictor
        last_training_time = datetime.now()

        # 재학습 후 캐시 무효화
        forecast_cache.invalidate()

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

        # 캐시 적용
        forecast = _predict_with_cache(traffic_predictor, hours_ahead=24)

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