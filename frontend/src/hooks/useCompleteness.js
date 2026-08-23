import { useOnboarding } from "../context/OnboardingContext";
import { WIZARD_STEPS } from "../utils/constants";

export function useCompleteness() {
  const { completeness } = useOnboarding();
  const sections = completeness.sections || {};
  const completedCount = WIZARD_STEPS.filter((s) => sections[s.key]).length;
  return {
    percentage: completeness.percentage ?? 0,
    sections,
    completedCount,
    totalSections: WIZARD_STEPS.length,
  };
}
