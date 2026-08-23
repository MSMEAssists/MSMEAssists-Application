import { useOnboarding } from "../context/OnboardingContext";

export function useProfile() {
  const { profile, isLoading, isSaving, loadError, hasProfile, saveSection, reload } = useOnboarding();
  return { profile, isLoading, isSaving, loadError, hasProfile, saveSection, reload };
}
