// frontend/src/components/ExerciseComparison.jsx

import React, { useRef, useState, useEffect } from 'react';
import axios from 'axios';

const ExerciseComparison = ({ exerciseId }) => {
  const userVideoRef = useRef(null);
  const referenceVideoRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [stream, setStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordedChunks, setRecordedChunks] = useState([]);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [realtimeFeedback, setRealtimeFeedback] = useState(null);

  // 웹캠 시작
  const startWebcam = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      
      if (userVideoRef.current) {
        userVideoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
      }
    } catch (error) {
      console.error('웹캠 오류:', error);
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

  // 녹화 시작
  const startRecording = () => {
    if (!stream) {
      alert('먼저 웹캠을 시작하세요.');
      return;
    }

    const chunks = [];
    const recorder = new MediaRecorder(stream, {
      mimeType: 'video/webm'
    });

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    recorder.onstop = () => {
      setRecordedChunks(chunks);
    };

    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);

    // 참조 영상도 동시에 재생 (플레이스홀더)
    if (referenceVideoRef.current) {
      // TODO: 실제 참조 영상 URL로 교체
      // referenceVideoRef.current.play();
    }
  };

  // 녹화 중지
  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  // 비교 분석
  const analyzeComparison = async () => {
    if (recordedChunks.length === 0) {
      alert('먼저 운동을 녹화하세요.');
      return;
    }

    setAnalyzing(true);

    try {
      // 녹화된 영상을 Blob으로 변환
      const blob = new Blob(recordedChunks, { type: 'video/webm' });
      
      const formData = new FormData();
      formData.append('user_video', blob, 'user_exercise.webm');
      formData.append('exercise_id', exerciseId);
      formData.append('sample_rate', '5');

      const response = await axios.post(
        'http://localhost:8000/api/pose-comparison/compare',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      setComparisonResult(response.data);
    } catch (error) {
      console.error('분석 오류:', error);
      
      // 참조 데이터가 없는 경우
      if (error.response?.data?.note) {
        alert(error.response.data.message + '\n\n' + error.response.data.note);
      } else {
        alert('분석 중 오류가 발생했습니다.');
      }
    } finally {
      setAnalyzing(false);
    }
  };

  // 실시간 프레임 체크 (선택적 기능)
  const checkRealtimeFrame = async () => {
    if (!userVideoRef.current || !stream) return;

    const canvas = canvasRef.current;
    const video = userVideoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      try {
        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');
        formData.append('exercise_id', exerciseId);
        formData.append('frame_index', '0'); // TODO: 실제 프레임 인덱스 추적

        const response = await axios.post(
          'http://localhost:8000/api/pose-comparison/realtime-frame-check',
          formData
        );

        setRealtimeFeedback(response.data);
      } catch (error) {
        console.error('실시간 체크 오류:', error);
      }
    }, 'image/jpeg');
  };

  // 주기적 실시간 체크 (1초마다)
  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(checkRealtimeFrame, 1000);
      return () => clearInterval(interval);
    }
  }, [isRecording]);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => stopWebcam();
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h2 className="text-3xl font-bold mb-6 text-gray-800">
        🎯 운동 자세 비교 분석
      </h2>

      {/* 안내 메시지 */}
      <div className="mb-6 bg-blue-50 border-l-4 border-blue-500 p-4">
        <h3 className="font-semibold text-blue-900 mb-2">
          💡 시스템 개발 현황
        </h3>
        <p className="text-sm text-blue-800">
          현재는 시스템 아키텍처 검증 단계입니다. 
          <strong> 추후 실제 헬스케어 전문가 시연 영상</strong>을 활용하여 
          정확한 자세 비교가 가능해질 예정입니다.
        </p>
      </div>

      {/* 제어 버튼 */}
      <div className="flex gap-4 mb-6">
        {!stream ? (
          <button
            onClick={startWebcam}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
          >
            웹캠 시작
          </button>
        ) : (
          <>
            {!isRecording ? (
              <button
                onClick={startRecording}
                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold"
              >
                🔴 녹화 시작
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold animate-pulse"
              >
                ⏹ 녹화 중지
              </button>
            )}
            
            {recordedChunks.length > 0 && (
              <button
                onClick={analyzeComparison}
                disabled={analyzing}
                className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-semibold disabled:bg-gray-400"
              >
                {analyzing ? '분석 중...' : '📊 자세 비교 분석'}
              </button>
            )}
            
            <button
              onClick={stopWebcam}
              className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-semibold"
            >
              웹캠 중지
            </button>
          </>
        )}
      </div>

      {/* 영상 비교 화면 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* 참조 영상 (플레이스홀더) */}
        <div className="bg-gray-100 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3 text-gray-800">
            📹 참조 영상 (전문가 시연)
          </h3>
          <div className="bg-gray-300 aspect-video rounded-lg flex items-center justify-center">
            <div className="text-center text-gray-600">
              <p className="text-2xl mb-2">🎬</p>
              <p className="font-semibold">참조 영상 준비 중</p>
              <p className="text-sm mt-2">
                실제 헬스케어 데이터로<br/>
                업데이트 예정
              </p>
            </div>
          </div>
          {/* 
          <video
            ref={referenceVideoRef}
            className="w-full rounded-lg"
            controls
          >
            <source src="placeholder_for_future_video" type="video/mp4" />
          </video>
          */}
        </div>

        {/* 사용자 웹캠 */}
        <div className="bg-white rounded-lg p-4 shadow-lg">
          <h3 className="text-lg font-semibold mb-3 text-gray-800">
            👤 내 동작
          </h3>
          <div className="relative">
            <video
              ref={userVideoRef}
              autoPlay
              playsInline
              muted
              className="w-full rounded-lg border-2 border-blue-500"
            />
            
            {/* 실시간 피드백 오버레이 */}
            {isRecording && realtimeFeedback && realtimeFeedback.success && (
              <div className="absolute top-4 right-4 bg-black bg-opacity-70 text-white px-4 py-2 rounded-lg">
                <div className="flex items-center gap-2">
                  <div 
                    className={`w-3 h-3 rounded-full ${
                      realtimeFeedback.color === 'green' ? 'bg-green-500' :
                      realtimeFeedback.color === 'yellow' ? 'bg-yellow-500' :
                      realtimeFeedback.color === 'orange' ? 'bg-orange-500' :
                      'bg-red-500'
                    }`}
                  />
                  <span className="font-semibold">
                    {realtimeFeedback.similarity_score}점
                  </span>
                </div>
                <p className="text-sm mt-1">{realtimeFeedback.feedback}</p>
              </div>
            )}

            {isRecording && (
              <div className="absolute top-4 left-4 bg-red-600 text-white px-3 py-1 rounded-full text-sm font-semibold animate-pulse">
                🔴 REC
              </div>
            )}
          </div>
          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
      </div>

      {/* 비교 결과 */}
      {comparisonResult && comparisonResult.success && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-2xl font-bold mb-6 text-gray-800">
            📊 분석 결과
          </h3>

          {/* 전체 유사도 점수 */}
          <div className="mb-8">
            <div className="flex justify-between items-center mb-2">
              <span className="text-lg font-semibold">전체 유사도</span>
              <span className={`text-4xl font-bold ${
                comparisonResult.overall_similarity >= 85 ? 'text-green-600' :
                comparisonResult.overall_similarity >= 70 ? 'text-yellow-600' :
                comparisonResult.overall_similarity >= 50 ? 'text-orange-600' :
                'text-red-600'
              }`}>
                {comparisonResult.overall_similarity}점
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className={`h-4 rounded-full transition-all ${
                  comparisonResult.overall_similarity >= 85 ? 'bg-green-600' :
                  comparisonResult.overall_similarity >= 70 ? 'bg-yellow-600' :
                  comparisonResult.overall_similarity >= 50 ? 'bg-orange-600' :
                  'bg-red-600'
                }`}
                style={{ width: `${comparisonResult.overall_similarity}%` }}
              />
            </div>
          </div>

          {/* 피드백 */}
          <div className="bg-blue-50 rounded-lg p-5 mb-6">
            <h4 className="font-semibold text-blue-900 mb-3 text-lg">
              💬 피드백
            </h4>
            <ul className="space-y-2">
              {comparisonResult.feedback.map((fb, index) => (
                <li key={index} className="text-blue-800 flex items-start">
                  <span className="mr-2">•</span>
                  <span>{fb}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 속도 정보 */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">운동 속도</p>
              <p className="text-2xl font-bold text-gray-800">
                {comparisonResult.speed_ratio?.toFixed(2)}x
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {comparisonResult.speed_ratio > 1.3 ? '너무 느림' :
                 comparisonResult.speed_ratio < 0.7 ? '너무 빠름' : '적절'}
              </p>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">DTW 거리</p>
              <p className="text-2xl font-bold text-gray-800">
                {comparisonResult.dtw_distance?.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                낮을수록 유사함
              </p>
            </div>
          </div>

          {/* 프레임별 유사도 그래프 (간단한 시각화) */}
          {comparisonResult.frame_similarities && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-semibold text-gray-800 mb-3">
                시간별 유사도 변화
              </h4>
              <div className="flex items-end gap-1 h-32">
                {comparisonResult.frame_similarities.map((sim, index) => (
                  <div
                    key={index}
                    className={`flex-1 rounded-t ${
                      sim >= 0.85 ? 'bg-green-500' :
                      sim >= 0.70 ? 'bg-yellow-500' :
                      sim >= 0.50 ? 'bg-orange-500' :
                      'bg-red-500'
                    }`}
                    style={{ height: `${sim * 100}%` }}
                    title={`프레임 ${index}: ${(sim * 100).toFixed(1)}%`}
                  />
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-2 text-center">
                각 막대는 시간 구간별 자세 정확도를 나타냅니다
              </p>
            </div>
          )}
        </div>
      )}

      {/* 참조 데이터 없음 메시지 */}
      {comparisonResult && !comparisonResult.success && (
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-6 rounded-lg">
          <h4 className="font-semibold text-yellow-900 mb-2">
            ⚠️ {comparisonResult.message}
          </h4>
          {comparisonResult.note && (
            <p className="text-sm text-yellow-800">{comparisonResult.note}</p>
          )}
        </div>
      )}

      {/* 사용 가이드 */}
      <div className="mt-6 bg-green-50 p-4 rounded-lg">
        <h3 className="font-semibold text-green-900 mb-2">
          📖 사용 방법
        </h3>
        <ol className="text-sm text-green-800 space-y-1 list-decimal list-inside">
          <li>웹캠을 시작하고 전신이 보이도록 위치를 조정하세요</li>
          <li>녹화 시작 버튼을 누르고 운동을 수행하세요</li>
          <li>운동이 끝나면 녹화 중지를 누르세요</li>
          <li>'자세 비교 분석' 버튼으로 결과를 확인하세요</li>
          <li>피드백을 참고하여 자세를 개선하세요</li>
        </ol>
      </div>
    </div>
  );
};

export default ExerciseComparison;
