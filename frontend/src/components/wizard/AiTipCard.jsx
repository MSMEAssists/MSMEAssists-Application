import { FiCpu } from "react-icons/fi";

const TIPS = {
  business: "Manufacturing businesses often qualify for additional Udyam-linked benefits — we'll check this automatically in the Registrations step.",
  location: "State and district-level schemes are matched based on where your business actually operates, not your registered address.",
  financial: "Turnover and investment figures determine your MSME classification (Micro / Small / Medium) — this is calculated automatically, not something you select.",
  characteristics: "Attributes like women-ownership or export intent can unlock reserved schemes and subsidy relaxations later, in Module 2.",
  registrations: "Even if a registration is still in progress, mark it as such — partial progress is factored differently than a missing registration.",
  documents: "Uploading a document only records it here. Verification is handled separately and won't block you from continuing.",
  review: "Take a moment to check each section before saving — anything marked 'Needs attention' can still be edited from here.",
};

export default function AiTipCard({ stepKey }) {
  const tip = TIPS[stepKey];
  if (!tip) return null;
  return (
    <div className="flex gap-3 rounded-lg border border-[#bfe4e0] bg-teal-100 p-4">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-teal-600">
        <FiCpu size={14} className="text-white" />
      </div>
      <div>
        <div className="mb-1 font-data text-[11px] font-semibold uppercase tracking-wide text-teal-700">
          AI Guidance
        </div>
        <p className="text-[12.5px] leading-relaxed text-ink-700">{tip}</p>
      </div>
    </div>
  );
}
