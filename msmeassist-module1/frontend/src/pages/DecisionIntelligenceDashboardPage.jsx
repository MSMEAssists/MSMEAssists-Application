import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  FiCheckCircle,
  FiChevronDown,
  FiChevronUp,
  FiCopy,
  FiDownload,
  FiExternalLink,
  FiFileText,
  FiShield,
} from "react-icons/fi";
import AppLayout from "../layouts/AppLayout";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Alert from "../components/ui/Alert";
import { PageLoader } from "../components/ui/Spinner";
import { OnboardingProvider, useOnboarding } from "../context/OnboardingContext";
import decisionIntelligenceService from "../services/decisionIntelligenceService";
import recommendationService from "../services/recommendationService";
import complianceService from "../services/complianceService";
import SchemeComplianceModal from "../components/compliance/SchemeComplianceModal";
import { formatDate, formatINR, titleCase } from "../utils/formatters";
import { cleanPortalUrl, validateDirectApplicationUrl } from "../utils/urlSanitizer";
import { downloadPersonalizedSchemePdf } from "../utils/schemeReportPdf";

function presentValue(value) {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  return text;
}

function humanWhy(scheme) {
  const factors = (scheme.driving_profile_factors || []).filter(Boolean);
  if (factors.length) {
    return `This scheme may be relevant because it aligns with: ${factors.join(", ")}.`;
  }
  const raw = presentValue(scheme.why_recommended);
  if (!raw) return "";
  return raw
    .replace(/Ranked #\d+ via Bradley-Terry-Luce Model \([^)]+\)\.\s*/i, "")
    .replace(/Latent utility θ=[^,]*,\s*/i, "")
    .replace(/win probability=[^%]+%\.\s*/i, "")
    .trim();
}

function eligibilityPresentation(status) {
  const key = presentValue(status).toLowerCase().replace(/\s+/g, "_");
  if (!key) {
    return {
      label: "Needs verification",
      variant: "warning",
      note: "Official eligibility still needs to be confirmed against the scheme guidelines.",
    };
  }
  if (key.includes("not_eligible") || key === "ineligible") {
    return {
      label: "May not be eligible",
      variant: "error",
      note: "Review the official conditions before taking further action.",
    };
  }
  if (
    key.includes("insufficient") ||
    key.includes("confirm") ||
    key.includes("need") ||
    key.includes("verif")
  ) {
    return {
      label: "Needs verification",
      variant: "warning",
      note: "More information or documents may be required before eligibility can be confirmed.",
    };
  }
  if (key.includes("potential") || key.includes("conditional")) {
    return {
      label: "Potential match",
      variant: "warning",
      note: "This may apply to your business, but official conditions still need to be checked.",
    };
  }
  if (key.includes("eligible")) {
    return {
      label: "Likely eligible",
      variant: "success",
      note: "This is an indicative finding only. It does not guarantee approval or funding.",
    };
  }
  return {
    label: titleCase(status),
    variant: "neutral",
    note: "Please confirm this finding against the official scheme guidelines.",
  };
}

function matchLabel(scheme) {
  const similarity = Number(scheme.similarity_score);
  if (!Number.isNaN(similarity) && similarity > 0) {
    const pct = similarity <= 1 ? Math.round(similarity * 100) : Math.round(similarity);
    return `Match strength ${pct}% (ranking indicator, not an official approval)`;
  }
  return "";
}

function listFromUnknown(value) {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === "string") return item;
        return (
          item?.text ||
          item?.statement ||
          item?.clause ||
          item?.document ||
          item?.name ||
          item?.description ||
          ""
        );
      })
      .map((text) => presentValue(text))
      .filter(Boolean);
  }
  if (typeof value === "string") return [value];
  return [];
}

