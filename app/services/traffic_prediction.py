# app/services/traffic_prediction.py

import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrafficPredictor:
    """
    Prophet 기반 실시간 트래픽 예측 시스템
    
    주요 기능:
    1. 과거 트래픽 데이터 학습
    2. 미래 트래픽 예측 (시간별, 일별)
    3. 서버 증설 필요 시점 예측
    4. 이상 트래픽 탐지
    """
    
    def __init__(
        self, 
        base_capacity: int = 1000,
        server_capacity_per_unit: int = 500
    ):
        """
        Args:
            base_capacity: 기본 서버 용량 (동시 접속자 수)
            server_capacity_per_unit: 서버 1대당 처리 용량
        """
        self.base_capacity = base_capacity
        self.server_capacity_per_unit = server_capacity_per_unit
        self.model = None
        self.training_data = None
        self.is_trained = False
    
    def prepare_training_data(
        self, 
        timestamps: List[datetime],
        user_counts: List[int]
    ) -> pd.DataFrame:
        """
        Prophet 학습용 데이터 준비
        
        Args:
            timestamps: 시간 리스트
            user_counts: 사용자 수 리스트
        
        Returns:
            Prophet 형식 DataFrame (ds, y 컬럼)
        """
        df = pd.DataFrame({
            'ds': timestamps,
            'y': user_counts
        })
        
        # 정렬 및 중복 제거
        df = df.sort_values('ds').drop_duplicates('ds')
        
        logger.info(f"Prepared {len(df)} training samples")
        
        return df
    
    def train(
        self, 
        historical_data: pd.DataFrame,
        seasonality_mode: str = 'multiplicative',
        daily_seasonality: bool = True,
        weekly_seasonality: bool = True
    ) -> Dict:
        """
        Prophet 모델 학습
        
        Args:
            historical_data: ds, y 컬럼을 가진 DataFrame
            seasonality_mode: 'additive' 또는 'multiplicative'
            daily_seasonality: 일별 패턴 학습 여부
            weekly_seasonality: 주별 패턴 학습 여부
        
        Returns:
            학습 통계
        """
        logger.info("Starting Prophet model training...")
        
        # Prophet 모델 생성
        self.model = Prophet(
            seasonality_mode=seasonality_mode,
            daily_seasonality=daily_seasonality,
            weekly_seasonality=weekly_seasonality,
            changepoint_prior_scale=0.05,  # 트렌드 변화 민감도
            seasonality_prior_scale=10.0   # 계절성 강도
        )
        
        # 시간대별 패턴 추가 (출퇴근 시간 등)
        self.model.add_seasonality(
            name='hourly',
            period=1,
            fourier_order=8
        )
        
        # 학습
        self.model.fit(historical_data)
        self.training_data = historical_data
        self.is_trained = True
        
        logger.info("Training complete")
        
        return {
            "training_samples": len(historical_data),
            "date_range": {
                "start": str(historical_data['ds'].min()),
                "end": str(historical_data['ds'].max())
            },
            "avg_traffic": float(historical_data['y'].mean()),
            "max_traffic": int(historical_data['y'].max()),
            "min_traffic": int(historical_data['y'].min())
        }
    
    def predict_future(
        self, 
        hours_ahead: int = 24,
        freq: str = 'H'
    ) -> pd.DataFrame:
        """
        미래 트래픽 예측
        
        Args:
            hours_ahead: 예측 시간 (시간 단위)
            freq: 예측 주기 ('H'=시간별, 'D'=일별)
        
        Returns:
            예측 결과 DataFrame (ds, yhat, yhat_lower, yhat_upper)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # 미래 데이터프레임 생성
        future = self.model.make_future_dataframe(
            periods=hours_ahead,
            freq=freq
        )
        
        # 예측
        forecast = self.model.predict(future)
        
        logger.info(f"Predicted {hours_ahead} hours ahead")
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    
    def calculate_required_servers(
        self, 
        predicted_users: int,
        safety_margin: float = 1.2
    ) -> int:
        """
        필요 서버 대수 계산
        
        Args:
            predicted_users: 예측 사용자 수
            safety_margin: 안전 마진 (1.2 = 20% 여유)
        
        Returns:
            필요 서버 대수
        """
        required_capacity = predicted_users * safety_margin
        servers_needed = int(np.ceil(required_capacity / self.server_capacity_per_unit))
        
        return max(1, servers_needed)
    
    def detect_traffic_spike(
        self, 
        current_traffic: int,
        baseline_traffic: int,
        threshold_multiplier: float = 1.5
    ) -> Dict:
        """
        트래픽 급증 탐지
        
        Args:
            current_traffic: 현재 트래픽
            baseline_traffic: 평균 트래픽
            threshold_multiplier: 급증 판단 기준 (1.5 = 50% 증가)
        
        Returns:
            급증 여부 및 상세 정보
        """
        is_spike = current_traffic > baseline_traffic * threshold_multiplier
        spike_percentage = ((current_traffic - baseline_traffic) / baseline_traffic) * 100
        
        return {
            "is_spike": is_spike,
            "current_traffic": current_traffic,
            "baseline_traffic": baseline_traffic,
            "spike_percentage": round(spike_percentage, 2),
            "severity": self._get_spike_severity(spike_percentage)
        }
    
    def _get_spike_severity(self, spike_percentage: float) -> str:
        """트래픽 급증 심각도 판단"""
        if spike_percentage < 50:
            return "Normal"
        elif spike_percentage < 100:
            return "Warning"
        elif spike_percentage < 200:
            return "Critical"
        else:
            return "Emergency"
    
    def get_prediction_summary(
        self, 
        forecast: pd.DataFrame,
        include_server_recommendation: bool = True
    ) -> Dict:
        """
        예측 결과 요약
        
        Returns:
            예측 통계 및 서버 권장 사항
        """
        latest_forecast = forecast.tail(24)  # 최근 24시간
        
        summary = {
            "next_24h": {
                "avg_predicted_users": int(latest_forecast['yhat'].mean()),
                "peak_predicted_users": int(latest_forecast['yhat'].max()),
                "peak_time": str(latest_forecast.loc[latest_forecast['yhat'].idxmax(), 'ds']),
                "min_predicted_users": int(latest_forecast['yhat'].min()),
                "confidence_interval": {
                    "lower": int(latest_forecast['yhat_lower'].mean()),
                    "upper": int(latest_forecast['yhat_upper'].mean())
                }
            }
        }
        
        if include_server_recommendation:
            peak_users = int(latest_forecast['yhat'].max())
            servers_needed = self.calculate_required_servers(peak_users)
            
            summary["server_recommendation"] = {
                "required_servers": servers_needed,
                "peak_load_time": str(latest_forecast.loc[latest_forecast['yhat'].idxmax(), 'ds']),
                "estimated_capacity_needed": peak_users,
                "safety_margin_applied": "20%"
            }
        
        return summary
    
    def generate_hourly_forecast_data(
        self, 
        forecast: pd.DataFrame,
        hours: int = 24
    ) -> List[Dict]:
        """
        시간별 예측 데이터 (차트용)
        
        Returns:
            시간별 예측 리스트
        """
        latest = forecast.tail(hours)
        
        return [
            {
                "timestamp": str(row['ds']),
                "predicted_users": int(row['yhat']),
                "lower_bound": int(row['yhat_lower']),
                "upper_bound": int(row['yhat_upper']),
                "required_servers": self.calculate_required_servers(int(row['yhat']))
            }
            for _, row in latest.iterrows()
        ]


class TrafficDataGenerator:
    """
    실제 데이터가 없을 때 시뮬레이션용 트래픽 데이터 생성기
    """
    
    @staticmethod
    def generate_realistic_traffic(
        days: int = 30,
        base_traffic: int = 500,
        peak_hours: List[int] = [9, 12, 18, 21]
    ) -> pd.DataFrame:
        """
        현실적인 트래픽 패턴 생성
        
        Args:
            days: 생성할 날짜 수
            base_traffic: 기본 트래픽
            peak_hours: 피크 시간대
        
        Returns:
            시뮬레이션 데이터
        """
        timestamps = []
        user_counts = []
        
        start_date = datetime.now() - timedelta(days=days)
        
        for day in range(days):
            for hour in range(24):
                timestamp = start_date + timedelta(days=day, hours=hour)
                
                # 기본 트래픽
                traffic = base_traffic
                
                # 시간대별 패턴
                if hour in peak_hours:
                    traffic *= 2.0  # 피크 시간 2배
                elif 1 <= hour <= 6:
                    traffic *= 0.3  # 새벽 30%
                
                # 주말 패턴
                if timestamp.weekday() >= 5:  # 토, 일
                    traffic *= 1.5
                
                # 랜덤 노이즈
                noise = np.random.normal(0, traffic * 0.1)
                traffic = int(traffic + noise)
                
                timestamps.append(timestamp)
                user_counts.append(max(0, traffic))
        
        return pd.DataFrame({
            'ds': timestamps,
            'y': user_counts
        })


def demo_traffic_prediction():
    """트래픽 예측 데모"""
    logger.info("=== Traffic Prediction Demo ===")
    
    # 1. 시뮬레이션 데이터 생성
    generator = TrafficDataGenerator()
    training_data = generator.generate_realistic_traffic(days=30)
    logger.info(f"Generated {len(training_data)} training samples")
    
    # 2. 예측기 생성 및 학습
    predictor = TrafficPredictor()
    train_stats = predictor.train(training_data)
    logger.info(f"Training stats: {train_stats}")
    
    # 3. 24시간 예측
    forecast = predictor.predict_future(hours_ahead=24)
    
    # 4. 예측 요약
    summary = predictor.get_prediction_summary(forecast)
    logger.info(f"Prediction summary: {summary}")
    
    # 5. 트래픽 급증 탐지
    current_traffic = int(forecast.tail(1)['yhat'].values[0])
    baseline = train_stats['avg_traffic']
    spike_info = predictor.detect_traffic_spike(current_traffic, baseline)
    logger.info(f"Spike detection: {spike_info}")
    
    return {
        "training_stats": train_stats,
        "prediction_summary": summary,
        "spike_detection": spike_info
    }


if __name__ == "__main__":
    demo_traffic_prediction()
