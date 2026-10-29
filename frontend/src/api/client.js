const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:18080';

export async function fetchStats() {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchMessages({
  limit = 100,
  risk_level,
  classification,
  ai_status,
  local_category,
  review_status,
  needs_review,
  has_link,
  min_risk,
} = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  if (risk_level) params.set('risk_level', risk_level);
  if (classification) params.set('classification', classification);
  if (ai_status) params.set('ai_status', ai_status);
  if (local_category) params.set('local_category', local_category);
  if (review_status) params.set('review_status', review_status);
  if (needs_review) params.set('needs_review', needs_review);
  if (has_link !== undefined && has_link !== null) params.set('has_link', has_link);
  if (min_risk !== undefined && min_risk !== null && min_risk !== '') params.set('min_risk', min_risk);
  const res = await fetch(`${BASE_URL}/messages?${params}`);
  if (!res.ok) throw new Error('Failed to fetch messages');
  return res.json();
}

export async function fetchAiStatus() {
  const res = await fetch(`${BASE_URL}/ai/status`);
  if (!res.ok) throw new Error('Failed to fetch AI status');
  return res.json();
}

export async function fetchMessageAiAnalysis(messageId) {
  const res = await fetch(`${BASE_URL}/messages/${messageId}/ai-analysis`);
  if (!res.ok) throw new Error('Failed to fetch AI analysis');
  return res.json();
}

export async function reanalyzeMessageAi(messageId) {
  const res = await fetch(`${BASE_URL}/messages/${messageId}/reanalyze-ai`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reanalyze message with AI');
  return res.json();
}

export async function reanalyzeAiCandidates(limit = 50) {
  const res = await fetch(`${BASE_URL}/ai/reanalyze-candidates?limit=${limit}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reanalyze AI candidates');
  return res.json();
}

export async function backfillLocal(limit = 500) {
  const res = await fetch(`${BASE_URL}/maintenance/backfill-local?limit=${limit}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to run local backfill');
  return res.json();
}

export async function fetchMessageDetail(messageId) {
  const res = await fetch(`${BASE_URL}/messages/${messageId}`);
  if (!res.ok) throw new Error('Failed to fetch message detail');
  return res.json();
}

export async function updateMessageReview(messageId, status, note = '') {
  const params = new URLSearchParams();
  params.set('status', status);
  if (note) params.set('note', note);
  const res = await fetch(`${BASE_URL}/messages/${messageId}/review?${params}`, {
    method: 'PATCH',
  });
  if (!res.ok) throw new Error('Failed to update review status');
  return res.json();
}

export async function fetchAlerts({ limit = 100, resolved } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  if (resolved !== undefined && resolved !== null) {
    params.set('resolved', resolved);
  }
  const res = await fetch(`${BASE_URL}/alerts?${params}`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
}

export async function resolveAlert(alertId) {
  const res = await fetch(`${BASE_URL}/alerts/${alertId}/resolve`, {
    method: 'PATCH',
  });
  if (!res.ok) throw new Error('Failed to resolve alert');
  return res.json();
}

export async function fetchSimilar(messageId, limit = 10) {
  const params = new URLSearchParams();
  params.set('message_id', messageId);
  params.set('limit', limit);
  const res = await fetch(`${BASE_URL}/similar?${params}`);
  if (!res.ok) throw new Error('Failed to fetch similar messages');
  return res.json();
}

export async function fetchGraph() {
  const res = await fetch(`${BASE_URL}/graph`);
  if (!res.ok) throw new Error('Failed to fetch graph');
  return res.json();
}

export async function fetchUsers({ search, limit = 100 } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  if (search) params.set('search', search);
  const res = await fetch(`${BASE_URL}/users?${params}`);
  if (!res.ok) throw new Error('Failed to fetch users');
  return res.json();
}

export async function fetchUser(userId) {
  const res = await fetch(`${BASE_URL}/user/${userId}`);
  if (!res.ok) throw new Error('Failed to fetch user profile');
  return res.json();
}

export async function fetchUserMessages(userId, { type, chat_id, limit = 100 } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  if (type) params.set('type', type);
  if (chat_id) params.set('chat_id', chat_id);
  const res = await fetch(`${BASE_URL}/user/${userId}/messages?${params}`);
  if (!res.ok) throw new Error('Failed to fetch user messages');
  return res.json();
}
