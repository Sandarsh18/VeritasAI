import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 600000,  // 10 minutes — pipeline makes 4 sequential LLM calls
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('veritasai_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const verifyClaim = async (claim) => {
  const res = await api.post('/api/verify', { claim });
  return res.data;
};

export const suggestClaim = async (input) => {
  const res = await api.post('/api/suggest-claim', { input });
  return res.data;
};

export const getHistory = async () => {
  const res = await api.get('/api/claims/history');
  return res.data;
};

export const getGraphData = async (claimId) => {
  const res = await api.get(`/api/graph/${claimId}`);
  return res.data;
};

export const getStats = async () => {
  const res = await api.get('/api/stats');
  return res.data;
};

export const getHealth = async () => {
  const res = await api.get('/health');
  return res.data;
};

export const getModels = async () => {
  const res = await api.get('/api/models');
  return res.data;
};

export const login = async (credentials) => {
  const res = await api.post('/api/auth/login', credentials);
  return res.data;
};

export const register = async (userData) => {
  const res = await api.post('/api/auth/register', userData);
  return res.data;
};

export const logout = async () => {
  const res = await api.post('/api/auth/logout');
  return res.data;
};

export const getMe = async () => {
  const res = await api.get('/api/auth/me');
  return res.data;
};

export const updateProfile = async (data) => {
  const res = await api.put('/api/auth/profile', data);
  return res.data;
};

export const changePassword = async (data) => {
  const res = await api.post('/api/auth/change-password', data);
  return res.data;
};

export const getUserClaims = async (filters = {}) => {
  const res = await api.get('/api/user/claims', { params: filters });
  return res.data;
};

export const getUserClaimById = async (id) => {
  const res = await api.get(`/api/user/claims/${id}`);
  return res.data;
};

export const bookmarkClaim = async (id) => {
  const res = await api.post(`/api/user/claims/${id}/bookmark`);
  return res.data;
};

export const deleteMyClaim = async (id) => {
  const res = await api.delete(`/api/user/claims/${id}`);
  return res.data;
};

export const getUserStats = async () => {
  const res = await api.get('/api/user/stats');
  return res.data;
};

export const submitFeedback = async (claimId, rating, comment) => {
  const res = await api.post(`/api/feedback/${claimId}`, { rating, comment });
  return res.data;
};

export const getFeedback = async (claimId) => {
  const res = await api.get(`/api/feedback/${claimId}`);
  return res.data;
};

export const shareClaim = async (claimId) => {
  const res = await api.post(`/api/claims/${claimId}/share`);
  return res.data;
};

export const getSharedClaim = async (token) => {
  const res = await api.get(`/api/shared/${token}`);
  return res.data;
};

export const getTrending = async () => {
  const res = await api.get('/api/trending');
  return res.data;
};

export const searchClaims = async (query, filters = {}) => {
  const res = await api.get('/api/search', { params: { q: query, ...filters } });
  return res.data;
};

export const getSources = async () => {
  const res = await api.get('/api/sources');
  return res.data;
};

export const checkUsername = async (username) => {
  const res = await api.get('/api/auth/check-username', { params: { username } });
  return res.data;
};

export default api;
