import React from "react";
import { FiArrowRight, FiCheckCircle, FiExternalLink, FiTag, FiMapPin, FiGlobe } from "react-icons/fi";
import { cleanPortalUrl, validateDirectApplicationUrl } from "../../utils/urlSanitizer";

const RANK_BADGES = {
  1: { icon: "🥇", label: "#1" },
  2: { icon: "🥈", label: "#2" },
  3: { icon: "🥉", label: "#3" },
};

const normalizeTag = (value = "") => {
  const text = String(value)
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!text) return "";

  const friendlyMap = {
    micro: "Micro Enterprise",
    small: "Small Enterprise",
    medium: "Medium Enterprise",
    manufacturing: "Manufacturing",
    mfg: "Manufacturing",
    "food processing": "Food Processing",
    credit: "Credit Support",
    finance: "Finance Support",
    export: "Export Ready",
    technology: "Technology Oriented",
    women: "Women-led Business",
    service: "Services",
    trading: "Trading",
    startup: "Startup",
    "formal bank finance": "Formal Bank Finance",
    udyam: "Udyam Registered",
    scheme: "Scheme",
    subsidy: "Subsidy",
    loan: "Loan Support",
    business: "Business Support",
  };

  if (friendlyMap[text]) return friendlyMap[text];
  if (text.includes("micro")) return "Micro Enterprise";
  if (text.includes("small")) return "Small Enterprise";
  if (text.includes("medium")) return "Medium Enterprise";
  if (text.includes("manufactur")) return "Manufacturing";
  if (text.includes("credit") || text.includes("finance")) return "Credit Support";
  if (text.includes("export")) return "Export Ready";
  if (text.includes("tech")) return "Technology Oriented";

  return text
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const getReasoningText = (item) => {
  const rawText = item?.key_comparative_advantage || "";
  if (!rawText) {
    return "This scheme fits your business profile and the available government support signals.";
  }

  const clean = rawText
    .replace(/\s+/g, " ")
    .replace(/^(?:Ranked|This scheme|It|The scheme)\s+[^.]*?\b(?:because|based on|for|with|matches|supports)\b/i, "")
    .trim();

  const parts = clean.split(/(?<=[.!?])\s+/).filter(Boolean);
  const reason = parts.length > 1 ? `${parts[0]} ${parts[1]}` : parts[0] || rawText;
  return reason.length > 180 ? `${reason.slice(0, 177).trim()}...` : reason;
};

export default function BtlRankLadder({ rankings = [] }) {
  if (!rankings || rankings.length === 0) {
    return null;
  }

  return (
    <div className="space-y-5">
      {rankings.map((item) => {
        const badge = RANK_BADGES[item.rank] || { icon: "#", label: `#${item.rank}` };
        const tagList = [
          item.knowledge_type ? normalizeTag(item.knowledge_type) : "",
          ...Object.keys(item.feature_attributions || {}).slice(0, 2).map((key) => normalizeTag(key)),
        ].filter(Boolean).slice(0, 3);
        const directAppUrl = validateDirectApplicationUrl(item.official_application_url);
        const guidelinesUrl = item.official_url ? cleanPortalUrl(item.official_url) : null;

        return (
          <div
            key={item.scheme_id}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md"
          >
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-lg font-bold text-navy-900">
                  {badge.icon}
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                      {badge.label}
                    </span>
                    {item.scheme_scope === "STATE" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
                        <FiMapPin size={10} />
                        {item.state_jurisdiction ? `${item.state_jurisdiction} State Scheme` : "State Scheme"}
                      </span>
                    )}
                    {item.scheme_scope === "CENTRAL" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-800 border border-sky-200">
                        <FiGlobe size={10} />
                        Central / Pan-India Scheme
                      </span>
                    )}
                  </div>
                  <h3 className="mt-1 text-xl font-bold leading-tight text-navy-900">
                    {item.title}
                  </h3>
                </div>
              </div>

              {directAppUrl ? (
                <a
                  href={directAppUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 self-start rounded-lg bg-teal-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-teal-700"
                >
                  Apply Now <FiExternalLink size={13} />
                </a>
              ) : (
                <span
                  className="inline-flex items-center gap-1 self-start rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-500 italic"
                  title="Direct online application link unavailable for this scheme (may require applying through scheduled banks or offline)"
                >
                  Direct application link unavailable
                </span>
              )}
            </div>

            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
              <FiCheckCircle size={14} className="text-emerald-600" />
              Recommended for your business
            </div>

            {tagList.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {tagList.map((tag) => (
                  <span
                    key={`${item.scheme_id}-${tag}`}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-700"
                  >
                    <FiTag size={10} className="text-slate-500" />
                    {tag}
                  </span>
                ))}
              </div>
            )}

            <div className="mt-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Why this is recommended
              </p>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {getReasoningText(item)}
              </p>
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
              {guidelinesUrl ? (
                <a
                  href={guidelinesUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-navy-900 transition"
                  title="Official scheme guidelines and documentation"
                >
                  Official Guidelines & Scheme Details <FiExternalLink size={12} />
                </a>
              ) : (
                <span />
              )}
              {directAppUrl ? (
                <a
                  href={directAppUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-bold text-teal-700 transition hover:text-teal-900"
                >
                  Open Official Application Portal <FiExternalLink size={14} />
                </a>
              ) : (
                <span className="text-xs text-slate-400 italic">
                  Direct application link unavailable
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
