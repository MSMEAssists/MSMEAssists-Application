import React from "react";
import { FiTrendingUp, FiDollarSign, FiShield, FiPercent, FiActivity } from "react-icons/fi";

export default function FinancialSummaryCard({ summary }) {
  if (!summary) return null;

  const ratingColors = {
    HIGH: "bg-emerald-100 text-emerald-800 border-emerald-300",
    MODERATE: "bg-teal-100 text-teal-800 border-teal-300",
    CONSTRAINED: "bg-amber-100 text-amber-800 border-amber-300",
    LOW: "bg-rose-100 text-rose-800 border-rose-300",
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-600 text-white font-bold">
            <FiActivity size={20} />
          </div>
          <div>
            <h2 className="text-base font-bold text-navy-900">Financial Situation & Insights</h2>
            <p className="text-xs text-slate-500">Automated financial health score and cash-flow estimation</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">Health Score</span>
            <span className="text-xl font-extrabold text-navy-900">{summary.financial_health_score}/100</span>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-xs font-bold ${
              ratingColors[summary.repayment_capacity_rating] || "bg-slate-100 text-slate-800"
            }`}
          >
            {summary.repayment_capacity_rating} Repayment Capacity
          </span>
        </div>
      </div>

      {/* Grid of Financial Metrics */}
      <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricBox label="Annual Revenue" value={summary.annual_revenue} sub={`Monthly: ${summary.monthly_revenue}`} />
        <MetricBox label="Monthly Operating Expenses" value={summary.monthly_expenses} sub={`Margin: ${summary.gross_margin_pct}%`} />
        <MetricBox label="Monthly Net Profit" value={summary.monthly_profit} sub={`Net Cash: ${summary.net_cash_flow}`} />
        <MetricBox label="DSCR (Coverage Ratio)" value={summary.estimated_dscr} sub="Debt Service Capacity" />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 border-t border-slate-100 pt-4">
        <MetricBox label="Working Capital Req." value={summary.working_capital_requirement} />
        <MetricBox label="Capital Investment Req." value={summary.investment_requirement} />
        <MetricBox label="Calculated Funding Gap" value={summary.funding_requirement} highlight />
      </div>
    </div>
  );
}

function MetricBox({ label, value, sub, highlight }) {
  return (
    <div className={`rounded-lg p-3 ${highlight ? "bg-teal-50 border border-teal-200" : "bg-slate-50"}`}>
      <span className="block text-[11px] font-medium text-slate-500">{label}</span>
      <span className={`block text-base font-bold ${highlight ? "text-teal-800" : "text-navy-900"}`}>{value}</span>
      {sub && <span className="block text-[10px] text-slate-400 mt-0.5">{sub}</span>}
    </div>
  );
}
