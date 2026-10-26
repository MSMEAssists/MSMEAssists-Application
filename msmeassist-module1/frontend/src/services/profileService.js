import apiClient from "./apiClient";

export async function getMyProfile() {
  const { data } = await apiClient.get("/profile/me");
  return data;
}

/** Returns null instead of throwing when no profile exists yet (404) — callers use this to route to onboarding vs. dashboard without try/catch boilerplate everywhere. */
export async function getMyProfileOrNull() {
  try {
    return await getMyProfile();
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

export async function createProfile(sectionPayload) {
  const { data } = await apiClient.post("/profile/me", sectionPayload);
  return data;
}

export async function updateProfile(sectionPayload) {
  const { data } = await apiClient.put("/profile/me", sectionPayload);
  return data;
}

export async function getCompleteness() {
  const { data } = await apiClient.get("/profile/completeness");
  return data;
}

export async function getEligibility() {
  const { data } = await apiClient.get("/profile/eligibility");
  return data;
}
