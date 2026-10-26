import React from "react";
import { FiCheckCircle, FiAlertCircle, FiTrendingUp, FiGlobe } from "react-icons/fi";

export default function ExportReadinessCard({ readiness }) {
  if (!readiness) return null;

  const score = readiness.score;
  const isHigh = score >= 75;
  const isModerate = score >= 45 && score < 75;

  const badgeColor = isHigh
    ? "bg-emerald-100 text-emerald-800 border-emerald-300"
    : isModerate
    ? "bg-amber-100 text-amber-800 border-amber-300"
    : "bg-rose-100 text-rose-800 border-rose-300";

  const barColor = isHigh
    ? "bg-emerald-600"
    : isModerate
    ? "bg-amber-500"
    : "bg-rose-500";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-teal-700 text-white shadow-xs">
            <FiGlobe size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-navy-900">Export Readiness Scorecard</h2>
              <span className={`rounded-full border px-3 py-0.5 text-xs font-bold ${badgeColor}`}>
                {readiness.level}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">{readiness.summary}</p>
          </div>
        </div>

        {/* Big Score Counter */}
        <div className="flex items-baseline gap-1 bg-slate-50 px-4 py-2 rounded-xl border border-slate-100">
          <span className="text-3xl font-extrabold text-navy-900">{score}</span>
          <span className="text-xs font-bold text-slate-400">/ 100</span>
        </div>
      </div>

      {/* Score Meter Bar */}
      <div className="mt-4">
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full transition-all duration-500 ${barColor}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>

      {/* Strengths & Gaps breakdown */}
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Enterprise Advantages */}
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-4">
          <div className="flex items-center gap-2 mb-2 text-emerald-800 font-bold text-xs uppercase tracking-wider">
            <FiCheckCircle size={14} />
            <span>Verified Export Signals ({readiness.strengths?.length || 0})</span>
          </div>
          <ul className="space-y-1.5 text-xs text-emerald-950">
            {(readiness.strengths || []).map((s, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-emerald-600 font-bold">•</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Readiness Gaps */}
        <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-4">
          <div className="flex items-center gap-2 mb-2 text-amber-800 font-bold text-xs uppercase tracking-wider">
            <FiAlertCircle size={14} />
            <span>Action Required Items ({readiness.gaps?.length || 0})</span>
          </div>
          <ul className="space-y-1.5 text-xs text-amber-950">
            {(readiness.gaps || []).map((g, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-amber-600 font-bold">•</span>
                <span>{g}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
