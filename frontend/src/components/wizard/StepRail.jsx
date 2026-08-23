import { useNavigate } from "react-router-dom";
import { FiCheck } from "react-icons/fi";
import { WIZARD_STEPS } from "../../utils/constants";
import { useCompleteness } from "../../hooks/useCompleteness";

export default function StepRail({ currentStepKey }) {
  const navigate = useNavigate();
  const { sections } = useCompleteness();

  return (
    <nav className="rounded-lg border border-border bg-white p-2" aria-label="Onboarding steps">
      {WIZARD_STEPS.map((step) => {
        const isCurrent = step.key === currentStepKey;
        const isDone = sections[step.key] && !isCurrent;
        return (
          <button
            key={step.key}
            type="button"
            onClick={() => navigate(`/onboarding/${step.key}`)}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-surface-sunken"
          >
            <span
              className={[
                "flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-full border-[1.5px] font-data text-xs font-bold",
                isDone
                  ? "border-success-600 bg-success-600 text-white"
                  : isCurrent
                  ? "border-navy-900 bg-navy-900 text-white"
                  : "border-border bg-surface-sunken text-ink-400",
              ].join(" ")}
            >
              {isDone ? <FiCheck size={13} /> : String(step.index).padStart(2, "0")}
            </span>
            <span className={`text-[13.5px] font-semibold ${isCurrent ? "text-navy-900" : "text-ink-700"}`}>
              {step.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
