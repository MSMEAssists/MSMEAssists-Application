import { FiExternalLink, FiAward, FiFileText, FiCheckCircle, FiAlertTriangle, FiShield } from "react-icons/fi";
import ProvenanceList, { ProvenanceRow } from "./ProvenanceList";
import { cleanPortalUrl, validateDirectApplicationUrl } from "../../utils/urlSanitizer";

const TYPE_STYLES = {
  SCHEME: { bg: "bg-teal-100", text: "text-teal-700", label: "Scheme" },
  LOAN: { bg: "bg-blue-100", text: "text-blue-700", label: "Loan / Credit" },
  SUBSIDY: { bg: "bg-saffron-100", text: "text-saffron-600", label: "Subsidy" },
  GRANT: { bg: "bg-purple-100", text: "text-purple-700", label: "Grant" },
  PROCUREMENT: { bg: "bg-indigo-100", text: "text-indigo-700", label: "Procurement / Tender" },
  NOTIFICATION: { bg: "bg-amber-100", text: "text-amber-700", label: "Notification" },
  POLICY: { bg: "bg-emerald-100", text: "text-emerald-700", label: "Policy" },
  OTHER: { bg: "bg-surface-sunken", text: "text-ink-700", label: "Program" },
};

const ELIGIBILITY_STYLES = {
  eligible: { bg: "bg-success-100", text: "text-success-600", label: "Eligible" },
  conditionally_eligible: { bg: "bg-teal-100", text: "text-teal-700", label: "Conditionally Eligible" },
  potentially_eligible: { bg: "bg-saffron-100", text: "text-saffron-600", label: "Potentially Eligible" },
  not_eligible: { bg: "bg-error-100", text: "text-error-600", label: "Not Eligible" },
  insufficient_evidence: { bg: "bg-warning-100", text: "text-warning-600", label: "Insufficient Evidence" },
};

