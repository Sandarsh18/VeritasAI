import axios from "axios";

// VITE_API_BASE_URL resolution:
// - Local dev (no Docker): "http://localhost:8000" (set in .env)
// - Docker Compose: "" (empty) -> requests use same-origin relative paths
//   like "/api/verify", which nginx proxies to the backend container.
// The `?? ` operator preserves an intentional empty string for Docker.
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL: apiBaseUrl,
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
  console.log("[UI Debug] /api/verify response", {
    keys: Object.keys(data || {}),
    evidenceCount: Array.isArray(data?.evidence) ? data.evidence.length : 0,
    prosecutorArgs: Array.isArray(data?.prosecutor?.arguments)
      ? data.prosecutor.arguments.length
      : 0,
    defenderArgs: Array.isArray(data?.defender?.arguments)
      ? data.defender.arguments.length
      : 0,
    pipelineWarning: data?.pipeline_warning || "",
  });
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

export const deleteHistoryClaim = async (historyId, token) => {
  const resolvedToken =
    token ||
    localStorage.getItem("veritas-token") ||
    sessionStorage.getItem("veritas-token") ||
    null;

  const headers = {};
  if (resolvedToken) {
    headers.Authorization = `Bearer ${resolvedToken}`;
  }

  const { data } = await api.delete(`/api/claims/${historyId}`, { headers });
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

export const exportPdf = async (historyId) => {
  try {
    const response = await api.get(`/api/export/pdf/${historyId}`, {
      responseType: "blob",
    });
    return response.data;
  } catch (error) {
    if (error?.response?.status !== 404) throw error;
    const response = await api.get(`/api/claims/history/${historyId}/export`, {
      responseType: "blob",
    });
    return response.data;
  }
};

export default api;
