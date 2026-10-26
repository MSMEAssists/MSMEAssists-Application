import React from "react";
import { FiTarget, FiCreditCard, FiAlertCircle } from "react-icons/fi";

export default function LoanRequirementCard({ requirement }) {
  if (!requirement) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy-900 text-white font-bold">
            <FiTarget size={18} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-navy-900">Loan Requirement Identification</h3>
            <p className="text-xs text-slate-500">Automated mapping based on business goals & funding gap</p>
          </div>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            requirement.urgency === "HIGH"
              ? "bg-amber-100 text-amber-800"
              : "bg-slate-100 text-slate-700"
          }`}
        >
          {requirement.urgency} Urgency
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg bg-indigo-50/70 p-3.5 border border-indigo-100">
          <span className="block text-[11px] font-semibold text-indigo-700 uppercase tracking-wider">
            Required Financing Amount
          </span>
          <span className="mt-1 block text-xl font-extrabold text-navy-900">
            {requirement.required_amount}
          </span>
        </div>

        <div className="rounded-lg bg-slate-50 p-3.5">
          <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Primary Loan Purpose
          </span>
          <span className="mt-1 block text-sm font-bold text-navy-900">
            {requirement.purpose}
          </span>
        </div>

        <div className="rounded-lg bg-slate-50 p-3.5">
          <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Target Category
          </span>
          <span className="mt-1 block text-sm font-bold text-teal-800">
            {requirement.loan_type}
          </span>
        </div>
      </div>
    </div>
  );
}