function formatAttributeTag(attr) {
  return attr
    .replace(/_/g, " ")
    .replace(/:/g, ": ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatPercent(score) {
  if (score == null || Number.isNaN(Number(score))) return null;
  return `${Math.round(Number(score) * 100)}%`;
}

function Section({ title, children }) {
  if (!children) return null;
  return (
    <div className="mb-4">
      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-ink-400">
        {title}
      </span>
      {children}
    </div>
  );
}

export default function SchemeCard({ scheme, onCheckCompliance }) {
  const typeStyle = TYPE_STYLES[scheme.knowledge_type?.toUpperCase()] || TYPE_STYLES.OTHER;
  const statusKey = scheme.eligibility_status || "potentially_eligible";
  const statusStyle = ELIGIBILITY_STYLES[statusKey] || ELIGIBILITY_STYLES.potentially_eligible;
  const isInsufficient = statusKey === "insufficient_evidence";
  const recommendationPct = formatPercent(scheme.recommendation_score);
  const notes = scheme.insufficient_evidence_notes || [];

  return (
    <div className="flex flex-col justify-between rounded-md border border-border bg-white p-5 shadow-card transition-all hover:border-border-strong hover:shadow-elevated">
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`inline-flex items-center gap-1 rounded px-2.5 py-0.5 text-xs font-semibold ${typeStyle.bg} ${typeStyle.text}`}>
              <FiAward size={12} />
              {typeStyle.label}
            </span>
            <span className={`inline-flex items-center rounded px-2.5 py-0.5 text-xs font-semibold ${statusStyle.bg} ${statusStyle.text}`}>
              {statusStyle.label}
            </span>
            {scheme.page_number != null && (
              <span className="inline-flex items-center gap-1 rounded bg-surface-sunken px-2 py-0.5 text-xs font-medium text-ink-500">
                <FiFileText size={11} /> Page {scheme.page_number}
              </span>
            )}
          </div>
          {recommendationPct && (
            <span className="rounded bg-teal-50 px-2 py-0.5 font-data text-[11px] font-medium text-teal-700">
              Recommendation {recommendationPct}
            </span>
          )}
        </div>

        <h3 className="mb-1.5 text-base font-bold leading-snug text-navy-900">
          {scheme.title}
        </h3>
        <p className="mb-3 text-xs font-medium text-ink-500">
          {scheme.organization}
        </p>

        {isInsufficient && (
          <div className="mb-4 flex items-start gap-2 rounded-md border border-warning-100 bg-warning-100/60 p-3 text-xs text-warning-600">
            <FiAlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-navy-900">Insufficient official evidence</p>
              {notes.length > 0 ? (
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink-700">
                  {notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-ink-700">
                  Retrieved official sources do not contain enough evidence to confirm eligibility for this profile.
                </p>
              )}
            </div>
          </div>
        )}

        {!isInsufficient && notes.length > 0 && (
          <div className="mb-4 rounded-md border border-border bg-surface-sunken p-3 text-xs text-ink-700">
            <p className="mb-1 font-semibold text-navy-900">Evidence notes</p>
            <ul className="list-disc space-y-0.5 pl-4">
              {notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {(scheme.snippet || scheme.description) && (
          <p className="mb-4 text-xs leading-relaxed text-ink-700">
            {scheme.snippet || scheme.description}
          </p>
        )}

        {scheme.why_it_matches && scheme.why_it_matches.length > 0 && (
          <Section title="Why it matches">
            <ul className="space-y-1">
              {scheme.why_it_matches.map((reason) => (
                <li key={reason} className="flex items-start gap-1.5 text-xs text-ink-700">
                  <FiCheckCircle size={12} className="mt-0.5 flex-shrink-0 text-teal-600" />
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {scheme.aligned_attributes && scheme.aligned_attributes.length > 0 && (
          <Section title="Profile alignment signals">
            <div className="flex flex-wrap gap-1">
              {scheme.aligned_attributes.map((attr) => (
                <span
                  key={attr}
                  className="inline-flex items-center gap-1 rounded border border-teal-100/80 bg-teal-50/70 px-2 py-0.5 text-[11px] font-medium text-teal-700"
                >
                  <FiCheckCircle size={10} className="text-teal-600" />
                  {formatAttributeTag(attr)}
                </span>
              ))}
            </div>
          </Section>
        )}

        {scheme.key_eligibility_criteria?.length > 0 && (
          <Section title="Eligibility conditions">
            <ProvenanceList items={scheme.key_eligibility_criteria} />
          </Section>
        )}

        {scheme.unmet_or_conflicting_conditions?.length > 0 && (
          <Section title="Unmet or conflicting conditions">
            <ProvenanceList items={scheme.unmet_or_conflicting_conditions} />
          </Section>
        )}

        {scheme.benefits_available?.length > 0 && (
          <Section title="Benefits">
            <ProvenanceList items={scheme.benefits_available} />
          </Section>
        )}

        {scheme.required_documents?.length > 0 && (
          <Section title="Required documents">
            <ProvenanceList items={scheme.required_documents} />
          </Section>
        )}

        {scheme.application_process && (
          <Section title="Application / process">
            <ul>
              <ProvenanceRow item={scheme.application_process} />
            </ul>
          </Section>
        )}
      </div>

      <div className="mt-1 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
        <div className="font-data text-[11px] text-ink-400">
          <div>Official Government Source</div>
          {(scheme.id || scheme.page_number != null) && (
            <div className="mt-0.5">
              {scheme.id && <span>Source chunk {scheme.id}</span>}
              {scheme.id && scheme.page_number != null && <span> · </span>}
              {scheme.page_number != null && <span>Page {scheme.page_number}</span>}
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          {onCheckCompliance && (
            <button
              onClick={() => onCheckCompliance(scheme)}
              className="inline-flex items-center gap-1.5 rounded border border-teal-600 px-3 py-1.5 text-xs font-semibold text-teal-600 transition hover:bg-teal-600 hover:text-white"
            >
              <FiShield size={12} />
              Check My Compliance
            </button>
          )}
          {scheme.official_url && (
            <a
              href={cleanPortalUrl(scheme.official_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-teal-700 hover:underline"
              title="Official scheme guidelines and documentation"
            >
              Official Guidelines <FiExternalLink size={12} />
            </a>
          )}
          {(() => {
            const directAppUrl = validateDirectApplicationUrl(scheme.official_application_url);
            if (directAppUrl) {
              return (
                <a
                  href={directAppUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-teal-700"
                >
                  Apply Now <FiExternalLink size={13} />
                </a>
              );
            }
            return (
              <span
                className="inline-flex items-center gap-1 text-xs text-slate-400 italic"
                title="This scheme does not provide a direct online application portal (may require offline bank application or departmental submission)"
              >
                Direct application link unavailable
              </span>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
