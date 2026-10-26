import React from "react";
import { FiCheckCircle, FiXCircle, FiAlertCircle, FiExternalLink, FiFileText } from "react-icons/fi";

export default function ExportRegistrationAudit({ licenses }) {
  if (!licenses || licenses.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
      <div className="flex items-center gap-2 mb-4">
        <FiFileText size={18} className="text-teal-700" />
        <h3 className="text-base font-bold text-navy-900">
          Mandatory Export Licenses & Registration Audit ({licenses.length})
        </h3>
      </div>

      <div className="divide-y divide-slate-100">
        {licenses.map((lic, i) => {
          const isMet = lic.status === "met";
          const isWarning = lic.status === "needs_verification";
          return (
            <div key={i} className="py-3.5 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 rounded-full p-1 ${
                      isMet
                        ? "bg-emerald-100 text-emerald-600"
                        : isWarning
                        ? "bg-amber-100 text-amber-600"
                        : "bg-rose-100 text-rose-600"
                    }`}
                  >
                    {isMet ? (
                      <FiCheckCircle size={14} />
                    ) : isWarning ? (
                      <FiAlertCircle size={14} />
                    ) : (
                      <FiXCircle size={14} />
                    )}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-xs font-bold text-navy-900">{lic.name}</h4>
                      <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {lic.authority}
                      </span>
                    </div>

                    <p className="mt-0.5 text-xs text-slate-600">{lic.description}</p>

                    {lic.profile_value && (
                      <p className="mt-1 text-[11px] text-slate-500 font-data">
                        Profile verification: <span className="font-semibold text-navy-900">{lic.profile_value}</span>
                      </p>
                    )}

                    {!isMet && lic.how_to_fix && (
                      <div className="mt-2 rounded bg-amber-50 p-2.5 border border-amber-100 text-xs text-amber-900">
                        <span className="font-bold text-amber-800 uppercase text-[10px] block mb-0.5">What to do:</span>
                        {lic.how_to_fix}
                      </div>
                    )}
                  </div>
                </div>

                {lic.portal_url && (
                  <a
                    href={lic.portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-teal-700 hover:underline"
                  >
                    <span>Apply / Verify</span>
                    <FiExternalLink size={11} />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
