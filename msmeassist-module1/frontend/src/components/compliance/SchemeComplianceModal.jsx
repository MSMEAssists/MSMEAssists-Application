/**
 * SchemeComplianceModal
 *
 * Slide-up full-screen panel that shows a rule-by-rule compliance
 * assessment for a specific government scheme against the authenticated
 * user's business profile.
 *
 * Props:
 *   scheme   {object}   — the DiscoveredSchemeOut object that was clicked
 *   isOpen   {boolean}
 *   onClose  {function}
 *   data     {object|null}  — SchemeComplianceResponse from the API
 *   isLoading {boolean}
 *   error    {string|null}
 *
 * Design rules:
 *   - Only existing custom Tailwind tokens (navy, teal, saffron, success,
 *     error, warning, ink, border, surface-sunken, bg).
 *   - Animation via framer-motion (already in package.json).
 *   - No shadcn / radix / headlessui.
 *   - Body scroll locked while open; Escape key closes.
 *   - Every rule card shows: category badge, rule text (from official source),
 *     verdict badge, profile fact, plain-language explanation, source citation.
 *   - Prominent disclaimer always visible at bottom.
 */
import { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cleanPortalUrl } from "../../utils/urlSanitizer";
import {
  FiX,
  FiCheckCircle,
  FiXCircle,
  FiAlertCircle,
  FiAlertTriangle,
  FiExternalLink,
  FiFileText,
  FiShield,
  FiInfo,
  FiClipboard,
  FiRefreshCw,
} from "react-icons/fi";
import { Spinner } from "../ui/Spinner";

// ---------------------------------------------------------------------------
// Config maps
// ---------------------------------------------------------------------------

const VERDICT = {
  met: {
    bg: "bg-success-100", text: "text-success-600",
    border: "border-success-100", Icon: FiCheckCircle, label: "Met",
  },
  not_met: {
    bg: "bg-error-100", text: "text-error-600",
    border: "border-error-100", Icon: FiXCircle, label: "Not Met",
  },
  needs_info: {
    bg: "bg-warning-100", text: "text-warning-600",
    border: "border-warning-100", Icon: FiAlertCircle, label: "Needs Info",
  },
};

const OVERALL = {
  ready: {
    bg: "bg-success-100", text: "text-success-600",
    border: "border-success-100", Icon: FiCheckCircle, label: "Ready to Apply",
  },
  partially_ready: {
    bg: "bg-saffron-100", text: "text-saffron-600",
    border: "border-saffron-100", Icon: FiAlertCircle, label: "Partially Ready",
  },
  action_required: {
    bg: "bg-error-100", text: "text-error-600",
    border: "border-error-100", Icon: FiXCircle, label: "Action Required",
  },
  insufficient_data: {
    bg: "bg-warning-100", text: "text-warning-600",
    border: "border-warning-100", Icon: FiAlertTriangle, label: "Insufficient Data",
  },
};

const CATEGORY_COLOR = {
  "Eligibility":         "bg-teal-100 text-teal-700",
  "Registration":        "bg-blue-100 text-blue-700",
  "Documents":           "bg-indigo-100 text-indigo-700",
  "Financial":           "bg-purple-100 text-purple-700",
  "Application":         "bg-saffron-100 text-saffron-600",
  "Special Provisions":  "bg-pink-100 text-pink-700",
};

