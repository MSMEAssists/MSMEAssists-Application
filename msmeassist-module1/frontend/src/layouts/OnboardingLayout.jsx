import { useLocation, useNavigate } from "react-router-dom";
import AppLayout from "./AppLayout";
import HorizontalStepBar from "../components/wizard/HorizontalStepBar";
import CompletenessWidget from "../components/wizard/CompletenessWidget";
import { useCompleteness } from "../hooks/useCompleteness";
import { FiSave, FiCheckCircle } from "react-icons/fi";

export default function OnboardingLayout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const step = location.pathname.split("/").filter(Boolean).pop();
  const { percentage } = useCompleteness();

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl px-4 pb-24 pt-8 sm:px-6">
        {/* ── Page Header matching concept board ─────────────────────── */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border/80 pb-5">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-charcoal">
              Business Profile
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-text">
              Complete your business profile to get the best scheme recommendations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-semibold text-slate-dark">
              <span className="flex h-2 w-2 rounded-full bg-burnt-orange" />
              <span>{percentage}% Completed</span>
            </div>

            <button
              type="button"
              onClick={() => navigate("/schemes")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-semibold text-slate-dark hover:bg-warm-offwhite transition"
              title="Save progress and browse schemes"
            >
              <FiSave size={13} className="text-burnt-orange" />
              <span>Save &amp; Resume</span>
            </button>
          </div>
        </div>

        {/* ── Horizontal 7-Step Progress Indicator ───────────────────── */}
        <div className="mb-8 rounded-xl border border-border bg-white p-4 shadow-card">
          <HorizontalStepBar currentStepKey={step} />
        </div>

        {/* ── Form Card Container ────────────────────────────────────── */}
        <main className="rounded-2xl border border-border bg-white p-6 shadow-elevated sm:p-10">
          {children}
        </main>
      </div>
    </AppLayout>
  );
}
