import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 600000,  // 10 minutes — pipeline makes 4 sequential LLM calls
});

export const verifyClaim = async (claim) => {
  const res = await api.post('/api/verify', { claim });
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

export default api;
