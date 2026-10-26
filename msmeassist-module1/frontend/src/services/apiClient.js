import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export const TOKEN_STORAGE_KEY = "msmeassist_access_token";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Normalizes every backend error into { code, message, field, status }
// matching the envelope documented in docs/module-1-api.md:
//   { "error": { "code": "...", "message": "...", "field": "..." } }
function normalizeError(error) {
  if (error.response) {
    const { status, data } = error.response;
    const envelope = data?.error;
    if (envelope) {
      return { status, code: envelope.code, message: envelope.message, field: envelope.field ?? null };
    }
    return { status, code: "UNKNOWN_ERROR", message: "Something went wrong. Please try again.", field: null };
  }
  if (error.request) {
    return {
      status: 0,
      code: "NETWORK_ERROR",
      message: "Could not reach the MSMEAssist server. Check your connection and try again.",
      field: null,
    };
  }
  return { status: 0, code: "CLIENT_ERROR", message: error.message, field: null };
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = normalizeError(error);

    // A 401 anywhere except the auth endpoints themselves means the stored
    // token is dead — clear it so ProtectedRoute sends the user back to
    // /login instead of looping on failed requests.
    const isAuthEndpoint = error.config?.url?.includes("/auth/login") || error.config?.url?.includes("/auth/register");
    if (normalized.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(normalized);
  }
);

export default apiClient;
