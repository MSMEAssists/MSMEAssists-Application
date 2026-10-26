import React from "react";
import { FiAward, FiExternalLink, FiDollarSign, FiShield } from "react-icons/fi";

export default function ExportSchemesList({ schemes }) {
  if (!schemes || schemes.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FiAward className="text-teal-700" size={18} />
        <h3 className="text-base font-bold text-navy-900">
          Government Export Promotion & Rebate Schemes ({schemes.length})
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {schemes.map((scheme) => {
          const isEligible = scheme.eligibility_status === "eligible";
          return (
            <div
              key={scheme.id}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-teal-300 hover:shadow-card"
            >
              <div>
                {/* Category & Status */}
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded bg-teal-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-teal-800">
                    {scheme.category}
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-[11px] font-semibold ${
                      isEligible
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {isEligible ? "Ready to Claim" : "Action Needed"}
                  </span>
                </div>

                {/* Scheme Title & Org */}
                <h4 className="text-sm font-bold text-navy-900 mb-1">{scheme.title}</h4>
                <p className="text-[11px] text-slate-500 mb-3 flex items-center gap-1">
                  <FiShield size={11} className="text-teal-600 shrink-0" />
                  {scheme.organization}
                </p>

                {/* Description */}
                <p className="text-xs text-slate-600 mb-3 leading-relaxed">
                  {scheme.benefit_description}
                </p>

                {/* Estimated Financial Benefit */}
                <div className="mb-3 rounded-lg bg-emerald-50/80 border border-emerald-100 px-3 py-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 block">
                    Estimated Incentive / Benefit
                  </span>
                  <span className="text-xs font-bold text-emerald-900 flex items-center gap-1 mt-0.5">
                    <FiDollarSign size={12} />
                    {scheme.estimated_benefit}
                  </span>
                </div>

                {/* Action instruction */}
                {scheme.what_to_do && (
                  <p className="text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100">
                    <span className="font-bold text-navy-900">How to claim: </span>
                    {scheme.what_to_do}
                  </p>
                )}
              </div>

              {/* Portal link */}
              {scheme.official_url && (
                <div className="mt-4 pt-3 border-t border-slate-100 text-right">
                  <a
                    href={scheme.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-bold text-teal-700 hover:text-teal-900"
                  >
                    <span>Official DGFT Portal</span>
                    <FiExternalLink size={12} />
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