function buildProfileFields(profile, overview) {
  const business = profile?.business || {};
  const location = profile?.location || {};
  const financial = profile?.financial || {};
  const overviewSafe = overview || {};

  const locationParts = [location.city, location.district, location.state]
    .map(presentValue)
    .filter(Boolean);
  const locationText =
    locationParts.join(", ") || presentValue(overviewSafe.location) || presentValue(overviewSafe.state);

  const classification =
    presentValue(financial.msme_classification) || presentValue(overviewSafe.msme_classification);
  const turnover =
    financial.annual_turnover_inr != null
      ? formatINR(financial.annual_turnover_inr)
      : presentValue(overviewSafe.turnover_formatted) ||
        presentValue(overviewSafe.annual_turnover_formatted);
  const investment =
    financial.investment_inr != null
      ? formatINR(financial.investment_inr)
      : presentValue(overviewSafe.investment_formatted);

  const fields = [
    { label: "Business name", value: presentValue(business.name) || presentValue(overviewSafe.business_name) },
    {
      label: "Business sector",
      value: presentValue(business.industry) || presentValue(overviewSafe.industry),
    },
    { label: "Location", value: locationText },
    {
      label: "Business classification",
      value: classification ? titleCase(classification) : "",
    },
    { label: "Annual turnover", value: turnover },
    { label: "Plant / machinery investment", value: investment },
  ];

  return fields.filter((field) => field.value);
}