function catColor(cat) {
  return CATEGORY_COLOR[cat] || "bg-surface-sunken text-ink-700";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Gap Analysis — the "you have / you are missing" checklist
// ---------------------------------------------------------------------------

const GAP_STATUS = {
  met:        { Icon: FiCheckCircle, color: "text-success-600", bg: "bg-success-100", label: "You have this" },
  not_met:    { Icon: FiXCircle,     color: "text-error-600",   bg: "bg-error-100",   label: "Missing — action required" },
  needs_info: { Icon: FiAlertCircle, color: "text-warning-600", bg: "bg-warning-100", label: "Needs verification" },
};

function GapAnalysisSection({ gaps, metCount, missingCount }) {
  if (!gaps || gaps.length === 0) return null;

  return (
    <div className="mb-6 rounded-md border border-border bg-white shadow-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface-sunken px-4 py-3">
        <div className="flex items-center gap-2">
          <FiClipboard size={15} className="text-navy-900" />
          <span className="text-sm font-bold text-navy-900">Readiness Checklist</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold bg-success-100 text-success-600">
            <FiCheckCircle size={10} /> {metCount} Ready
          </span>
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold bg-error-100 text-error-600">
            <FiAlertCircle size={10} /> {missingCount} Action needed
          </span>
        </div>
      </div>

      {/* Gap items */}
      <div className="divide-y divide-border">
        {gaps.map((gap, i) => {
          const cfg = GAP_STATUS[gap.status] || GAP_STATUS.needs_info;
          const Icon = cfg.Icon;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.2 }}
              className="px-4 py-3"
            >
              <div className="flex items-start gap-3">
                {/* Status icon */}
                <div className={`mt-0.5 flex-shrink-0 rounded-full p-1 ${cfg.bg}`}>
                  <Icon size={12} className={cfg.color} />
                </div>

                <div className="min-w-0 flex-1">
                  {/* Requirement name + status label */}
                  <div className="flex flex-wrap items-center justify-between gap-1 mb-0.5">
                    <span className="text-xs font-bold text-navy-900">{gap.requirement}</span>
                    <span className={`text-[10px] font-semibold ${cfg.color}`}>{cfg.label}</span>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-ink-500 mb-1">{gap.description}</p>

                  {/* Profile value */}
                  {gap.profile_value && (
                    <div className="mb-1 flex items-center gap-1.5 rounded bg-surface-sunken px-2 py-1">
                      <FiInfo size={10} className="flex-shrink-0 text-ink-400" />
                      <span className="font-data text-[11px] text-ink-700">
                        Your profile: <span className="font-semibold text-navy-900">{gap.profile_value}</span>
                      </span>
                    </div>
                  )}

                  {/* Gap detail + how to fix */}
                  {gap.status !== "met" && (gap.gap_detail || gap.how_to_fix) && (
                    <div className="rounded-md border border-teal-100 bg-teal-50 px-3 py-2 mt-1">
                      {gap.gap_detail && (
                        <p className="text-xs text-ink-700 mb-1">{gap.gap_detail}</p>
                      )}
                      {gap.how_to_fix && (
                        <>
                          <p className="text-[11px] font-bold uppercase tracking-wide text-teal-700 mb-0.5">What to do</p>
                          <p className="text-xs text-teal-900">{gap.how_to_fix}</p>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/** Tri-colour progress bar */
function ProgressBar({ met, notMet, total }) {
  if (!total) return null;
  const metPct    = Math.round((met    / total) * 100);
  const notMetPct = Math.round((notMet / total) * 100);
  const needsPct  = 100 - metPct - notMetPct;
  return (
    <div className="overflow-hidden rounded-full bg-border" style={{ height: 8 }}>
      <div className="flex h-full">
        <div className="bg-success-600 transition-all" style={{ width: `${metPct}%` }} />
        <div className="bg-error-600   transition-all" style={{ width: `${notMetPct}%` }} />
        <div className="bg-saffron-500 transition-all" style={{ width: `${needsPct}%` }} />
      </div>
    </div>
  );
}

/** Single rule card */
function RuleCard({ rule, index }) {
  const cfg  = VERDICT[rule.verdict] || VERDICT.needs_info;
  const Icon = cfg.Icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.22 }}
      className={`rounded-md border ${cfg.border} bg-white p-4 shadow-card`}
    >
      {/* Header */}
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${catColor(rule.category)}`}>
            {rule.category}
          </span>
          <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
            <Icon size={11} />
            {cfg.label}
          </span>
        </div>
        <span className="font-data text-[10px] text-ink-400">{rule.rule_id}</span>
      </div>

      {/* Rule text — verbatim from official source */}
      <p className="mb-2 text-xs font-medium leading-relaxed text-navy-900">
        {rule.rule_statement}
      </p>

      {/* Profile fact */}
      {rule.profile_fact && (
        <div className="mb-2 flex items-center gap-1.5 rounded bg-surface-sunken px-2.5 py-1.5">
          <FiInfo size={11} className="flex-shrink-0 text-ink-400" />
          <span className="font-data text-[11px] text-ink-700">
            Your profile:&nbsp;
            <span className="font-semibold text-navy-900">{rule.profile_fact}</span>
          </span>
        </div>
      )}

      {/* Explanation — split on "What to do:" to render guidance as an action box */}
      {(() => {
        const parts = rule.explanation.split(/\n\nWhat to do:/i);
        const context = parts[0].trim();
        const action  = parts[1] ? parts[1].trim() : null;
        return (
          <>
            <p className="mb-2 text-xs leading-relaxed text-ink-700">{context}</p>
            {action && (
              <div className="mb-2 rounded-md border border-teal-100 bg-teal-50 px-3 py-2.5">
                <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-teal-700">
                  What to do
                </p>
                <p className="text-xs leading-relaxed text-teal-900">{action}</p>
              </div>
            )}
          </>
        );
      })()}

      {/* Source provenance */}
      {(rule.source_url || rule.source_organization || rule.source_page_number != null) && (
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-data text-[10px] text-ink-400">
          {rule.source_organization && (
            <span className="inline-flex items-center gap-0.5">
              <FiShield size={10} className="text-teal-600" />
              {rule.source_organization}
            </span>
          )}
          {rule.source_page_number != null && (
            <span className="inline-flex items-center gap-0.5">
              <FiFileText size={10} /> Page {rule.source_page_number}
            </span>
          )}
          {rule.source_chunk_id && (
            <span className="text-ink-400">Chunk {rule.source_chunk_id}</span>
          )}
          {rule.source_url && (
            <a
              href={cleanPortalUrl(rule.source_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium text-teal-600 hover:underline"
            >
              Official application portal <FiExternalLink size={10} />
            </a>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------
const LOADING_STEPS = [
  { title: "Retrieving official gazettes & documents", detail: "RAG vector retrieval from verified government repositories" },
  { title: "Extracting statutory eligibility rules", detail: "Parsing turnover ceilings, investment criteria, and category rules" },
  { title: "Matching against your business profile", detail: "Cross-referencing enterprise type, state, and registered credentials" },
  { title: "Compiling readiness score & action items", detail: "Synthesizing gap analysis checklist and verified citations" },
];

export default function SchemeComplianceModal({
  scheme,
  isOpen,
  onClose,
  data,
  isLoading,
  error,
  onRetry,
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  /* Advance loading steps smoothly while processing */
  useEffect(() => {
    if (!isLoading) {
      setActiveStep(0);
      return;
    }
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev < LOADING_STEPS.length - 1 ? prev + 1 : prev));
    }, 1400);
    return () => clearInterval(interval);
  }, [isLoading]);

  /* Lock body scroll while open */
  useEffect(() => {
    document.body.style.overflow = isOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  /* Reset evidence accordion state when modal closes or scheme changes */
  useEffect(() => {
    if (!isOpen) setShowEvidence(false);
  }, [isOpen, scheme]);

  /* Escape key */
  const handleKey = useCallback(
    (e) => { if (e.key === "Escape") onClose(); },
    [onClose]
  );
  useEffect(() => {
    if (isOpen) window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, handleKey]);

  /* Derived rule groups */
  const notMet    = data?.rules?.filter((r) => r.verdict === "not_met")    ?? [];
  const needsInfo = data?.rules?.filter((r) => r.verdict === "needs_info") ?? [];
  const met       = data?.rules?.filter((r) => r.verdict === "met")        ?? [];

  const overallCfg = data ? (OVERALL[data.overall_status] || OVERALL.insufficient_data) : null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* ── Backdrop ───────────────────────────────────────────── */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-navy-950/60 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* ── Slide-up panel ─────────────────────────────────────── */}
          <motion.div
            key="panel"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 280 }}
            className="fixed inset-x-0 bottom-0 z-50 flex max-h-[92vh] flex-col rounded-t-2xl bg-bg shadow-elevated"
            role="dialog"
            aria-modal="true"
            aria-label={`Compliance check: ${scheme?.title}`}
          >
            {/* drag handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="h-1 w-10 rounded-full bg-border-strong" />
            </div>

            {/* ── Header ─────────────────────────────────────────────── */}
            <div className="flex items-start justify-between gap-4 border-b border-border px-5 pb-4 pt-2">
              <div className="min-w-0">
                <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wider text-ink-400">
                  Scheme Compliance Check
                </p>
                <h2 className="truncate text-lg font-bold leading-tight text-navy-900">
                  {scheme?.title}
                </h2>
                {scheme?.organization && (
                  <p className="mt-0.5 text-xs text-ink-500">{scheme.organization}</p>
                )}
              </div>
              <button
                onClick={onClose}
                className="mt-0.5 flex-shrink-0 rounded p-1.5 text-ink-500 transition hover:bg-surface-sunken hover:text-navy-900"
                aria-label="Close"
              >
                <FiX size={20} />
              </button>
            </div>

            {/* ── Scrollable body ─────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto px-5 py-5">

              {/* Loading State with Stage Tracker */}
              {isLoading && (
                <div className="mx-auto max-w-md py-12 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-teal-600 shadow-sm">
                    <Spinner size={30} className="text-teal-600" />
                  </div>
                  <h3 className="text-base font-bold text-navy-900">
                    Running Statutory Compliance Audit
                  </h3>
                  <p className="mt-1 text-xs text-ink-500">
                    Analyzing official scheme gazettes and cross-referencing against your enterprise profile...
                  </p>

                  {/* Progress steps */}
                  <div className="mt-6 space-y-2.5 text-left border border-border/80 rounded-xl bg-white p-4 shadow-xs">
                    {LOADING_STEPS.map((step, idx) => {
                      const isDone = idx < activeStep;
                      const isCurrent = idx === activeStep;
                      return (
                        <div key={idx} className="flex items-center gap-3">
                          <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                            isDone
                              ? "bg-success-100 text-success-600"
                              : isCurrent
                              ? "bg-teal-600 text-white animate-pulse"
                              : "bg-surface-sunken text-ink-400"
                          }`}>
                            {isDone ? <FiCheckCircle size={13} /> : idx + 1}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className={`text-xs font-semibold ${isCurrent ? "text-navy-900 font-bold" : isDone ? "text-ink-700" : "text-ink-400"}`}>
                              {step.title}
                            </p>
                            <p className="text-[10px] text-ink-400 truncate">{step.detail}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Error State with explicit Retry Action */}
              {!isLoading && error && (
                <div className="mx-auto max-w-md my-8 rounded-xl border border-error-100 bg-white p-6 text-center shadow-card">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-error-50 text-error-600">
                    <FiAlertCircle size={24} />
                  </div>
                  <h3 className="text-base font-bold text-navy-900">Compliance Assessment Unavailable</h3>
                  <p className="mt-1.5 text-xs text-ink-600 leading-relaxed">{error}</p>
                  <p className="mt-2 text-[11px] text-ink-400">
                    You can retry the automated verification or review the official portal directly.
                  </p>
                  <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
                    {onRetry && (
                      <button
                        type="button"
                        onClick={onRetry}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-teal-700"
                      >
                        <FiRefreshCw size={12} />
                        Retry Assessment
                      </button>
                    )}
                    {scheme?.official_url && (
                      <a
                        href={cleanPortalUrl(scheme.official_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-3.5 py-2 text-xs font-semibold text-navy-900 shadow-xs transition hover:bg-surface-sunken"
                      >
                        Official Portal <FiExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* Empty state when no data and not loading */}
              {!isLoading && !error && !data && (
                <div className="mx-auto max-w-md my-8 rounded-xl border border-border bg-white p-8 text-center shadow-card">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-sunken text-ink-400">
                    <FiShield size={24} />
                  </div>
                  <h3 className="text-base font-bold text-navy-900">Ready to Check Compliance</h3>
                  <p className="mt-1.5 text-xs text-ink-500 leading-relaxed">
                    Verify this scheme's statutory eligibility criteria, mandatory document checklist, and turnover limits against your profile.
                  </p>
                  {onRetry && (
                    <div className="mt-5">
                      <button
                        type="button"
                        onClick={onRetry}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-teal-700"
                      >
                        Run Compliance Check
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Results */}
              {!isLoading && !error && data && (
                <>
                  {/* ── Business Context Strip & Official Scheme Portal Link — Placed at the VERY TOP ── */}
                  {(() => {
                    const rawPortal = data.official_url || scheme?.official_url || scheme?.source_url || scheme?.url;
                    const portalUrl = cleanPortalUrl(rawPortal);
                    return (
                      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-md border border-teal-100 bg-white px-4 py-3 shadow-card">
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                          <div>
                            <p className="text-[10px] font-medium uppercase tracking-wider text-ink-400">Business Enterprise</p>
                            <p className="text-xs font-bold text-navy-900">{data.business_name || "Your Enterprise"}</p>
                          </div>
                          <div className="h-6 w-px bg-border" />
                          <div>
                            <p className="text-[10px] font-medium uppercase tracking-wider text-ink-400">MSME Classification</p>
                            <p className="text-xs font-semibold capitalize text-navy-900">{data.msme_classification}</p>
                          </div>
                        </div>
                        {portalUrl && (
                          <a
                            href={portalUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md bg-teal-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-teal-700"
                          >
                            Open Portal to Apply <FiExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    );
                  })()}

                  {/* ── Overall status banner ── */}
                  <div className={`mb-5 flex items-start gap-3 rounded-md border p-4 ${overallCfg.bg} ${overallCfg.border}`}>
                    <overallCfg.Icon size={20} className={`mt-0.5 flex-shrink-0 ${overallCfg.text}`} />
                    <div>
                      <p className={`text-sm font-bold ${overallCfg.text}`}>{overallCfg.label}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-ink-700">{data.overall_summary}</p>
                    </div>
                  </div>

                  {/* ── AI Advisory Summary ── */}
                  <div className="mb-5 rounded-md border border-teal-100 bg-teal-50/80 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-1.5">
                      <FiShield className="text-teal-700" size={16} />
                      <span className="text-xs font-bold text-teal-900 uppercase tracking-wide">
                        AI Compliance Advisory Summary
                      </span>
                    </div>
                    <p className="text-xs leading-relaxed text-teal-950">
                      Based on your business profile for <span className="font-semibold">{data.business_name}</span> ({data.msme_classification} enterprise),
                      {data.gap_missing_count > 0 ? (
                        <>
                          {" "}you have <span className="font-semibold text-error-700">{data.gap_missing_count} action item(s)</span> requiring attention before submitting your application. Follow the Readiness Checklist below to fix missing registrations or document uploads.
                        </>
                      ) : (
                        <>
                          {" "}your enterprise appears <span className="font-semibold text-success-700">fully ready</span> to apply under official scheme guidelines! Verify final documentation requirements before applying.
                        </>
                      )}
                    </p>
                  </div>

                  {/* ── Gap Analysis Checklist ── */}
                  {data.gap_analysis && data.gap_analysis.length > 0 && (
                    <GapAnalysisSection
                      gaps={data.gap_analysis}
                      metCount={data.gap_met_count}
                      missingCount={data.gap_missing_count}
                    />
                  )}

                  {/* ── Expandable RAG Government Evidence Accordion ── */}
                  <div className="mb-5">
                    <button
                      type="button"
                      onClick={() => setShowEvidence((prev) => !prev)}
                      className="flex w-full items-center justify-between rounded-md border border-border bg-surface-sunken px-4 py-3 text-xs font-semibold text-navy-900 transition hover:bg-white hover:shadow-card"
                    >
                      <div className="flex items-center gap-2">
                        <FiShield className="text-teal-600" size={15} />
                        <span>Official Government Evidence & Citations ({data.total_rules} Rules)</span>
                      </div>
                      <span className="text-xs font-bold text-teal-600">
                        {showEvidence ? "Hide Evidence ▲" : "Show Evidence ▼"}
                      </span>
                    </button>

                    <AnimatePresence>
                      {showEvidence && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-3 space-y-4 overflow-hidden"
                        >
                          {/* ── Aggregate progress ── */}
                          {data.total_rules > 0 && (
                            <div className="rounded-md border border-border bg-white p-4 shadow-card">
                              <div className="mb-3 flex flex-wrap items-center gap-2">
                                <span className="inline-flex items-center gap-1 rounded px-2.5 py-0.5 text-xs font-semibold bg-success-100 text-success-600">
                                  {data.met_count} Met
                                </span>
                                <span className="inline-flex items-center gap-1 rounded px-2.5 py-0.5 text-xs font-semibold bg-error-100 text-error-600">
                                  {data.not_met_count} Not Met
                                </span>
                                <span className="inline-flex items-center gap-1 rounded px-2.5 py-0.5 text-xs font-semibold bg-warning-100 text-warning-600">
                                  {data.needs_info_count} Needs Info
                                </span>
                                <span className="ml-auto font-data text-[11px] text-ink-400 self-center">
                                  {data.total_rules} requirement{data.total_rules !== 1 ? "s" : ""} assessed
                                </span>
                              </div>
                              <ProgressBar met={data.met_count} notMet={data.not_met_count} total={data.total_rules} />
                            </div>
                          )}

                          {/* ── RAG evidence note ── */}
                          {data.rag_evidence_note && (
                            <div className="flex items-start gap-2 rounded-md border border-warning-100 bg-warning-100/60 p-3 text-xs text-warning-600">
                              <FiAlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                              <p>{data.rag_evidence_note}</p>
                            </div>
                          )}

                          {/* ── Fallback notice ── */}
                          {data.used_fallback && (
                            <div className="flex items-start gap-2 rounded-md border border-teal-100 bg-teal-50 p-3 text-xs text-teal-700">
                              <FiInfo size={14} className="mt-0.5 flex-shrink-0" />
                              <p>
                                The RAG knowledge base returned limited results for this scheme.
                                The rules below are based on official published guidelines for this scheme.
                              </p>
                            </div>
                          )}

                          {/* ── NOT MET (most critical — shown first) ── */}
                          {notMet.length > 0 && (
                            <section>
                              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-error-600">
                                <FiXCircle size={15} /> Requirements Not Met ({notMet.length})
                              </h3>
                              <div className="space-y-3">
                                {notMet.map((rule, i) => (
                                  <RuleCard key={rule.rule_id} rule={rule} index={i} />
                                ))}
                              </div>
                            </section>
                          )}

                          {/* ── NEEDS INFO ── */}
                          {needsInfo.length > 0 && (
                            <section>
                              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-warning-600">
                                <FiAlertCircle size={15} /> Needs Verification ({needsInfo.length})
                              </h3>
                              <div className="space-y-3">
                                {needsInfo.map((rule, i) => (
                                  <RuleCard key={rule.rule_id} rule={rule} index={notMet.length + i} />
                                ))}
                              </div>
                            </section>
                          )}

                          {/* ── MET ── */}
                          {met.length > 0 && (
                            <section>
                              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-success-600">
                                <FiCheckCircle size={15} /> Requirements Met ({met.length})
                              </h3>
                              <div className="space-y-3">
                                {met.map((rule, i) => (
                                  <RuleCard key={rule.rule_id} rule={rule} index={notMet.length + needsInfo.length + i} />
                                ))}
                              </div>
                            </section>
                          )}

                          {/* ── No rules at all ── */}
                          {data.total_rules === 0 && (
                            <div className="rounded-md border border-border bg-white p-8 text-center">
                              <FiInfo size={22} className="mx-auto mb-2 text-ink-400" />
                              <p className="text-sm font-semibold text-navy-900">No rules extracted</p>
                              <p className="mt-1 text-xs text-ink-500">
                                The RAG knowledge base did not return official eligibility rules for this
                                scheme. Check the official portal directly.
                              </p>
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* ── Disclaimer ── */}
                  <div className="mt-2 rounded-md border border-border bg-surface-sunken p-4 text-xs leading-relaxed text-ink-500">
                    <p className="mb-1 font-semibold text-ink-700">
                      <FiInfo className="mr-1 inline" size={11} />
                      Guidance only
                    </p>
                    <p>{data.disclaimer}</p>
                    {data.rag_chunks_used > 0 && (
                      <p className="mt-2 font-data text-[10px] text-ink-400">
                        Assessment based on {data.rag_chunks_used} official government document
                        chunk{data.rag_chunks_used !== 1 ? "s" : ""} retrieved from the knowledge base.
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* bottom safe-area spacer */}
            <div className="h-4 flex-shrink-0" />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
