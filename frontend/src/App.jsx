// frontend/src/App.jsx

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Rehabilitation from './components/Rehabilitation';
import ExerciseComparison from './components/ExerciseComparison';
import CommunityFeed from './components/CommunityFeed';
import Analytics from './pages/Analytics';  // 새로 추가!

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        {/* 네비게이션 바 */}
        <nav className="bg-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex space-x-8">
                <Link
                  to="/"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                >
                  홈
                </Link>
                <Link
                  to="/rehabilitation"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                >
                  재활운동 추천
                </Link>
                <Link
                  to="/exercise"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                >
                  자세 비교
                </Link>
                <Link
                  to="/community"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                >
                  커뮤니티
                </Link>
                <Link
                  to="/analytics"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                >
                  📊 데이터 분석
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* 라우트 */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/rehabilitation" element={<Rehabilitation />} />
          <Route path="/exercise" element={<ExerciseComparison />} />
          <Route path="/community" element={<CommunityFeed />} />
          <Route path="/analytics" element={<Analytics />} />  {/* 새로 추가! */}
        </Routes>
      </div>
    </Router>
  );
}

// 홈 페이지
const Home = () => {
  return (
    <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Physical AI Healthcare Platform
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI 기반 재활운동 추천 및 자세 분석 시스템
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
          <FeatureCard
            title="재활운동 추천"
            description="Claude AI가 개인 맞춤 재활운동을 추천합니다"
            link="/rehabilitation"
            icon="🏃"
          />
          <FeatureCard
            title="자세 비교"
            description="MediaPipe로 실시간 자세를 분석합니다"
            link="/exercise"
            icon="🎯"
          />
          <FeatureCard
            title="커뮤니티"
            description="다른 사용자들과 경험을 공유하세요"
            link="/community"
            icon="👥"
          />
          <FeatureCard
            title="데이터 분석"
            description="사용 패턴과 통계를 확인하세요"
            link="/analytics"
            icon="📊"
          />
        </div>
      </div>
    </div>
  );
};

const FeatureCard = ({ title, description, link, icon }) => {
  return (
    <Link to={link}>
      <div className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow cursor-pointer">
        <div className="text-4xl mb-4">{icon}</div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600">{description}</p>
      </div>
    </Link>
  );
};

export default App;
