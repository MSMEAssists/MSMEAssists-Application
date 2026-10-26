import React from "react";
import { FiAlertTriangle, FiCheckSquare, FiInfo } from "react-icons/fi";

export default function FinancialRisksCard({ risks = [], improvements = [] }) {
  if ((!risks || risks.length === 0) && (!improvements || improvements.length === 0)) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {/* Financial Risks Card */}
      <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-5 shadow-xs">
        <div className="flex items-center gap-2 font-bold text-rose-900 border-b border-rose-100 pb-3 text-sm">
          <FiAlertTriangle size={18} className="text-rose-600 shrink-0" />
          <span>Financial Risk Factors</span>
        </div>
        <ul className="mt-3 space-y-2.5 text-xs text-rose-950">
          {risks.length > 0 ? (
            risks.map((r, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-rose-600 shrink-0" />
                <span className="leading-relaxed">{r}</span>
              </li>
            ))
          ) : (
            <li className="text-emerald-700 font-semibold">
              ✓ No critical financial risk factors detected based on reported figures.
            </li>
          )}
        </ul>
      </div>

      {/* Financial Improvement Areas */}
      <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-5 shadow-xs">
        <div className="flex items-center gap-2 font-bold text-teal-900 border-b border-teal-100 pb-3 text-sm">
          <FiCheckSquare size={18} className="text-teal-600 shrink-0" />
          <span>Actionable Improvement Areas</span>
        </div>
        <ul className="mt-3 space-y-2.5 text-xs text-teal-950">
          {improvements.map((imp, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-teal-600 shrink-0" />
              <span className="leading-relaxed">{imp}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
