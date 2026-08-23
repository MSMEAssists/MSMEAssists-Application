import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Input from "../../components/ui/Input";
import Select from "../../components/ui/Select";
import Switch from "../../components/ui/Switch";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import WizardNav from "../../components/wizard/WizardNav";
import { PageLoader } from "../../components/ui/Spinner";
import { useProfile } from "../../hooks/useProfile";
import { PROFITABILITY_STATUSES } from "../../utils/constants";
import { titleCase } from "../../utils/formatters";

const EMPTY_FORM = {
  annual_turnover_inr: "",
  investment_inr: "",
  employee_count: "",
  has_existing_loan: false,
  has_bank_finance: false,
  profitability_status: "",
};

export default function FinancialStep() {
  const { profile, isLoading, isSaving, saveSection } = useProfile();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (!hydrated.current && profile?.financial) {
      setForm({
        annual_turnover_inr: String(profile.financial.annual_turnover_inr ?? ""),
        investment_inr: String(profile.financial.investment_inr ?? ""),
        employee_count: String(profile.financial.employee_count ?? ""),
        has_existing_loan: Boolean(profile.financial.has_existing_loan),
        has_bank_finance: Boolean(profile.financial.has_bank_finance),
        profitability_status: profile.financial.profitability_status || "",
      });
      hydrated.current = true;
    }
  }, [profile]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function validate() {
    const errs = {};
    if (form.annual_turnover_inr === "" || Number(form.annual_turnover_inr) < 0)
      errs.annual_turnover_inr = "Enter a valid turnover amount";
    if (form.investment_inr === "" || Number(form.investment_inr) < 0)
      errs.investment_inr = "Enter a valid investment amount";
    if (form.employee_count === "" || Number(form.employee_count) < 0)
      errs.employee_count = "Enter a valid employee count";
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
        financial: {
          annual_turnover_inr: Number(form.annual_turnover_inr),
          investment_inr: Number(form.investment_inr),
          employee_count: Number(form.employee_count),
          has_existing_loan: form.has_existing_loan,
          has_bank_finance: form.has_bank_finance,
          profitability_status: form.profitability_status || null,
        },
      });
      return true;
    } catch (err) {
      if (err.field) setErrors((prev) => ({ ...prev, [err.field.replace("financial.", "")]: err.message }));
      else setApiError(err.message || "Could not save your financial details.");
      return false;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (await persist()) navigate("/onboarding/characteristics");
  }

  async function handleSaveAndExit() {
    if (await persist()) navigate("/");
  }

  if (isLoading) return <PageLoader label="Loading…" />;

  const classification = profile?.financial?.msme_classification;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-2 font-data text-xs font-semibold uppercase tracking-wide text-teal-600">Step 3 of 7</div>
      <h3 className="mb-1.5 text-2xl">Financial profile</h3>
      <p className="mb-7 text-sm text-ink-500">
        Turnover and investment figures determine your MSME classification and eligible schemes.
      </p>

      <Alert variant="error" className="mb-5">{apiError}</Alert>

      <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] sm:grid-cols-2">
        <Input
          label="Annual Turnover (₹)"
          required
          type="number"
          min="0"
          className="font-data"
          value={form.annual_turnover_inr}
          error={errors.annual_turnover_inr}
          onChange={(e) => update("annual_turnover_inr", e.target.value)}
        />
        <Input
          label="Investment in Plant & Machinery (₹)"
          required
          type="number"
          min="0"
          className="font-data"
          value={form.investment_inr}
          error={errors.investment_inr}
          onChange={(e) => update("investment_inr", e.target.value)}
        />
        <Input
          label="Number of Employees"
          required
          type="number"
          min="0"
          className="font-data"
          value={form.employee_count}
          error={errors.employee_count}
          onChange={(e) => update("employee_count", e.target.value)}
        />
        <Select
          label="Profitability Status"
          placeholder="Select status"
          options={PROFITABILITY_STATUSES}
          value={form.profitability_status}
          onChange={(e) => update("profitability_status", e.target.value)}
        />

        <div className="sm:col-span-2">
          <Switch
            label="Do you have an existing business loan?"
            description="Include term loans, working capital or CGTMSE-backed credit"
            checked={form.has_existing_loan}
            onChange={(v) => update("has_existing_loan", v)}
          />
          <Switch
            label="Currently accessing formal bank finance"
            description="Cash credit, overdraft, or bank-issued working capital"
            checked={form.has_bank_finance}
            onChange={(v) => update("has_bank_finance", v)}
          />
        </div>

        {classification && classification !== "not_classified" && (
          <div className="flex items-center gap-2.5 rounded-md bg-surface-sunken px-4 py-3.5 sm:col-span-2">
            <Badge variant="saffron">{titleCase(classification)} Enterprise</Badge>
            <span className="text-[12.5px] text-ink-500">
              MSME classification calculated automatically from the figures above, per Udyam norms.
            </span>
          </div>
        )}
      </div>

      <WizardNav stepKey="financial" onSaveAndExit={handleSaveAndExit} isSaving={isSaving} />
    </form>
  );
}
