import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Input from "../../components/ui/Input";
import Select from "../../components/ui/Select";
import Alert from "../../components/ui/Alert";
import WizardNav from "../../components/wizard/WizardNav";
import { PageLoader } from "../../components/ui/Spinner";
import { useProfile } from "../../hooks/useProfile";
import { AREA_TYPES, PREMISES_TYPES } from "../../utils/constants";
import { isValidPinCode } from "../../utils/validators";

const EMPTY_FORM = { state: "", district: "", city: "", pin_code: "", area_type: "urban", premises_type: "" };

export default function LocationStep() {
  const { profile, isLoading, isSaving, saveSection } = useProfile();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (!hydrated.current && profile?.location) {
      setForm({
        state: profile.location.state || "",
        district: profile.location.district || "",
        city: profile.location.city || "",
        pin_code: profile.location.pin_code || "",
        area_type: profile.location.area_type || "urban",
        premises_type: profile.location.premises_type || "",
      });
      hydrated.current = true;
    }
  }, [profile]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function validate() {
    const errs = {};
    if (!form.state.trim()) errs.state = "State is required";
    if (!form.district.trim()) errs.district = "District is required";
    if (!form.city.trim()) errs.city = "City / town is required";
    if (!isValidPinCode(form.pin_code)) errs.pin_code = "PIN code must be exactly 6 digits";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function persist() {
    setApiError(null);
    if (!profile) {
      setApiError("Please complete the Business step first.");
      return false;
    }
    if (!validate()) return false;
    try {
      await saveSection({
        location: {
          state: form.state,
          district: form.district,
          city: form.city,
          pin_code: form.pin_code,
          area_type: form.area_type,
          premises_type: form.premises_type || null,
        },
      });
      return true;
    } catch (err) {
      if (err.field) setErrors((prev) => ({ ...prev, [err.field.replace("location.", "")]: err.message }));
      else setApiError(err.message || "Could not save your location details.");
      return false;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (await persist()) navigate("/onboarding/financial");
  }

  async function handleSaveAndExit() {
    if (await persist()) navigate("/");
  }

  if (isLoading) return <PageLoader label="Loading…" />;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-2 font-data text-xs font-semibold uppercase tracking-wide text-teal-600">Step 2 of 7</div>
      <h3 className="mb-1.5 text-2xl">Where is your business located?</h3>
      <p className="mb-7 text-sm text-ink-500">
        State and district-level schemes are matched based on your operating location.
      </p>

      <Alert variant="error" className="mb-5">{apiError}</Alert>

      <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] sm:grid-cols-2">
        <Input label="State" required value={form.state} error={errors.state} onChange={(e) => update("state", e.target.value)} />
        <Input label="District" required value={form.district} error={errors.district} onChange={(e) => update("district", e.target.value)} />
        <Input label="City / Town" required value={form.city} error={errors.city} onChange={(e) => update("city", e.target.value)} />
        <Input
          label="PIN Code"
          required
          maxLength={6}
          value={form.pin_code}
          error={errors.pin_code}
          onChange={(e) => update("pin_code", e.target.value.replace(/\D/g, ""))}
        />

        <div className="sm:col-span-2">
          <label className="mb-1.5 block text-[13px] font-semibold text-ink-700">
            Area Classification <span className="text-error-600">*</span>
          </label>
          <div className="grid grid-cols-2 gap-2.5">
            {AREA_TYPES.map((opt) => (
              <button
                type="button"
                key={opt.value}
                onClick={() => update("area_type", opt.value)}
                className={[
                  "rounded-md border-[1.5px] py-3 text-center text-[12.5px] font-semibold transition-colors",
                  form.area_type === opt.value
                    ? "border-navy-900 bg-navy-900 text-white"
                    : "border-border bg-white text-ink-700 hover:border-teal-500",
                ].join(" ")}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <Select
          label="Operating Location Type"
          placeholder="Select premises type"
          options={PREMISES_TYPES}
          value={form.premises_type}
          onChange={(e) => update("premises_type", e.target.value)}
          containerClassName="sm:col-span-2"
        />
      </div>

      <WizardNav stepKey="location" onSaveAndExit={handleSaveAndExit} isSaving={isSaving} />
    </form>
  );
}
