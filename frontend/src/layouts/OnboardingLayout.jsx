import { useLocation } from "react-router-dom";
import AppLayout from "./AppLayout";
import CompletenessWidget from "../components/wizard/CompletenessWidget";
import StepRail from "../components/wizard/StepRail";
import AiTipCard from "../components/wizard/AiTipCard";

export default function OnboardingLayout({ children }) {
  const location = useLocation();
  // Route table uses literal step segments (/onboarding/business, etc.),
  // not a dynamic :step param, so derive the current step from the path.
  const step = location.pathname.split("/").filter(Boolean).pop();

  return (
    <AppLayout>
      <div className="mx-auto max-w-[1180px] px-4 pb-20 pt-8 sm:px-6">
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[300px_1fr]">
          <aside className="flex flex-col gap-5 lg:sticky lg:top-[92px]">
            <CompletenessWidget />
            <StepRail currentStepKey={step} />
            <AiTipCard stepKey={step} />
          </aside>

          <main className="rounded-lg border border-border bg-white p-6 shadow-card sm:p-9">{children}</main>
        </div>
      </div>
    </AppLayout>
  );
}
