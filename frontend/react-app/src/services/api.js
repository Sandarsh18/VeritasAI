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

export const getHistoryResponse = async (token) => {
  const resolvedToken =
    token ||
    localStorage.getItem("veritas-token") ||
    sessionStorage.getItem("veritas-token") ||
    null;

  const headers = {};
  if (resolvedToken) {
    headers.Authorization = `Bearer ${resolvedToken}`;
  }

  const { data } = await api.get("/api/claims/history", { headers });

  if (Array.isArray(data)) {
    return {
      claims: data,
      is_authenticated: Boolean(resolvedToken),
      total: data.length,
    };
  }

  return {
    claims: data?.claims || [],
    is_authenticated: Boolean(data?.is_authenticated),
    total: Number(data?.total || 0),
  };
};

export const getHistory = async (token) => {
  const data = await getHistoryResponse(token);
  return data.claims || [];
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
