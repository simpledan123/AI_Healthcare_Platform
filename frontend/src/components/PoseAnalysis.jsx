// frontend/src/components/PoseAnalysis.jsx

import React, { useRef, useState, useEffect } from 'react';
import axios from 'axios';

const PoseAnalysis = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [selectedExercise, setSelectedExercise] = useState('general');

  // 웹캠 시작
  const startWebcam = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
      }
    } catch (error) {
      console.error('웹캠 접근 오류:', error);
      alert('웹캠 접근 권한이 필요합니다.');
    }
  };

  // 웹캠 중지
  const stopWebcam = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  // 자세 분석
  const analyzeFrame = async () => {
    if (!videoRef.current) return;

    setAnalyzing(true);

    // 캔버스에 현재 프레임 캡처
    const canvas = canvasRef.current;
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    // 이미지를 Blob으로 변환
    canvas.toBlob(async (blob) => {
      try {
        const formData = new FormData();
        formData.append('file', blob, 'frame.jpg');

        const endpoint = selectedExercise === 'general' 
          ? '/api/pose/analyze'
          : `/api/pose/analyze-exercise?exercise_type=${selectedExercise}`;

        const response = await axios.post(
          `http://localhost:8000${endpoint}`,
          formData,
          {
            headers: { 'Content-Type': 'multipart/form-data' }
          }
        );

        setResult(response.data);
      } catch (error) {
        console.error('자세 분석 오류:', error);
        alert('자세 분석 중 오류가 발생했습니다.');
      } finally {
        setAnalyzing(false);
      }
    }, 'image/jpeg');
  };

  // 컴포넌트 언마운트 시 웹캠 중지
  useEffect(() => {
    return () => stopWebcam();
  }, []);

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        🎥 실시간 자세 분석
      </h2>

      {/* 운동 타입 선택 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          운동 종류 선택
        </label>
        <select
          value={selectedExercise}
          onChange={(e) => setSelectedExercise(e.target.value)}
          className="w-full p-2 border border-gray-300 rounded-md"
        >
          <option value="general">일반 자세</option>
          <option value="stretch">스트레칭</option>
          <option value="squat">스쿼트</option>
          <option value="plank">플랭크</option>
        </select>
      </div>

      {/* 웹캠 제어 버튼 */}
      <div className="flex gap-4 mb-6">
        {!stream ? (
          <button
            onClick={startWebcam}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            웹캠 시작
          </button>
        ) : (
          <>
            <button
              onClick={analyzeFrame}
              disabled={analyzing}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
            >
              {analyzing ? '분석 중...' : '자세 분석'}
            </button>
            <button
              onClick={stopWebcam}
              className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            >
              웹캠 중지
            </button>
          </>
        )}
      </div>

      {/* 비디오 스트림 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-2">실시간 영상</h3>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="w-full rounded-lg border-2 border-gray-300"
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>

        {/* 분석 결과 */}
        {result && result.success && (
          <div>
            <h3 className="text-lg font-semibold mb-2">분석 결과</h3>
            <img
              src={result.annotated_image}
              alt="분석된 자세"
              className="w-full rounded-lg border-2 border-green-500 mb-4"
            />

            {/* 자세 점수 */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium">자세 점수</span>
                <span className={`text-2xl font-bold ${
                  result.pose_score >= 80 ? 'text-green-600' :
                  result.pose_score >= 60 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {result.pose_score}/100
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className={`h-3 rounded-full ${
                    result.pose_score >= 80 ? 'bg-green-600' :
                    result.pose_score >= 60 ? 'bg-yellow-600' :
                    'bg-red-600'
                  }`}
                  style={{ width: `${result.pose_score}%` }}
                />
              </div>
            </div>

            {/* 피드백 */}
            <div className="bg-blue-50 p-4 rounded-lg mb-4">
              <h4 className="font-semibold mb-2 text-blue-900">자세 피드백</h4>
              <ul className="space-y-2">
                {result.feedback.map((feedback, index) => (
                  <li key={index} className="text-sm text-blue-800">
                    {feedback}
                  </li>
                ))}
              </ul>
            </div>

            {/* 운동별 추가 피드백 */}
            {result.exercise_feedback && (
              <div className="bg-purple-50 p-4 rounded-lg">
                <h4 className="font-semibold mb-2 text-purple-900">
                  {selectedExercise} 특화 피드백
                </h4>
                <ul className="space-y-2">
                  {result.exercise_feedback.map((feedback, index) => (
                    <li key={index} className="text-sm text-purple-800">
                      {feedback}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 관절 각도 (디버깅용) */}
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-800">
                상세 각도 정보 보기
              </summary>
              <div className="mt-2 text-xs text-gray-700 bg-gray-50 p-3 rounded">
                <pre>{JSON.stringify(result.angles, null, 2)}</pre>
              </div>
            </details>
          </div>
        )}

        {/* 실패 메시지 */}
        {result && !result.success && (
          <div className="bg-red-50 p-4 rounded-lg">
            <p className="text-red-800">{result.message}</p>
          </div>
        )}
      </div>

      {/* 사용 팁 */}
      <div className="mt-6 bg-yellow-50 p-4 rounded-lg">
        <h3 className="font-semibold text-yellow-900 mb-2">💡 사용 팁</h3>
        <ul className="text-sm text-yellow-800 space-y-1">
          <li>• 전신이 프레임에 들어오도록 카메라를 조정하세요</li>
          <li>• 밝은 곳에서 촬영하면 정확도가 높아집니다</li>
          <li>• 운동 동작을 천천히 수행하며 분석해보세요</li>
          <li>• 정기적으로 자세를 체크하여 개선하세요</li>
        </ul>
      </div>
    </div>
  );
};

export default PoseAnalysis;
