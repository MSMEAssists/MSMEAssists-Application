import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Select from "../../components/ui/Select";
import Input from "../../components/ui/Input";
import Badge from "../../components/ui/Badge";
import Alert from "../../components/ui/Alert";
import WizardNav from "../../components/wizard/WizardNav";
import { PageLoader } from "../../components/ui/Spinner";
import { useProfile } from "../../hooks/useProfile";
import { REGISTRATION_TYPES, REGISTRATION_STATUSES, REGISTRATION_STATUS_BADGE } from "../../utils/constants";

function buildInitialRows(existingRegistrations = []) {
  const byType = Object.fromEntries(existingRegistrations.map((r) => [r.type, r]));
  return REGISTRATION_TYPES.map((t) => ({
    type: t.value,
    label: t.label,
    status: byType[t.value]?.status || "not_applicable",
    identifier: "",
    maskedOnFile: byType[t.value]?.masked_identifier || null,
  }));
}

export default function RegistrationsStep() {
  const { profile, isLoading, isSaving, saveSection } = useProfile();
  const navigate = useNavigate();
  const [rows, setRows] = useState(buildInitialRows());
  const [apiError, setApiError] = useState(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (!hydrated.current && profile) {
      setRows(buildInitialRows(profile.registrations));
      hydrated.current = true;
    }
  }, [profile]);

  function updateRow(type, field, value) {
    setRows((prev) => prev.map((r) => (r.type === type ? { ...r, [field]: value } : r)));
  }

  async function persist() {
    setApiError(null);
    if (!profile) {
      setApiError("Please complete the Business step first.");
      return false;
    }
    try {
      await saveSection({
        registrations: rows.map((r) => ({
          type: r.type,
          status: r.status,
          identifier: r.identifier ? r.identifier : null,
        })),
      });
      return true;
    } catch (err) {
      setApiError(err.message || "Could not save your registration details.");
      return false;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (await persist()) navigate("/onboarding/documents");
  }

  async function handleSaveAndExit() {
    if (await persist()) navigate("/");
  }

  if (isLoading) return <PageLoader label="Loading…" />;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-6">
        <h2 className="text-xl sm:text-2xl font-extrabold text-charcoal">5. Standards &amp; Registrations</h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-text">
          Specify your statutory enterprise registrations to qualify for government portal verification.
        </p>
      </div>

      <Alert variant="error" className="mb-5">{apiError}</Alert>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.type} className="rounded-xl border border-border bg-white p-4.5 shadow-card hover:border-slate-muted transition">
            <div className="mb-3 flex items-center justify-between gap-2">
              <span className="text-sm font-bold text-charcoal">{row.label}</span>
              <Badge variant={REGISTRATION_STATUS_BADGE[row.status] || "neutral"}>
                {REGISTRATION_STATUSES.find((s) => s.value === row.status)?.label}
              </Badge>
            </div>
            <Select
              options={REGISTRATION_STATUSES}
              value={row.status}
              onChange={(e) => updateRow(row.type, "status", e.target.value)}
              containerClassName="mb-2.5"
            />
            {row.status !== "not_applicable" && (
              <Input
                placeholder={row.maskedOnFile ? `On file: ${row.maskedOnFile}` : "Registration / identifier number"}
                value={row.identifier}
                onChange={(e) => updateRow(row.type, "identifier", e.target.value)}
              />
            )}
          </div>
        ))}
      </div>

      <WizardNav stepKey="registrations" onSaveAndExit={handleSaveAndExit} isSaving={isSaving} />
    </form>
  );
}
