// frontend/src/components/ExerciseCard.jsx

import React, { useState } from 'react';
import './ExerciseCard.css';

const ExerciseCard = ({ exercise, index, onComplete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showVideo, setShowVideo] = useState(false);

  const difficultyColors = {
    '초급': '#4CAF50',
    '중급': '#FF9800',
    '고급': '#F44336'
  };

  // 운동 이름으로 YouTube 검색 URL 생성
  const getYouTubeSearchUrl = () => {
    const searchQuery = encodeURIComponent(`${exercise.name} 운동 방법`);
    return `https://www.youtube.com/results?search_query=${searchQuery}`;
  };

  return (
    <div className={`exercise-card ${isExpanded ? 'expanded' : ''}`}>
      {/* 카드 헤더 */}
      <div className="card-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="header-left">
          <span className="exercise-number">#{index + 1}</span>
          <h3 className="exercise-name">{exercise.name}</h3>
        </div>
        <div className="header-right">
          <span 
            className="difficulty-badge"
            style={{ backgroundColor: difficultyColors[exercise.difficulty] }}
          >
            {exercise.difficulty}
          </span>
          <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {/* 카드 내용 (확장 시 표시) */}
      {isExpanded && (
        <div className="card-content">
          {/* 운동 설명 */}
          <div className="exercise-description">
            <h4>🎯 운동 방법</h4>
            <div className="description-text">
              {exercise.description.split('\n').map((line, idx) => (
                <p key={idx}>{line}</p>
              ))}
            </div>
          </div>

          {/* 운동 정보 */}
          <div className="exercise-info">
            <div className="info-item">
              <span className="info-label">세트</span>
              <span className="info-value">{exercise.sets}세트</span>
            </div>
            <div className="info-item">
              <span className="info-label">횟수</span>
              <span className="info-value">{exercise.reps}회</span>
            </div>
            {exercise.duration_seconds && (
              <div className="info-item">
                <span className="info-label">유지시간</span>
                <span className="info-value">{exercise.duration_seconds}초</span>
              </div>
            )}
          </div>

          {/* 주의사항 */}
          <div className="exercise-cautions">
            <h4>⚠️ 주의사항</h4>
            <ul>
              {exercise.cautions.map((caution, idx) => (
                <li key={idx}>{caution}</li>
              ))}
            </ul>
          </div>

          {/* 액션 버튼 */}
          <div className="card-actions">
            <button 
              className="btn-video"
              onClick={() => window.open(getYouTubeSearchUrl(), '_blank')}
            >
              📹 영상 찾기
            </button>
            <button 
              className="btn-complete"
              onClick={() => onComplete && onComplete(exercise)}
            >
              ✅ 완료 표시
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExerciseCard;
