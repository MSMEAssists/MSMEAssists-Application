import React, { useState } from "react";
import { FiAward, FiInfo, FiChevronDown, FiChevronUp, FiCheck, FiExternalLink } from "react-icons/fi";
import WhyThisOptionModal from "./WhyThisOptionModal";

export default function RecommendedOptionsList({ options = [] }) {
  const [selectedOption, setSelectedOption] = useState(null);
  const [expandedId, setExpandedId] = useState(options[0]?.id || null);

  if (!options || options.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-sm text-slate-500">No suitable loan options identified based on current profile parameters.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-navy-900">Recommended Financing & Loan Options</h2>
          <p className="text-xs text-slate-500">
            Tailored government schemes, credit guarantees, and term loans evaluated for your profile
          </p>
        </div>
        <span className="text-xs font-semibold text-slate-400">
          Showing Top {options.length} Financial Recommendations
        </span>
      </div>

      <div className="space-y-3.5">
        {options.map((opt, idx) => {
          const isExpanded = expandedId === opt.id;
          return (
            <div
              key={opt.id || idx}
              className={`rounded-xl border transition bg-white shadow-xs ${
                idx === 0 ? "border-teal-400 ring-1 ring-teal-300" : "border-slate-200"
              }`}
            >
              {/* Card Header */}
              <div className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                        idx === 0
                          ? "bg-teal-600 text-white"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      #{opt.btl_rank || idx + 1}
                    </span>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-bold text-navy-900">{opt.name}</h3>
                        <span className="rounded bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 border border-indigo-100">
                          {opt.type}
                        </span>
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                          {opt.category}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600 line-clamp-2">{opt.reason}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedOption(opt)}
                      className="inline-flex items-center gap-1 rounded-md bg-teal-50 px-2.5 py-1.5 text-xs font-bold text-teal-800 border border-teal-200 hover:bg-teal-100 transition"
                    >
                      <FiInfo size={14} />
                      <span>Why This Option?</span>
                    </button>

                    <button
                      onClick={() => setExpandedId(isExpanded ? null : opt.id)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-navy-900"
                    >
                      {isExpanded ? <FiChevronUp size={18} /> : <FiChevronDown size={18} />}
                    </button>
                  </div>
                </div>

                {/* Key Metrics Strip */}
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 bg-slate-50 p-3 rounded-lg text-xs">
                  <div>
                    <span className="block text-[10px] font-medium text-slate-400 uppercase">Max Amount</span>
                    <span className="font-bold text-navy-900">{opt.amount}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-medium text-slate-400 uppercase">Interest Rate</span>
                    <span className="font-bold text-teal-700">{opt.interest_rate}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-medium text-slate-400 uppercase">Tenure</span>
                    <span className="font-bold text-navy-900">{opt.tenure}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-medium text-slate-400 uppercase">Suitability</span>
                    <span className="font-bold text-indigo-700">
                      {(opt.financial_suitability_score * 100).toFixed(0)}% Match
                    </span>
                  </div>
                </div>
              </div>

              {/* Accordion Expandable Details */}
              {isExpanded && (
                <div className="border-t border-slate-100 bg-slate-50/50 p-5 space-y-4 text-xs">
                  <div>
                    <h4 className="font-bold text-navy-900 mb-1">Eligibility Criteria</h4>
                    <p className="text-slate-600">{opt.eligibility}</p>
                  </div>

                  <div>
                    <h4 className="font-bold text-navy-900 mb-2">Required Documentation</h4>
                    <div className="flex flex-wrap gap-2">
                      {opt.documents?.map((d, i) => (
                        <span key={i} className="inline-flex items-center gap-1 rounded bg-white px-2.5 py-1 border border-slate-200 text-slate-700">
                          <FiCheck size={12} className="text-teal-600" />
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>

                  {opt.official_url && (
                    <div className="pt-2 flex justify-between items-center border-t border-slate-200">
                      <span className="text-[11px] text-slate-400">Source: {opt.source_organization}</span>
                      <a
                        href={opt.official_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-bold text-teal-700 hover:underline"
                      >
                        <span>Official Portal</span>
                        <FiExternalLink size={12} />
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedOption && (
        <WhyThisOptionModal option={selectedOption} onClose={() => setSelectedOption(null)} />
      )}
    </div>
  );
}
