import React from "react";
import { FiX, FiCheckCircle, FiFileText, FiInfo, FiExternalLink } from "react-icons/fi";

export default function WhyThisOptionModal({ option, onClose }) {
  if (!option) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-900/60 p-4 backdrop-blur-xs">
      <div className="w-full max-w-xl rounded-xl bg-white p-6 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <span className="inline-block rounded bg-teal-100 px-2 py-0.5 text-[11px] font-bold text-teal-800 uppercase tracking-wider mb-1">
              Explainable AI Financial Advisory
            </span>
            <h3 className="text-lg font-bold text-navy-900">{option.name}</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-navy-900"
          >
            <FiX size={20} />
          </button>
        </div>

        <div className="mt-4 space-y-4 text-xs text-slate-600">
          <div className="rounded-lg bg-teal-50/80 p-4 border border-teal-200">
            <h4 className="font-bold text-teal-900 flex items-center gap-1.5 text-sm mb-1.5">
              <FiCheckCircle size={16} className="text-teal-700" /> Why is this option recommended for you?
            </h4>
            <p className="leading-relaxed text-teal-950 font-medium">{option.reason}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md bg-slate-50 p-3">
              <span className="font-semibold text-slate-500 block">Eligibility Signal</span>
              <span className="font-bold text-navy-900">{option.eligibility}</span>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <span className="font-semibold text-slate-500 block">Financial Suitability Score</span>
              <span className="font-bold text-indigo-700 text-sm">
                {(option.financial_suitability_score * 100).toFixed(0)}% Match
              </span>
            </div>
          </div>

          <div>
            <h5 className="font-bold text-navy-900 flex items-center gap-1 mb-2">
              <FiFileText size={14} className="text-teal-600" /> Mandatory Documents Required by Lender
            </h5>
            <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {option.documents?.map((doc, i) => (
                <li key={i} className="flex items-center gap-2 rounded bg-slate-50 px-2.5 py-1.5 text-slate-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-teal-600 shrink-0" />
                  <span>{doc}</span>
                </li>
              ))}
            </ul>
          </div>

          {option.official_url && (
            <div className="pt-2 text-right">
              <a
                href={option.official_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs font-bold text-teal-700 hover:underline"
              >
                <span>Official Scheme Documentation ({option.source_organization})</span>
                <FiExternalLink size={13} />
              </a>
            </div>
          )}
        </div>

        <div className="mt-6 border-t border-slate-100 pt-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-navy-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
          >
            Close Explanation
          </button>
        </div>
      </div>
    </div>
  );
}