function SchemeReportContent() {
  const { profile, documents, isLoading: profileLoading, loadError: profileError } = useOnboarding();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [downloadState, setDownloadState] = useState({ status: "idle", message: "" });
  const downloadInProgressRef = useRef(false);

  const [complianceScheme, setComplianceScheme] = useState(null);
  const [complianceData, setComplianceData] = useState(null);
  const [isComplianceOpen, setIsComplianceOpen] = useState(false);
  const [isComplianceLoading, setIsComplianceLoading] = useState(false);
  const [complianceError, setComplianceError] = useState(null);

  const loadReport = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await decisionIntelligenceService.orchestrateDecision({
        objective: "comprehensive",
        top_k: 5,
      });
      setData(response);
    } catch {
      // Graceful fallback to real recommendation service ranking
      try {
        const fallbackRecs = await recommendationService.getRankedRecommendations(5);
        if (fallbackRecs?.rankings?.length) {
          setData({
            top_scheme_recommendations: fallbackRecs.rankings.map((r, i) => ({
              rank: r.rank || i + 1,
              id: r.id || r.scheme_id || `scheme-${i}`,
              title: r.title || r.scheme_name || "Government Scheme",
              organization: r.organization || r.department || "",
              knowledge_type: r.knowledge_type || "SCHEME",
              official_url: r.official_url || "",
              official_application_url: r.official_application_url || "",
              eligibility_status: r.eligibility_status || "needs_verification",
              similarity_score: r.similarity_score || r.score || 0,
              why_recommended: r.why_recommended || r.explanation || "",
              driving_profile_factors: r.driving_profile_factors || [],
              key_benefits: r.key_benefits || (r.benefits_summary ? [r.benefits_summary] : []),
              eligibility_criteria: r.eligibility_criteria || [],
              required_documents: r.required_documents || [],
            })),
            business_overview: {},
            orchestrated_at: new Date().toISOString(),
          });
          return;
        }
      } catch {
        // Both endpoints failed
      }
      setError("We could not prepare your scheme report right now. Please try again in a moment.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  const schemes = data?.top_scheme_recommendations || [];
  const profileFields = useMemo(
    () => buildProfileFields(profile, data?.business_overview),
    [profile, data]
  );
  const generatedAt = formatDate(data?.orchestrated_at);

  const nextSteps = useMemo(() => {
    const steps = [
      {
        title: "Review eligibility",
        detail: "Confirm the scheme's official conditions.",
      },
    ];

    const documentHints = [];
    (documents || []).forEach((doc) => {
      if (doc?.document_type || doc?.file_name) {
        documentHints.push(doc.document_type || doc.file_name);
      }
    });
    (data?.export_advisory?.document_checklist || []).forEach((item) => {
      if (item?.document) documentHints.push(item.document);
    });

    steps.push({
      title: "Prepare required documents",
      detail: documentHints.length
        ? `Use the document checklist provided for each scheme (${[...new Set(documentHints)].slice(0, 4).join(", ")}).`
        : "Use the document checklist provided for each scheme.",
    });

    steps.push({
      title: "Apply through the official portal",
      detail: "Follow the verified application link where available.",
    });

    return steps;
  }, [data, documents]);

  const handleOpenCompliance = async (scheme) => {
    setComplianceScheme({
      id: scheme.id,
      title: scheme.title,
      organization: scheme.organization,
      official_url: scheme.official_url,
      knowledge_type: scheme.knowledge_type,
    });
    setComplianceData(null);
    setComplianceError(null);
    setIsComplianceOpen(true);
    setIsComplianceLoading(true);
    try {
      const result = await complianceService.checkSchemeCompliance({
        schemeId: scheme.id,
        schemeName: scheme.title,
        schemeOrganization: scheme.organization,
        officialUrl: scheme.official_url,
        knowledgeType: scheme.knowledge_type || "SCHEME",
      });
      setComplianceData(result);
    } catch {
      setComplianceError("We could not complete the eligibility check. Please try again.");
    } finally {
      setIsComplianceLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (downloadInProgressRef.current) return;
    if (!schemes.length) {
      setDownloadState({
        status: "error",
        message: "Your report is not ready to download yet. Wait for recommendations to load, then try again.",
      });
      return;
    }

    downloadInProgressRef.current = true;
    setDownloadState({ status: "working", message: "Preparing your PDF report…" });
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 80));
      downloadPersonalizedSchemePdf({
        businessName: profileFields.find((f) => f.label === "Business name")?.value || "MSMEAssist",
        generatedAt,
        profileFields,
        nextSteps,
        schemes: schemes.map((scheme, idx) => {
          const eligibility = eligibilityPresentation(scheme.eligibility_status);
          return {
            rank: scheme.rank || idx + 1,
            title: scheme.title,
            organization: scheme.organization,
            eligibilityLabel: `${eligibility.label}. ${eligibility.note}`,
            matchLabel: matchLabel(scheme),
            why: humanWhy(scheme),
            benefits: listFromUnknown(scheme.key_benefits),
            conditions: listFromUnknown(scheme.eligibility_criteria),
            documents: listFromUnknown(scheme.required_documents),
            guidelinesUrl: scheme.official_url ? cleanPortalUrl(scheme.official_url) : "",
            applyUrl: validateDirectApplicationUrl(scheme.official_application_url || scheme.official_url) || "",
          };
        }),
      });
      setDownloadState({
        status: "success",
        message: "Your personalized PDF report has been downloaded.",
      });
    } catch {
      setDownloadState({
        status: "error",
        message: "The PDF could not be created. Please try again.",
      });
    } finally {
      downloadInProgressRef.current = false;
    }
  };

  if (profileLoading || isLoading) {
    return <PageLoader label="Preparing your personalized scheme report…" />;
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8 space-y-7">
        {/* ── Top Header Banner with Brand & Download PDF Button ── */}
        <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-charcoal text-white shadow-xs">
              <svg
                className="h-6 w-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 21h18M3 10h18M5 10v11M9 10v11M13 10v11M17 10v11M12 3L2 10h20L12 3z" />
              </svg>
            </div>
            <div>
              <h1 className="font-display text-xl font-bold tracking-tight text-charcoal sm:text-2xl leading-tight">
                MSMEAssist
              </h1>
              <p className="text-xs font-medium text-slate-text">
                Government Schemes. Made Simple.
              </p>
            </div>
          </div>

          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={handleDownloadPdf}
            isLoading={downloadState.status === "working"}
            disabled={downloadState.status === "working"}
            aria-busy={downloadState.status === "working"}
            className="shrink-0 font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-burnt-orange focus-visible:ring-offset-2"
          >
            <FiDownload size={16} aria-hidden="true" />
            Download PDF
          </Button>
        </header>

        {/* ── Page Title & Kicker ── */}
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-burnt-orange">
            YOUR BUSINESS SUPPORT REPORT
          </p>
          <h2 className="mt-1 font-display text-2xl font-extrabold tracking-tight text-charcoal sm:text-3xl">
            Your Personalized Scheme Report
          </h2>
          <p className="mt-1.5 text-sm text-slate-text">
            Your recommended government schemes, eligibility findings, and next steps in one place.
          </p>
          {generatedAt && (
            <p className="mt-1 text-xs text-slate-text">Report generated on {generatedAt}</p>
          )}
        </div>

        {/* ── Feedback Alerts ── */}
        {downloadState.message && (
          <Alert
            variant={downloadState.status === "error" ? "error" : "success"}
            role="status"
            aria-live="polite"
          >
            {downloadState.message}
          </Alert>
        )}

        {(error || profileError) && (
          <div className="space-y-3">
            <Alert variant="error">
              {error || "Your saved business profile could not be loaded. Scheme findings may be incomplete."}
            </Alert>
            <Button type="button" variant="secondary" onClick={loadReport}>
              Try again
            </Button>
          </div>
        )}

        {/* ── Section B: Business Profile Summary ── */}
        <section className="rounded-xl border border-border bg-white p-6 shadow-card">
          <h3 className="text-base font-bold text-charcoal">Business Profile Summary</h3>
          {profileFields.length === 0 ? (
            <p className="mt-3 text-sm text-slate-text">
              No saved business profile details are available yet. Complete your profile to personalise this report.
            </p>
          ) : (
            <div className="mt-5 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
              {profileFields.map((field) => (
                <div key={field.label}>
                  <p className="text-xs font-medium text-slate-text">{field.label}</p>
                  <p className="mt-1 text-base font-bold text-charcoal tracking-tight">
                    {field.value}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Section C: Recommended Government Schemes ── */}
        <section className="space-y-4">
          <div>
            <h3 className="text-lg font-bold text-charcoal">Recommended Government Schemes</h3>
            <p className="mt-1 text-sm text-slate-text">
              Ranked for your saved business profile. A recommendation is not a guarantee of scheme approval or funding.
            </p>
          </div>

          {schemes.length === 0 ? (
            <div className="rounded-xl border border-border bg-white p-6 shadow-card">
              <p className="text-sm text-slate-dark">
                No scheme recommendations are available for your profile yet.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button type="button" variant="secondary" onClick={loadReport}>
                  Refresh report
                </Button>
                <Link
                  to="/schemes"
                  className="inline-flex items-center rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-slate-dark hover:bg-warm-offwhite focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-charcoal focus-visible:ring-offset-2"
                >
                  Browse schemes
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {schemes.map((scheme, index) => {
                const eligibility = eligibilityPresentation(scheme.eligibility_status);
                const isTop = index === 0;
                const schemeKey = scheme.id || `${scheme.title}-${index}`;
                const isOpen = expandedId === schemeKey;
                const guidelinesUrl = scheme.official_url ? cleanPortalUrl(scheme.official_url) : "";
                const applyUrl = validateDirectApplicationUrl(
                  scheme.official_application_url || scheme.official_url
                );
                const benefits = listFromUnknown(scheme.key_benefits);
                const conditions = listFromUnknown(scheme.eligibility_criteria);
                const requiredDocs = listFromUnknown(scheme.required_documents);
                const why = humanWhy(scheme);
                const match = matchLabel(scheme);
                const rankLabel = String(scheme.rank || index + 1).padStart(2, "0");

                return (
                  <article
                    key={schemeKey}
                    className={`rounded-xl border bg-white p-6 transition-all ${
                      isTop
                        ? "border-charcoal/30 shadow-card ring-1 ring-charcoal/5"
                        : "border-border shadow-card"
                    }`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex items-start gap-3.5">
                        <span
                          className={`mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
                            isTop ? "bg-charcoal text-white" : "bg-warm-muted text-charcoal"
                          }`}
                        >
                          {rankLabel}
                        </span>
                        <div>
                          <h4 className="text-base font-bold text-charcoal">
                            {isTop ? "Top scheme recommendation" : scheme.title}
                          </h4>
                          {isTop && (
                            <p className="mt-0.5 text-sm font-semibold text-slate-dark">
                              {scheme.title}
                            </p>
                          )}
                          {scheme.organization && (
                            <p className="mt-1 text-xs text-slate-text">{scheme.organization}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={eligibility.variant}>{eligibility.label}</Badge>
                      </div>
                    </div>

                    {why && <p className="mt-3.5 text-sm leading-relaxed text-slate-dark">{why}</p>}
                    {match && <p className="mt-2 text-xs font-medium text-slate-text">{match}</p>}
                    <p className="mt-1.5 text-xs text-slate-text">{eligibility.note}</p>

                    {/* Expandable Details Drawer */}
                    {isOpen && (
                      <div className="mt-4 space-y-4 border-t border-border pt-4 text-sm">
                        {benefits.length > 0 && (
                          <div>
                            <h5 className="text-xs font-bold uppercase tracking-wide text-slate-text">
                              Available benefits
                            </h5>
                            <ul className="mt-2 space-y-1.5 text-slate-dark">
                              {benefits.map((item, bIdx) => (
                                <li key={bIdx} className="flex gap-2">
                                  <FiCheckCircle className="mt-0.5 shrink-0 text-success-600" size={14} />
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {conditions.length > 0 && (
                          <div>
                            <h5 className="text-xs font-bold uppercase tracking-wide text-slate-text">
                              Eligibility conditions to review
                            </h5>
                            <ul className="mt-2 list-disc space-y-1.5 pl-5 text-slate-dark">
                              {conditions.map((item, cIdx) => (
                                <li key={cIdx}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {requiredDocs.length > 0 && (
                          <div>
                            <h5 className="text-xs font-bold uppercase tracking-wide text-slate-text">
                              Required documents
                            </h5>
                            <ul className="mt-2 space-y-1.5 text-slate-dark">
                              {requiredDocs.map((item, dIdx) => (
                                <li key={dIdx} className="flex gap-2">
                                  <FiFileText className="mt-0.5 shrink-0 text-burnt-orange" size={14} />
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {!benefits.length && !conditions.length && !requiredDocs.length && (
                          <p className="text-slate-text">
                            Extra scheme details were not included in this recommendation. Use the official guidelines
                            to review benefits, conditions, and documents.
                          </p>
                        )}
                      </div>
                    )}

                    {/* Action Buttons Row */}
                    <div className="mt-5 flex flex-wrap gap-2.5 border-t border-border pt-4">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => setExpandedId(isOpen ? null : schemeKey)}
                        className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-charcoal focus-visible:ring-offset-2"
                        aria-expanded={isOpen}
                      >
                        {isOpen ? <FiChevronUp size={14} /> : <FiChevronDown size={14} />}
                        View Details
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleOpenCompliance(scheme)}
                        className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-charcoal focus-visible:ring-offset-2"
                      >
                        <FiShield size={14} />
                        Check Eligibility
                      </Button>
                      {guidelinesUrl && (
                        <a
                          href={guidelinesUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-medium text-slate-dark hover:bg-warm-offwhite focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-charcoal focus-visible:ring-offset-2"
                        >
                          Official Guidelines
                          <FiExternalLink size={12} />
                        </a>
                      )}
                      {applyUrl && (
                        <a
                          href={applyUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg bg-charcoal px-3 py-1.5 text-xs font-semibold text-white hover:bg-charcoal-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-charcoal focus-visible:ring-offset-2"
                        >
                          Apply Now
                          <FiExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Section D: Your Next Steps ── */}
        <section className="rounded-xl border border-border bg-white p-6 shadow-card">
          <h3 className="text-base font-bold text-charcoal">Your Next Steps</h3>
          <ol className="mt-4 space-y-4">
            {nextSteps.map((step) => (
              <li key={step.title} className="flex items-start gap-3.5">
                <span className="mt-0.5 text-burnt-orange shrink-0">
                  {step.title === "Prepare required documents" ? (
                    <FiCopy size={18} aria-hidden="true" />
                  ) : step.title === "Apply through the official portal" ? (
                    <FiExternalLink size={18} aria-hidden="true" />
                  ) : (
                    <FiCheckCircle size={18} aria-hidden="true" />
                  )}
                </span>
                <div>
                  <p className="text-sm font-bold text-charcoal">{step.title}</p>
                  <p className="mt-0.5 text-sm text-slate-text leading-relaxed">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* ── Illustrative & Statutory Footnote ── */}
        <footer className="text-center pt-2 pb-4 text-xs text-slate-text/75 space-y-1">
          <p>
            Illustrative layout only. Actual business details, scheme rankings, eligibility findings, and PDF download must come from your existing application.
          </p>
          <p>
            Always verify conditions on the official government portal before applying. This report is a decision aid and does not guarantee scheme approval or funding.
          </p>
        </footer>
      </div>

      <SchemeComplianceModal
        scheme={complianceScheme}
        isOpen={isComplianceOpen}
        onClose={() => setIsComplianceOpen(false)}
        data={complianceData}
        isLoading={isComplianceLoading}
        error={complianceError}
        onRetry={() => handleOpenCompliance(complianceScheme)}
      />
    </AppLayout>
  );
}

export default function DecisionIntelligenceDashboardPage() {
  return (
    <OnboardingProvider>
      <SchemeReportContent />
    </OnboardingProvider>
  );
}

