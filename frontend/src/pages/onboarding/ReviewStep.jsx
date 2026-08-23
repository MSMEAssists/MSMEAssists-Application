import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiCheck, FiAlertTriangle, FiChevronDown } from "react-icons/fi";
import Badge from "../../components/ui/Badge";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import { PageLoader } from "../../components/ui/Spinner";
import { useOnboarding } from "../../context/OnboardingContext";
import * as profileService from "../../services/profileService";
import { formatINR, formatDate, titleCase } from "../../utils/formatters";

export default function ReviewStep() {
  const { profile, documents, isLoading } = useOnboarding();
  const navigate = useNavigate();
  const [missing, setMissing] = useState([]);
  const [openSection, setOpenSection] = useState("business");
  const [isFinishing, setIsFinishing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!profile) return;
    profileService
      .getCompleteness()
      .then((c) => setMissing(c.missing || []))
      .catch(() => setMissing([]));
  }, [profile]);

  if (isLoading) return <PageLoader label="Loading…" />;

  if (!profile) {
    return <Alert variant="warning">Complete the earlier steps before reviewing your profile.</Alert>;
  }

  const missingBySection = missing.reduce((acc, m) => {
    (acc[m.section] ||= []).push(m.detail);
    return acc;
  }, {});

  async function handleSave() {
    setError(null);
    setIsFinishing(true);
    try {
      await profileService.getMyProfile(); // final confirm read from the real backend
      navigate("/profile/completed");
    } catch (err) {
      setError(err.message || "Could not finalize your profile. Please try again.");
    } finally {
      setIsFinishing(false);
    }
  }

  return (
    <div>
      <div className="mb-2 font-data text-xs font-semibold uppercase tracking-wide text-teal-600">Step 7 of 7</div>
      <h3 className="mb-1.5 text-2xl">Review your profile</h3>
      <p className="mb-7 text-sm text-ink-500">
        Check each section before saving. You can still edit anything later from here.
      </p>

      <Alert variant="error" className="mb-5">{error}</Alert>

      <ReviewSection
        title="Business"
        sectionKey="business"
        complete={profile.completeness.sections.business}
        open={openSection === "business"}
        onToggle={() => setOpenSection((s) => (s === "business" ? null : "business"))}
        onEdit={() => navigate("/onboarding/business")}
        missingItems={missingBySection.business}
      >
        {profile.business && (
          <>
            <Row k="Business Name" v={profile.business.name} />
            <Row k="Type" v={titleCase(profile.business.type)} />
            <Row k="Industry" v={profile.business.industry} />
            <Row k="Established" v={formatDate(profile.business.established_date)} />
          </>
        )}
      </ReviewSection>

      <ReviewSection
        title="Location"
        sectionKey="location"
        complete={profile.completeness.sections.location}
        open={openSection === "location"}
        onToggle={() => setOpenSection((s) => (s === "location" ? null : "location"))}
        onEdit={() => navigate("/onboarding/location")}
        missingItems={missingBySection.location}
      >
        {profile.location && (
          <>
            <Row k="State / District" v={`${profile.location.state} / ${profile.location.district}`} />
            <Row k="PIN Code" v={profile.location.pin_code} />
            <Row k="Area" v={titleCase(profile.location.area_type)} />
          </>
        )}
      </ReviewSection>

      <ReviewSection
        title="Financial"
        sectionKey="financial"
        complete={profile.completeness.sections.financial}
        open={openSection === "financial"}
        onToggle={() => setOpenSection((s) => (s === "financial" ? null : "financial"))}
        onEdit={() => navigate("/onboarding/financial")}
        missingItems={missingBySection.financial}
      >
        {profile.financial && (
          <>
            <Row k="Annual Turnover" v={formatINR(profile.financial.annual_turnover_inr)} />
            <Row k="Investment" v={formatINR(profile.financial.investment_inr)} />
            <Row k="Classification" v={titleCase(profile.financial.msme_classification)} />
          </>
        )}
      </ReviewSection>

      <ReviewSection
        title="Characteristics"
        sectionKey="characteristics"
        complete={profile.completeness.sections.characteristics}
        open={openSection === "characteristics"}
        onToggle={() => setOpenSection((s) => (s === "characteristics" ? null : "characteristics"))}
        onEdit={() => navigate("/onboarding/characteristics")}
        missingItems={missingBySection.characteristics}
      >
        {profile.characteristics && (
          <Row
            k="Tags selected"
            v={String(Object.values(profile.characteristics).filter((v) => v === true).length)}
          />
        )}
      </ReviewSection>

      <ReviewSection
        title="Registrations"
        sectionKey="registrations"
        complete={profile.completeness.sections.registrations}
        open={openSection === "registrations"}
        onToggle={() => setOpenSection((s) => (s === "registrations" ? null : "registrations"))}
        onEdit={() => navigate("/onboarding/registrations")}
        missingItems={missingBySection.registrations}
      >
        {profile.registrations.map((r) => (
          <Row key={r.type} k={titleCase(r.type)} v={titleCase(r.status)} />
        ))}
      </ReviewSection>

      <ReviewSection
        title="Documents"
        sectionKey="documents"
        complete={profile.completeness.sections.documents}
        open={openSection === "documents"}
        onToggle={() => setOpenSection((s) => (s === "documents" ? null : "documents"))}
        onEdit={() => navigate("/onboarding/documents")}
        missingItems={missingBySection.documents}
      >
        <Row k="Files uploaded" v={String(documents.length)} />
      </ReviewSection>

      {missing.length > 0 && (
        <div className="mt-4 flex items-start gap-2.5 rounded-md bg-warning-100 px-4 py-3.5">
          <FiAlertTriangle size={16} className="mt-0.5 flex-shrink-0 text-warning-600" />
          <span className="text-[12.5px] text-ink-700">
            <b>Missing information:</b> {missing.map((m) => m.detail).join(" · ")}
          </span>
        </div>
      )}

      <div className="mt-8 flex flex-col-reverse items-stretch gap-2.5 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
        <Button variant="ghost" type="button" onClick={() => navigate("/onboarding/documents")}>
          ← Back
        </Button>
        <Button type="button" isLoading={isFinishing} onClick={handleSave}>
          Save Profile
        </Button>
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex justify-between border-b border-dashed border-border py-1.5 text-[13px] last:border-none">
      <span className="text-ink-500">{k}</span>
      <span className="font-data text-[12.5px] font-semibold text-ink-900">{v || "—"}</span>
    </div>
  );
}

function ReviewSection({ title, complete, open, onToggle, onEdit, missingItems, children }) {
  return (
    <div className="mb-3.5 overflow-hidden rounded-md border border-border">
      <div className="flex cursor-pointer items-center gap-3 bg-surface-sunken px-[18px] py-3.5" onClick={onToggle}>
        <Badge variant={complete ? "success" : "warning"}>
          {complete ? (
            <>
              <FiCheck size={11} /> Complete
            </>
          ) : (
            <>
              <FiAlertTriangle size={11} /> Needs attention
            </>
          )}
        </Badge>
        <span className="flex-1 text-[13.5px] font-bold text-navy-900">{title}</span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="text-[13px] font-semibold text-teal-600 hover:underline"
        >
          Edit
        </button>
        <FiChevronDown className={`text-ink-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </div>
      {open && (
        <div className="px-[18px] py-4">
          {children}
          {missingItems?.length > 0 && (
            <p className="mt-2 text-[12px] font-medium text-error-600">{missingItems.join(" · ")}</p>
          )}
        </div>
      )}
    </div>
  );
}
