import { useNavigate } from "react-router-dom";
import Button from "../ui/Button";
import { WIZARD_STEPS } from "../../utils/constants";

/**
 * `type="submit"` on Continue relies on this being rendered inside the
 * step's <form onSubmit={...}>. Save & Exit runs the same save logic via
 * `onSaveAndExit` (passed by the step page) but then leaves the wizard
 * instead of advancing to the next step.
 */
export default function WizardNav({ stepKey, onSaveAndExit, isSaving, continueLabel }) {
  const navigate = useNavigate();
  const currentIndex = WIZARD_STEPS.findIndex((s) => s.key === stepKey);
  const prevStep = WIZARD_STEPS[currentIndex - 1];
  const isLastStep = stepKey === "review";

  return (
    <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
      {prevStep ? (
        <Button variant="ghost" type="button" onClick={() => navigate(`/onboarding/${prevStep.key}`)}>
          ← Back
        </Button>
      ) : (
        <span />
      )}
      <div className="flex gap-2.5">
        <Button variant="ghost" type="button" isLoading={isSaving} onClick={onSaveAndExit}>
          Save &amp; Exit
        </Button>
        <Button type="submit" isLoading={isSaving}>
          {continueLabel || (isLastStep ? "Save Profile" : "Continue →")}
        </Button>
      </div>
    </div>
  );
}
