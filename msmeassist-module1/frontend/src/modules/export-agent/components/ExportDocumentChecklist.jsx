import React from "react";
import { FiCheckCircle, FiClock, FiFileText } from "react-icons/fi";

export default function ExportDocumentChecklist({ documents }) {
  if (!documents || documents.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
      <div className="flex items-center gap-2 mb-4">
        <FiFileText size={18} className="text-teal-700" />
        <h3 className="text-base font-bold text-navy-900">
          Export Shipping & Customs Document Checklist ({documents.length})
        </h3>
      </div>

      <div className="space-y-3">
        {documents.map((doc, idx) => {
          const isReady = doc.status === "ready";
          return (
            <div
              key={idx}
              className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50/70 p-3.5"
            >
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 shrink-0 ${isReady ? "text-emerald-600" : "text-amber-600"}`}>
                  {isReady ? <FiCheckCircle size={15} /> : <FiClock size={15} />}
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold text-navy-900">{doc.document_name}</span>
                    <span className="rounded bg-teal-100 px-2 py-0.5 text-[10px] font-bold text-teal-800">
                      {doc.stage}
                    </span>
                    {doc.mandatory && (
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[9px] font-bold uppercase text-rose-700">
                        Mandatory
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-600">{doc.description}</p>
                </div>
              </div>

              <span
                className={`shrink-0 rounded px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${
                  isReady
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {isReady ? "Ready" : "Pending"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
