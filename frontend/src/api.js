const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || '요청을 처리하지 못했습니다.');
  }
  return data;
}

export const api = {
  meta: () => request('/api/meta'),
  dashboard: () => request('/api/dashboard'),
  references: () => request('/api/references'),
  reviewTasks: () => request('/api/review-tasks'),
  runDemo: (severity, painDescription) =>
    request(
      `/api/attempts/demo?severity=${severity}&pain_description=${encodeURIComponent(painDescription)}`,
      { method: 'POST' },
    ),
  analyzeVideo: (formData) =>
    request('/api/attempts/analyze', { method: 'POST', body: formData }),
  importReference: (formData) =>
    request('/api/references/import-video', { method: 'POST', body: formData }),
  resolveTask: (id, status, reviewerNote) =>
    request(`/api/review-tasks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, reviewer_note: reviewerNote }),
    }),
};

