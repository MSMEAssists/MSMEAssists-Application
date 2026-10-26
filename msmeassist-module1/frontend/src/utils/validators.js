// Mirrors backend/app/utils/validators.py so the wizard can fail fast
// before hitting the API, but the backend is always the source of truth.

export const PIN_CODE_RE = /^\d{6}$/;
export const MOBILE_RE = /^\+91[6-9]\d{9}$/;
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidPinCode(value) {
  return PIN_CODE_RE.test(value || "");
}

export function isValidMobile(value) {
  return MOBILE_RE.test(value || "");
}

export function isValidEmail(value) {
  return EMAIL_RE.test(value || "");
}

export function passwordStrength(value = "") {
  if (!value) return { score: 0, label: "" };
  let score = 0;
  if (value.length >= 8) score += 1;
  if (/[A-Za-z]/.test(value) && /\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value) && value.length >= 10) score += 1;
  const labels = ["Too short", "Weak", "Good", "Strong"];
  return { score, label: labels[score] };
}

export function passwordMeetsMinimum(value = "") {
  return value.length >= 8 && /[A-Za-z]/.test(value) && /\d/.test(value);
}
