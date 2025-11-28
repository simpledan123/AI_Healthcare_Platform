// frontend/src/components/CommunityFeed.jsx

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const CommunityFeed = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    pain_area: '',
    exercise_type: '',
    sort_by: 'recent'
  });
  const [showCreateModal, setShowCreateModal] = useState(false);

  // 게시글 목록 불러오기
  const fetchPosts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.pain_area) params.append('pain_area', filters.pain_area);
      if (filters.exercise_type) params.append('exercise_type', filters.exercise_type);
      params.append('sort_by', filters.sort_by);

      const response = await axios.get(
        `http://localhost:8000/api/community/posts?${params.toString()}`
      );
      setPosts(response.data.posts);
    } catch (error) {
      console.error('게시글 불러오기 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, [filters]);

  // 좋아요 토글
  const toggleLike = async (postId) => {
    try {
      const userId = localStorage.getItem('user_id'); // 실제 인증 시스템과 연동
      await axios.post(`http://localhost:8000/api/community/posts/${postId}/like`, {
        user_id: userId
      });
      fetchPosts(); // 목록 새로고침
    } catch (error) {
      console.error('좋아요 오류:', error);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">💬 커뮤니티</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + 게시글 작성
        </button>
      </div>

      {/* 필터 */}
      <div className="bg-white p-4 rounded-lg shadow mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            부위별 필터
          </label>
          <select
            value={filters.pain_area}
            onChange={(e) => setFilters({...filters, pain_area: e.target.value})}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="">전체</option>
            <option value="손목">손목</option>
            <option value="어깨">어깨</option>
            <option value="허리">허리</option>
            <option value="무릎">무릎</option>
            <option value="목">목</option>
            <option value="발목">발목</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            운동 타입
          </label>
          <select
            value={filters.exercise_type}
            onChange={(e) => setFilters({...filters, exercise_type: e.target.value})}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="">전체</option>
            <option value="ai_recommended">AI 추천</option>
            <option value="self_created">내가 찾은 방법</option>
            <option value="mixed">혼합</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            정렬
          </label>
          <select
            value={filters.sort_by}
            onChange={(e) => setFilters({...filters, sort_by: e.target.value})}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="recent">최신순</option>
            <option value="popular">인기순</option>
            <option value="effective">효과순</option>
          </select>
        </div>
      </div>

      {/* 게시글 목록 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
          <p className="mt-2 text-gray-600">로딩 중...</p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} onLike={toggleLike} />
          ))}

          {posts.length === 0 && (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <p className="text-gray-600">게시글이 없습니다.</p>
              <p className="text-sm text-gray-500 mt-2">
                첫 번째 경험을 공유해보세요!
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// 개별 게시글 카드 컴포넌트
const PostCard = ({ post, onLike }) => {
  const getExerciseTypeLabel = (type) => {
    const labels = {
      'ai_recommended': '🤖 AI 추천',
      'self_created': '💡 내가 찾은 방법',
      'mixed': '🔄 혼합'
    };
    return labels[type] || type;
  };

  const getEffectivenessColor = (rating) => {
    if (rating >= 4.5) return 'text-green-600';
    if (rating >= 3.5) return 'text-yellow-600';
    return 'text-orange-600';
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
      {/* 헤더 */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
            {post.user.username[0].toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-gray-800">{post.user.username}</p>
            <p className="text-xs text-gray-500">
              {new Date(post.created_at).toLocaleDateString('ko-KR')}
            </p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
            {post.pain_area}
          </span>
          <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
            {getExerciseTypeLabel(post.exercise_type)}
          </span>
        </div>
      </div>

      {/* 제목 및 내용 */}
      <h3 className="text-xl font-bold text-gray-800 mb-2">{post.title}</h3>
      <p className="text-gray-600 mb-4 line-clamp-3">{post.content}</p>

      {/* 통계 */}
      <div className="flex items-center gap-6 mb-4 text-sm text-gray-600">
        {post.duration_days && (
          <span>📅 {post.duration_days}일간</span>
        )}
        {post.effectiveness_rating && (
          <span className={`font-semibold ${getEffectivenessColor(post.effectiveness_rating)}`}>
            ⭐ {post.effectiveness_rating.toFixed(1)} 효과
          </span>
        )}
        <span>👁 {post.view_count} 조회</span>
      </div>

      {/* 유튜브 링크 */}
      {post.youtube_links && post.youtube_links.length > 0 && (
        <div className="mb-4 flex gap-2 flex-wrap">
          {post.youtube_links.map((link, index) => (
            <a
              key={index}
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 text-xs rounded-full hover:bg-red-200"
            >
              ▶️ 유튜브 영상 {index + 1}
            </a>
          ))}
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="flex gap-4 pt-4 border-t border-gray-200">
        <button
          onClick={() => onLike(post.id)}
          className="flex items-center gap-2 text-gray-600 hover:text-blue-600"
        >
          <span>👍</span>
          <span className="text-sm">{post.like_count || 0}</span>
        </button>
        <button className="flex items-center gap-2 text-gray-600 hover:text-blue-600">
          <span>💬</span>
          <span className="text-sm">{post.comment_count || 0}</span>
        </button>
        <button className="flex items-center gap-2 text-gray-600 hover:text-blue-600">
          <span>🔗</span>
          <span className="text-sm">공유</span>
        </button>
      </div>
    </div>
  );
};

export default CommunityFeed;
