import { useNavigate } from "react-router-dom";
import { FiCheck } from "react-icons/fi";
import { WIZARD_STEPS } from "../../utils/constants";
import { useCompleteness } from "../../hooks/useCompleteness";

export default function HorizontalStepBar({ currentStepKey }) {
  const navigate = useNavigate();
  const { sections } = useCompleteness();

  return (
    <div className="w-full overflow-x-auto pb-2">
      <div className="flex items-center justify-between min-w-[700px] gap-2 px-2">
        {WIZARD_STEPS.map((step, idx) => {
          const isCurrent = step.key === currentStepKey;
          const isDone = sections[step.key] && !isCurrent;
          const isLast = idx === WIZARD_STEPS.length - 1;

          return (
            <div key={step.key} className="flex items-center flex-1 last:flex-none">
              <button
                type="button"
                onClick={() => navigate(`/onboarding/${step.key}`)}
                className="flex flex-col items-center gap-1.5 group cursor-pointer text-center focus:outline-none"
              >
                {/* Step Circle */}
                <span
                  className={[
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all duration-150 select-none",
                    isCurrent
                      ? "bg-burnt-orange text-white shadow-md ring-4 ring-burnt-light"
                      : isDone
                      ? "bg-success-600 text-white"
                      : "bg-white border border-border text-slate-text group-hover:border-charcoal",
                  ].join(" ")}
                >
                  {isDone ? <FiCheck size={14} /> : step.index}
                </span>

                {/* Step Label */}
                <span
                  className={[
                    "text-[11px] font-semibold tracking-tight whitespace-nowrap transition-colors",
                    isCurrent
                      ? "text-charcoal font-bold"
                      : isDone
                      ? "text-slate-dark"
                      : "text-slate-text group-hover:text-charcoal",
                  ].join(" ")}
                >
                  {step.label}
                </span>
              </button>

              {/* Connecting line */}
              {!isLast && (
                <div
                  className={`flex-1 h-0.5 mx-2 -mt-4 transition-colors ${
                    isDone ? "bg-success-600" : "bg-border"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
