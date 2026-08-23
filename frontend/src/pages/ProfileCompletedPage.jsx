import { useNavigate } from "react-router-dom";
import { FiCheck } from "react-icons/fi";
import AppLayout from "../layouts/AppLayout";
import Button from "../components/ui/Button";
import { PageLoader } from "../components/ui/Spinner";
import { useOnboarding, OnboardingProvider } from "../context/OnboardingContext";

function ProfileCompletedContent() {
  const { profile, documents, isLoading } = useOnboarding();
  const navigate = useNavigate();

  if (isLoading) return <PageLoader label="Loading your profile…" />;

  if (!profile) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="mb-4 text-ink-500">You haven't started a business profile yet.</p>
        <Button onClick={() => navigate("/onboarding/business")}>Start your profile</Button>
      </div>
    );
  }

  const missingCount = Object.values(profile.completeness.sections).filter((v) => !v).length;

  return (
    <div className="mx-auto max-w-[760px] px-6 pb-24 pt-16 text-center">
      <div className="mx-auto mb-6 flex h-[76px] w-[76px] items-center justify-center rounded-full bg-success-100">
        <FiCheck size={34} className="text-success-600" />
      </div>
      <h1 className="mb-2.5 text-[28px]">Your business profile is saved</h1>
      <p className="mx-auto mb-9 max-w-[480px] text-[15px] leading-relaxed text-ink-500">
        {profile.business?.name || "Your business"} is now set up on MSMEAssist. We'll use this profile to surface
        government services relevant to your business.
      </p>

      <div className="mb-9 grid grid-cols-2 gap-3.5 sm:grid-cols-3">
        <StatCard value={`${profile.completeness.percentage}%`} label="Profile Completeness" />
        <StatCard value={String(Object.values(profile.completeness.sections).filter(Boolean).length)} label="Sections Complete" />
        <StatCard value={String(missingCount)} label="Items Needing Attention" />
      </div>

      <div className="flex flex-wrap justify-center gap-3">
        <Button variant="secondary" onClick={() => navigate("/onboarding/review")}>
          Review Profile
        </Button>
        {/* Module 2 is out of scope — this only navigates to a placeholder route. */}
        <Button variant="cta" onClick={() => navigate("/schemes")}>
          Discover Government Schemes →
        </Button>
      </div>

      <p className="mt-6 font-data text-[11.5px] text-ink-400">
        {documents.length} document{documents.length === 1 ? "" : "s"} on file
      </p>
    </div>
  );
}

function StatCard({ value, label }) {
  return (
    <div className="rounded-md border border-border bg-white p-[18px]">
      <b className="block font-display text-[22px] text-navy-900">{value}</b>
      <span className="text-xs text-ink-500">{label}</span>
    </div>
  );
}

export default function ProfileCompletedPage() {
  return (
    <OnboardingProvider>
      <AppLayout>
        <ProfileCompletedContent />
      </AppLayout>
    </OnboardingProvider>
  );
}
