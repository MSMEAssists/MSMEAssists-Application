import { useNavigate } from "react-router-dom";
import Button from "../ui/Button";
import { WIZARD_STEPS } from "../../utils/constants";
import { FiArrowLeft, FiArrowRight, FiSave } from "react-icons/fi";

export default function WizardNav({ stepKey, onSaveAndExit, isSaving, continueLabel }) {
  const navigate = useNavigate();
  const currentIndex = WIZARD_STEPS.findIndex((s) => s.key === stepKey);
  const prevStep = WIZARD_STEPS[currentIndex - 1];
  const isLastStep = stepKey === "review";

  return (
    <div className="mt-10 flex items-center justify-between border-t border-border pt-6">
      {prevStep ? (
        <Button
          variant="secondary"
          size="md"
          type="button"
          onClick={() => navigate(`/onboarding/${prevStep.key}`)}
          className="flex items-center gap-1.5 font-semibold text-slate-dark"
        >
          <FiArrowLeft size={15} />
          <span>Back</span>
        </Button>
      ) : (
        <div />
      )}

      <div className="flex items-center gap-3">
        {onSaveAndExit && (
          <Button
            variant="ghost"
            size="md"
            type="button"
            isLoading={isSaving}
            onClick={onSaveAndExit}
            className="text-xs font-semibold text-slate-text hover:text-charcoal"
          >
            <FiSave size={14} className="text-burnt-orange" />
            <span>Save Draft</span>
          </Button>
        )}

        <Button
          type="submit"
          variant="primary"
          size="md"
          isLoading={isSaving}
          className="flex items-center gap-2 font-bold px-6 shadow-sm"
        >
          <span>{continueLabel || (isLastStep ? "Submit & View Matches" : "Next")}</span>
          <FiArrowRight size={15} />
        </Button>
      </div>
    </div>
  );
}
