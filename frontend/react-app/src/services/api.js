import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 300000,
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

const savedToken = localStorage.getItem("veritas-token");
if (savedToken) {
  setAuthToken(savedToken);
}

export const verifyClaim = async (claim) => {
  const { data } = await api.post("/api/verify", { claim });
  return data;
};

export const getHistory = async () => {
  const { data } = await api.get("/api/claims/history");
  return data;
};

export const getHistoryDetails = async (historyId) => {
  const { data } = await api.get(`/api/claims/history/${historyId}`);
  return data;
};

export const getStats = async () => {
  const { data } = await api.get("/api/stats");
  return data;
};

export const login = async (payload) => {
  const { data } = await api.post("/api/auth/login/", payload);
  return data;
};

export const register = async (payload) => {
  const { data } = await api.post("/api/auth/register/", payload);
  return data;
};

export const getMe = async () => {
  const { data } = await api.get("/api/auth/me/");
  return data;
};

export default api;
