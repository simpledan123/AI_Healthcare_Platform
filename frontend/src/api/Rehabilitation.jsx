// frontend/src/api/rehabilitation.js

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/**
 * AI 운동 추천 받기
 */
export const getAIRecommendation = async (userId, painArea, severity, painDescription) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/rehabilitation/recommend`, {
      user_id: userId,
      pain_area: painArea,
      severity: severity,
      pain_description: painDescription
    });
    return response.data;
  } catch (error) {
    console.error('AI 추천 오류:', error);
    throw error;
  }
};

/**
 * 사용자 재활 기록 조회
 */
export const getUserRehabHistory = async (userId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/rehabilitation/history/${userId}`);
    return response.data;
  } catch (error) {
    console.error('기록 조회 오류:', error);
    return { records: [] };
  }
};

/**
 * 운동 완료 표시
 */
export const markExerciseCompleted = async (recordId, exerciseId, notes) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/api/rehabilitation/complete/${recordId}/${exerciseId}`,
      { notes }
    );
    return response.data;
  } catch (error) {
    console.error('완료 표시 오류:', error);
    throw error;
  }
};