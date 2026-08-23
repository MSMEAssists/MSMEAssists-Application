import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Select from "../../components/ui/Select";
import Switch from "../../components/ui/Switch";
import Alert from "../../components/ui/Alert";
import WizardNav from "../../components/wizard/WizardNav";
import { PageLoader } from "../../components/ui/Spinner";
import { useProfile } from "../../hooks/useProfile";
import { SOCIAL_CATEGORIES } from "../../utils/constants";

const EMPTY_FORM = {
  is_women_owned: false,
  social_category: "general",
  is_first_gen_entrepreneur: false,
  is_startup_recognized: false,
  is_rural_enterprise: false,
  exports_currently: false,
  export_intent: false,
  is_tech_oriented: false,
  is_sustainable: false,
};

export default function CharacteristicsStep() {
  const { profile, isLoading, isSaving, saveSection } = useProfile();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [apiError, setApiError] = useState(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (!hydrated.current && profile?.characteristics) {
      setForm({ ...EMPTY_FORM, ...profile.characteristics });
      hydrated.current = true;
    }
  }, [profile]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function persist() {
    setApiError(null);
    if (!profile) {
      setApiError("Please complete the Business step first.");
      return false;
    }
    try {
      await saveSection({ characteristics: form });
      return true;
    } catch (err) {
      setApiError(err.message || "Could not save your business characteristics.");
      return false;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (await persist()) navigate("/onboarding/registrations");
  }

  async function handleSaveAndExit() {
    if (await persist()) navigate("/");
  }

  if (isLoading) return <PageLoader label="Loading…" />;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-2 font-data text-xs font-semibold uppercase tracking-wide text-teal-600">Step 4 of 7</div>
      <h3 className="mb-1.5 text-2xl">Business characteristics</h3>
      <p className="mb-7 text-sm text-ink-500">
        These attributes unlock category-specific schemes and relaxations. Select all that apply.
      </p>

      <Alert variant="error" className="mb-5">{apiError}</Alert>

      <Section title="Ownership" desc="Ownership category can unlock reserved schemes and subsidy relaxations.">
        <Switch
          label="Women-owned enterprise"
          description="51%+ ownership or controlling stake held by women"
          checked={form.is_women_owned}
          onChange={(v) => update("is_women_owned", v)}
        />
        <Select
          label="Social Category"
          options={SOCIAL_CATEGORIES}
          value={form.social_category}
          onChange={(e) => update("social_category", e.target.value)}
          containerClassName="mb-2.5"
        />
        <Switch
          label="First-generation entrepreneur"
          description="No prior family history of business ownership"
          checked={form.is_first_gen_entrepreneur}
          onChange={(v) => update("is_first_gen_entrepreneur", v)}
        />
      </Section>

      <Section title="Business Stage" desc="Stage-specific schemes differ for early-stage vs. established enterprises.">
        <Switch
          label="Recognised startup (DPIIT)"
          description="Holds a valid Startup India recognition certificate"
          checked={form.is_startup_recognized}
          onChange={(v) => update("is_startup_recognized", v)}
        />
        <Switch
          label="Rural enterprise"
          description="Primary operations located in a designated rural area"
          checked={form.is_rural_enterprise}
          onChange={(v) => update("is_rural_enterprise", v)}
        />
      </Section>

      <Section title="Business Reach" desc="Export activity opens access to trade-focused support schemes.">
        <Switch
          label="Currently exports goods/services"
          description="Has an active export order in the last 12 months"
          checked={form.exports_currently}
          onChange={(v) => update("exports_currently", v)}
        />
        <Switch
          label="Intends to export"
          description="Actively exploring export markets"
          checked={form.export_intent}
          onChange={(v) => update("export_intent", v)}
        />
      </Section>

      <Section title="Innovation & Sustainability" desc="Relevant to technology, R&D, and green-manufacturing linked schemes." last>
        <Switch
          label="Technology-oriented business"
          description="Product or process built around proprietary technology"
          checked={form.is_tech_oriented}
          onChange={(v) => update("is_tech_oriented", v)}
        />
        <Switch
          label="Sustainable / green practices"
          description="Uses energy-efficient, low-emission or recycled processes"
          checked={form.is_sustainable}
          onChange={(v) => update("is_sustainable", v)}
        />
      </Section>

      <WizardNav stepKey="characteristics" onSaveAndExit={handleSaveAndExit} isSaving={isSaving} />
    </form>
  );
}

function Section({ title, desc, children, last }) {
  return (
    <div className={last ? "" : "mb-7"}>
      <div className="mb-1 text-sm font-bold text-navy-900">{title}</div>
      <p className="mb-3.5 text-[12.5px] text-ink-500">{desc}</p>
      {children}
    </div>
  );
}
