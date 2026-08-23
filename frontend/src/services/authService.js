import apiClient, { TOKEN_STORAGE_KEY } from "./apiClient";

export async function register({ fullName, email, mobileNumber, password, confirmPassword }) {
  const { data } = await apiClient.post("/auth/register", {
    full_name: fullName,
    email,
    mobile_number: mobileNumber,
    password,
    confirm_password: confirmPassword,
  });
  localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
  return data;
}

export async function login({ email, password }) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
  return data;
}

export async function getCurrentUser() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export function logout() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function hasStoredToken() {
  return Boolean(localStorage.getItem(TOKEN_STORAGE_KEY));
}
