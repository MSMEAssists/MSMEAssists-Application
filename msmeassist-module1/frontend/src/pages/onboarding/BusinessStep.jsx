import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Input from "../../components/ui/Input";
import TextArea from "../../components/ui/TextArea";
import SelectCard from "../../components/ui/SelectCard";
import Alert from "../../components/ui/Alert";
import WizardNav from "../../components/wizard/WizardNav";
import { PageLoader } from "../../components/ui/Spinner";
import { useProfile } from "../../hooks/useProfile";
import { BUSINESS_TYPES } from "../../utils/constants";
import { FiBriefcase, FiPackage, FiShoppingBag, FiMoreHorizontal } from "react-icons/fi";

const TYPE_ICONS = { manufacturing: FiPackage, services: FiBriefcase, trading: FiShoppingBag, other: FiMoreHorizontal };

const EMPTY_FORM = { name: "", type: "manufacturing", industry: "", sub_sector: "", established_date: "", description: "" };

export default function BusinessStep() {
  const { profile, isLoading, isSaving, saveSection } = useProfile();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (!hydrated.current && profile?.business) {
      setForm({
        name: profile.business.name || "",
        type: profile.business.type || "manufacturing",
        industry: profile.business.industry || "",
        sub_sector: profile.business.sub_sector || "",
        established_date: profile.business.established_date || "",
        description: profile.business.description || "",
      });
      hydrated.current = true;
    }
  }, [profile]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function validate() {
    const errs = {};
    if (!form.name.trim()) errs.name = "Business name is required";
    if (!form.industry.trim()) errs.industry = "Industry is required";
    if (!form.established_date) errs.established_date = "Establishment date is required";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function persist() {
    setApiError(null);
    if (!validate()) return false;
    try {
      await saveSection({
        business: {
          name: form.name,
          type: form.type,
          industry: form.industry,
          sub_sector: form.sub_sector || null,
          established_date: form.established_date,
          description: form.description || null,
        },
      });
      return true;
    } catch (err) {
      if (err.field) setErrors((prev) => ({ ...prev, [err.field]: err.message }));
      else setApiError(err.message || "Could not save your business details.");
      return false;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (await persist()) navigate("/onboarding/location");
  }

  async function handleSaveAndExit() {
    if (await persist()) navigate("/");
  }

  if (isLoading) return <PageLoader label="Loading your business profile…" />;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-6">
        <h2 className="text-xl sm:text-2xl font-extrabold text-charcoal">1. Basic Details</h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-text">
          Enter your registered enterprise name, industry sector, and operational category.
        </p>
      </div>

      <Alert variant="error" className="mb-5">{apiError}</Alert>

      <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] sm:grid-cols-2">
        <Input
          label="Business Name"
          required
          value={form.name}
          error={errors.name}
          onChange={(e) => update("name", e.target.value)}
        />
        <Input
          label="Establishment Date"
          required
          type="date"
          value={form.established_date}
          error={errors.established_date}
          onChange={(e) => update("established_date", e.target.value)}
        />

        <div className="sm:col-span-2">
          <label className="mb-1.5 block text-[13px] font-semibold text-ink-700">
            Business Type <span className="text-error-600">*</span>
          </label>
          <SelectCard
            options={BUSINESS_TYPES.map((t) => ({ ...t, icon: TYPE_ICONS[t.value] }))}
            value={form.type}
            onChange={(v) => update("type", v)}
          />
        </div>

        <Input
          label="Industry"
          required
          placeholder="e.g. Metal & Engineering Products"
          value={form.industry}
          error={errors.industry}
          onChange={(e) => update("industry", e.target.value)}
        />
        <Input
          label="Sub-sector"
          placeholder="e.g. Sheet Metal Fabrication"
          value={form.sub_sector}
          onChange={(e) => update("sub_sector", e.target.value)}
        />

        <TextArea
          label="Business Description"
          rows={3}
          hint="A short, plain description helps our engine match relevant schemes."
          containerClassName="sm:col-span-2"
          value={form.description}
          onChange={(e) => update("description", e.target.value)}
        />
      </div>

      <WizardNav stepKey="business" onSaveAndExit={handleSaveAndExit} isSaving={isSaving} />
    </form>
  );
}
