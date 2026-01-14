// frontend/src/pages/Analytics.jsx

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
} from 'chart.js';
import { Bar, Pie, Line } from 'react-chartjs-2';

// Chart.js 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

const API_BASE_URL = 'http://localhost:8000';

const Analytics = () => {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);
  const [dashboardData, setDashboardData] = useState(null);
  
  // 차트 데이터
  const [similarityChart, setSimilarityChart] = useState(null);
  const [painAreaChart, setPainAreaChart] = useState(null);
  const [hourlyUsageChart, setHourlyUsageChart] = useState(null);
  const [difficultyChart, setDifficultyChart] = useState(null);

  useEffect(() => {
    fetchAnalyticsData();
  }, [period]);

  const fetchAnalyticsData = async () => {
    setLoading(true);
    try {
      // 1. 대시보드 종합 데이터
      const dashboardRes = await axios.get(
        `${API_BASE_URL}/analytics/dashboard/summary?days=${period}`
      );
      setDashboardData(dashboardRes.data);

      // 2. 유사도 히스토그램
      const similarityRes = await axios.get(
        `${API_BASE_URL}/analytics/charts/similarity-histogram?days=${period}`
      );
      setSimilarityChart(similarityRes.data.chart_data);

      // 3. 통증 부위 파이 차트
      const painAreaRes = await axios.get(
        `${API_BASE_URL}/analytics/charts/pain-area-pie?days=${period}`
      );
      setPainAreaChart(painAreaRes.data.chart_data);

      // 4. 시간대별 사용량
      const hourlyRes = await axios.get(
        `${API_BASE_URL}/analytics/charts/hourly-usage?days=${period}`
      );
      setHourlyUsageChart(hourlyRes.data.chart_data);

      // 5. 난이도별 성과
      const difficultyRes = await axios.get(
        `${API_BASE_URL}/analytics/charts/difficulty-bar?days=${period}`
      );
      setDifficultyChart(difficultyRes.data.chart_data);

    } catch (error) {
      console.error('Analytics data fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">분석 데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">데이터를 불러올 수 없습니다.</p>
      </div>
    );
  }

  const { kpi, analytics } = dashboardData;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">데이터 분석 대시보드</h1>
          <p className="mt-2 text-gray-600">
            재활운동 사용 패턴 및 통계 분석
          </p>
        </div>

        {/* 기간 선택 */}
        <div className="mb-6 flex gap-2">
          {[7, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setPeriod(days)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                period === days
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {days}일
            </button>
          ))}
        </div>

        {/* KPI 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <KPICard
            title="총 세션"
            value={kpi.total_sessions}
            unit="회"
            color="blue"
          />
          <KPICard
            title="평균 유사도"
            value={kpi.avg_similarity}
            unit="점"
            color="green"
          />
          <KPICard
            title="운동 완료율"
            value={kpi.completion_rate}
            unit="%"
            color="purple"
          />
          <KPICard
            title="활동 일수"
            value={kpi.active_days}
            unit="일"
            color="orange"
          />
        </div>

        {/* 차트 그리드 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 유사도 분포 */}
          <ChartCard title="유사도 점수 분포">
            {similarityChart && <Bar data={similarityChart} options={barOptions} />}
          </ChartCard>

          {/* 통증 부위 분포 */}
          <ChartCard title="통증 부위 분포">
            {painAreaChart && <Pie data={painAreaChart} options={pieOptions} />}
          </ChartCard>

          {/* 시간대별 사용량 */}
          <ChartCard title="시간대별 활동 패턴" fullWidth>
            {hourlyUsageChart && (
              <Line data={hourlyUsageChart} options={lineOptions} />
            )}
          </ChartCard>

          {/* 난이도별 성과 */}
          <ChartCard title="난이도별 평균 점수">
            {difficultyChart && <Bar data={difficultyChart} options={barOptions} />}
          </ChartCard>
        </div>

        {/* 상세 통계 */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">상세 통계</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 유사도 통계 */}
            <StatSection
              title="유사도 분석"
              stats={[
                { label: '평균', value: analytics.similarity_analysis.mean.toFixed(2) },
                { label: '중앙값', value: analytics.similarity_analysis.median.toFixed(2) },
                { label: '표준편차', value: analytics.similarity_analysis.std.toFixed(2) },
                { label: '최고점', value: analytics.similarity_analysis.max.toFixed(2) },
              ]}
            />

            {/* 등급 분포 */}
            <StatSection
              title="등급별 분포"
              stats={[
                {
                  label: 'Excellent',
                  value: `${analytics.similarity_analysis.grade_distribution.excellent.percentage}%`,
                },
                {
                  label: 'Good',
                  value: `${analytics.similarity_analysis.grade_distribution.good.percentage}%`,
                },
                {
                  label: 'Fair',
                  value: `${analytics.similarity_analysis.grade_distribution.fair.percentage}%`,
                },
                {
                  label: 'Poor',
                  value: `${analytics.similarity_analysis.grade_distribution.poor.percentage}%`,
                },
              ]}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

// KPI 카드 컴포넌트
const KPICard = ({ title, value, unit, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    orange: 'bg-orange-50 text-orange-700',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm text-gray-600 mb-2">{title}</p>
      <div className="flex items-baseline">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        <span className={`ml-2 text-sm font-medium ${colorClasses[color]}`}>
          {unit}
        </span>
      </div>
    </div>
  );
};

// 차트 카드 컴포넌트
const ChartCard = ({ title, children, fullWidth = false }) => {
  return (
    <div className={`bg-white rounded-lg shadow p-6 ${fullWidth ? 'lg:col-span-2' : ''}`}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-64">
        {children}
      </div>
    </div>
  );
};

// 상세 통계 섹션
const StatSection = ({ title, stats }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>
      <div className="space-y-2">
        {stats.map((stat, idx) => (
          <div key={idx} className="flex justify-between items-center">
            <span className="text-gray-600">{stat.label}</span>
            <span className="font-semibold text-gray-900">{stat.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Chart.js 옵션
const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
    },
  },
  scales: {
    y: {
      beginAtZero: true,
    },
  },
};

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right',
    },
  },
};

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      position: 'top',
    },
  },
  scales: {
    y: {
      type: 'linear',
      display: true,
      position: 'left',
    },
    y1: {
      type: 'linear',
      display: true,
      position: 'right',
      grid: {
        drawOnChartArea: false,
      },
    },
  },
};

export default Analytics;
