// frontend/src/pages/Rehabilitation.jsx

import React, { useState, useEffect } from 'react';
import BodyPartSelector from '../components/BodyPartSelector';
import ExerciseCard from '../components/ExerciseCard';
import { getAIRecommendation, getUserRehabHistory, markExerciseCompleted } from '../api/rehabilitation';
import './Rehabilitation.css';

const Rehabilitation = () => {
  // 상태 관리
  const [currentUserId] = useState(1); // 실제로는 로그인된 사용자 ID 사용
  const [selectedPart, setSelectedPart] = useState(null);
  const [severity, setSeverity] = useState(5);
  const [painDescription, setPainDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [rehabHistory, setRehabHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('recommend'); // 'recommend' or 'history'

  // 재활 기록 불러오기
  useEffect(() => {
    if (activeTab === 'history') {
      loadRehabHistory();
    }
  }, [activeTab]);

  const loadRehabHistory = async () => {
    try {
      const data = await getUserRehabHistory(currentUserId);
      setRehabHistory(data.records);
    } catch (error) {
      console.error('기록 로드 실패:', error);
    }
  };

  // AI 추천 받기
  const handleGetRecommendation = async () => {
    if (!selectedPart) {
      alert('통증 부위를 선택해주세요.');
      return;
    }

    setIsLoading(true);
    try {
      const result = await getAIRecommendation(
        currentUserId,
        selectedPart,
        severity,
        painDescription || null
      );
      setRecommendation(result);
    } catch (error) {
      alert('AI 추천을 받는 중 오류가 발생했습니다.');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  // 운동 완료 처리
  const handleExerciseComplete = async (exercise) => {
    const notes = prompt('운동 후 느낌을 간단히 적어주세요 (선택사항):');
    // 실제로는 현재 추천의 record_id를 사용해야 함
    alert(`"${exercise.name}" 완료 처리되었습니다! 🎉`);
  };

  // 통증 강도 슬라이더 라벨
  const getSeverityLabel = (value) => {
    if (value <= 3) return '경미함';
    if (value <= 6) return '보통';
    if (value <= 8) return '심함';
    return '매우 심함';
  };

  return (
    <div className="rehabilitation-page">
      <div className="page-container">
        {/* 헤더 */}
        <header className="page-header">
          <h1 className="page-title">🏥 AI 재활 운동 추천</h1>
          <p className="page-subtitle">
            당신의 통증에 맞는 맞춤형 재활 운동을 AI가 추천해드립니다
          </p>
        </header>

        {/* 탭 네비게이션 */}
        <div className="tab-navigation">
          <button
            className={`tab-button ${activeTab === 'recommend' ? 'active' : ''}`}
            onClick={() => setActiveTab('recommend')}
          >
            🤖 AI 추천받기
          </button>
          <button
            className={`tab-button ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📊 내 기록
          </button>
        </div>

        {/* 추천받기 탭 */}
        {activeTab === 'recommend' && (
          <div className="recommend-section">
            {/* 통증 부위 선택 */}
            <BodyPartSelector 
              selectedPart={selectedPart}
              onSelect={setSelectedPart}
            />

            {/* 통증 강도 슬라이더 */}
            <div className="severity-selector">
              <h3 className="section-title">통증 강도를 선택하세요</h3>
              <div className="severity-slider-container">
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={severity}
                  onChange={(e) => setSeverity(Number(e.target.value))}
                  className="severity-slider"
                />
                <div className="severity-display">
                  <span className="severity-value">{severity}</span>
                  <span className="severity-label">{getSeverityLabel(severity)}</span>
                </div>
              </div>
            </div>

            {/* 추가 설명 (선택사항) */}
            <div className="description-input">
              <h3 className="section-title">추가 설명 (선택사항)</h3>
              <textarea
                className="pain-description-textarea"
                placeholder="예: 마우스 사용 후 시큰거림, 아침에 일어날 때 특히 아픔 등"
                value={painDescription}
                onChange={(e) => setPainDescription(e.target.value)}
                rows="3"
              />
            </div>

            {/* AI 추천 버튼 */}
            <button
              className="btn-get-recommendation"
              onClick={handleGetRecommendation}
              disabled={isLoading || !selectedPart}
            >
              {isLoading ? (
                <>
                  <span className="spinner"></span>
                  AI가 분석 중입니다...
                </>
              ) : (
                <>
                  🤖 AI 추천 받기
                </>
              )}
            </button>

            {/* AI 추천 결과 */}
            {recommendation && (
              <div className="recommendation-result">
                <div className="result-header">
                  <h2>💡 AI 추천 결과</h2>
                  <div className="result-meta">
                    <span className="meta-item">
                      📍 {recommendation.pain_area}
                    </span>
                    <span className="meta-item">
                      ⏱️ 약 {recommendation.estimated_duration_minutes}분 소요
                    </span>
                  </div>
                </div>

                {/* 전체 조언 */}
                <div className="general-advice">
                  <h3>📋 재활 가이드</h3>
                  <p>{recommendation.general_advice}</p>
                </div>

                {/* 추천 운동 목록 */}
                <div className="exercises-list">
                  <h3>🎯 추천 운동</h3>
                  {recommendation.exercises.map((exercise, index) => (
                    <ExerciseCard
                      key={index}
                      exercise={exercise}
                      index={index}
                      onComplete={handleExerciseComplete}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 기록 탭 */}
        {activeTab === 'history' && (
          <div className="history-section">
            <h2>📊 내 재활 운동 기록</h2>
            {rehabHistory.length === 0 ? (
              <div className="empty-history">
                <p>아직 재활 운동 기록이 없습니다.</p>
                <p>AI 추천을 받아 운동을 시작해보세요!</p>
              </div>
            ) : (
              <div className="history-list">
                {rehabHistory.map((record) => (
                  <div key={record.id} className="history-item">
                    <div className="history-header">
                      <span className="history-date">
                        {new Date(record.created_at).toLocaleDateString('ko-KR')}
                      </span>
                      <span className={`history-status ${record.completed ? 'completed' : 'pending'}`}>
                        {record.completed ? '✅ 완료' : '⏳ 진행중'}
                      </span>
                    </div>
                    <div className="history-content">
                      <strong>{record.pain_area}</strong> - 통증 강도: {record.severity}/10
                      <div className="history-exercises">
                        {record.recommended_exercises.length}개 운동 추천받음
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Rehabilitation;
