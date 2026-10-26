import React, { useState } from "react";
import { FiHelpCircle, FiEdit3, FiRefreshCw, FiCheck } from "react-icons/fi";

export default function MissingInfoAlert({ missingItems = [], onUpdateInputs, isSubmitting }) {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    monthly_expenses_inr: "",
    requested_amount_inr: "",
    available_capital_inr: "",
    existing_monthly_emi_inr: "",
  });

  if (!missingItems || missingItems.length === 0) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanData = {};
    if (formData.monthly_expenses_inr) cleanData.monthly_expenses_inr = parseFloat(formData.monthly_expenses_inr);
    if (formData.requested_amount_inr) cleanData.requested_amount_inr = parseFloat(formData.requested_amount_inr);
    if (formData.available_capital_inr) cleanData.available_capital_inr = parseFloat(formData.available_capital_inr);
    if (formData.existing_monthly_emi_inr) cleanData.existing_monthly_emi_inr = parseFloat(formData.existing_monthly_emi_inr);

    if (onUpdateInputs) {
      onUpdateInputs(cleanData);
    }
  };

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-5 shadow-xs space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-amber-100 pb-3">
        <div className="flex items-start gap-2.5">
          <FiHelpCircle size={18} className="text-amber-700 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-sm font-bold text-amber-900">Missing Information Detected</h4>
            <p className="text-xs text-amber-800">
              The agent used industry defaults for missing metrics. You can supply exact numbers below for higher advisory precision.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1.5 rounded-md bg-amber-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-800 transition"
        >
          <FiEdit3 size={14} />
          <span>{showForm ? "Hide Form" : "Provide Exact Details"}</span>
        </button>
      </div>

      <ul className="space-y-1 text-xs text-amber-900 font-medium pl-6 list-disc">
        {missingItems.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>

      {showForm && (
        <form onSubmit={handleSubmit} className="mt-4 border-t border-amber-200 pt-4 space-y-4 bg-white p-4 rounded-lg border border-amber-200">
          <h5 className="text-xs font-bold text-navy-900 uppercase tracking-wider">Specify Exact Financial Figures (Optional)</h5>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
            <div>
              <label className="block text-slate-600 font-medium mb-1">Monthly Operating Expenses (INR)</label>
              <input
                type="number"
                placeholder="e.g. 250000"
                value={formData.monthly_expenses_inr}
                onChange={(e) => setFormData({ ...formData, monthly_expenses_inr: e.target.value })}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1">Desired Loan Amount (INR)</label>
              <input
                type="number"
                placeholder="e.g. 1500000"
                value={formData.requested_amount_inr}
                onChange={(e) => setFormData({ ...formData, requested_amount_inr: e.target.value })}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1">Available Liquid Savings / Capital (INR)</label>
              <input
                type="number"
                placeholder="e.g. 500000"
                value={formData.available_capital_inr}
                onChange={(e) => setFormData({ ...formData, available_capital_inr: e.target.value })}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1">Existing Monthly Loan EMI (INR)</label>
              <input
                type="number"
                placeholder="e.g. 25000"
                value={formData.existing_monthly_emi_inr}
                onChange={(e) => setFormData({ ...formData, existing_monthly_emi_inr: e.target.value })}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 px-4 py-2 text-xs font-bold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              <FiRefreshCw className={isSubmitting ? "animate-spin" : ""} size={14} />
              <span>Re-analyze Financial Position</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
