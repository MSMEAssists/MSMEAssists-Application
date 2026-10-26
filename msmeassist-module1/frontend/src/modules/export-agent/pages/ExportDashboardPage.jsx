import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  FiBriefcase,
  FiRefreshCw,
  FiArrowLeft,
  FiCheckCircle,
  FiDollarSign,
  FiGlobe,
  FiInfo,
  FiExternalLink,
  FiShield,
} from "react-icons/fi";
import AppLayout from "../../../layouts/AppLayout";
import Button from "../../../components/ui/Button";
import { PageLoader } from "../../../components/ui/Spinner";
import exportService from "../services/exportService";
import ExportReadinessCard from "../components/ExportReadinessCard";
import ExportSchemesList from "../components/ExportSchemesList";
import ExportRegistrationAudit from "../components/ExportRegistrationAudit";
import ExportDocumentChecklist from "../components/ExportDocumentChecklist";

export default function ExportDashboardPage() {
  const navigate = useNavigate();

  const [advisoryData, setAdvisoryData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAdvisory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await exportService.getExportAdvisory({});
      setAdvisoryData(response);
    } catch (err) {
      const msg = err?.response?.data?.error?.message || err?.response?.data?.detail || err?.message || "Failed to load Export & Global Trade Agent advisory.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAdvisory();
  }, []);

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <button
              onClick={() => navigate("/schemes")}
              className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-navy-900 transition"
            >
              <FiArrowLeft size={14} /> Back to Step 3: Explainable AI Recommendations
            </button>
            <h1 className="text-2xl font-bold tracking-tight text-navy-900 sm:text-3xl">
              Module 5: Export &amp; Global Trade Agent Dashboard
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              International trade readiness, RoDTEP &amp; DGFT export schemes, license pre-audit, and customs document checklist.
            </p>
          </div>

          <Button
            variant="secondary"
            onClick={fetchAdvisory}
            disabled={isLoading}
            className="flex items-center gap-1.5"
          >
            <FiRefreshCw className={isLoading ? "animate-spin" : ""} size={14} />
            <span>Refresh Advisory</span>
          </Button>
        </div>

        {/* Sequential 5-Step Pipeline Journey Header */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3 lg:grid-cols-6">
            {/* Step 1 */}
            <button
              onClick={() => navigate("/profile/completed")}
              className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-emerald-700 font-semibold hover:bg-slate-100 transition border border-slate-100"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <FiCheckCircle size={13} />
              </span>
              <span className="truncate">Step 1: Profile</span>
            </button>

            {/* Step 2 */}
            <button
              onClick={() => navigate("/schemes")}
              className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-emerald-700 font-semibold hover:bg-slate-100 transition border border-slate-100"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <FiCheckCircle size={13} />
              </span>
              <span className="truncate">Step 2: RAG Intelligence</span>
            </button>

            {/* Step 3 */}
            <button
              onClick={() => navigate("/schemes")}
              className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-emerald-700 font-semibold hover:bg-slate-100 transition border border-slate-100"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <FiCheckCircle size={13} />
              </span>
              <span className="truncate">Step 3: Recommendations</span>
            </button>

            {/* Step 4 */}
            <button
              onClick={() => navigate("/finance-loan")}
              className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-emerald-700 font-semibold hover:bg-slate-100 transition border border-slate-100"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <FiCheckCircle size={13} />
              </span>
              <span className="truncate">Step 4: Finance Agent</span>
            </button>

            {/* Step 5 ACTIVE */}
            <div className="flex items-center gap-2 font-bold transition px-3 py-2 rounded-md bg-teal-50 text-teal-800 ring-1 ring-teal-400">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-600 text-xs text-white">
                5
              </span>
              <span className="truncate">Step 5: Export Agent</span>
            </div>

            {/* Step 6 */}
            <button
              onClick={() => navigate("/decision")}
              className="flex items-center gap-2 rounded-md bg-indigo-50 px-3 py-2 text-left font-bold text-indigo-800 transition hover:bg-indigo-100 border border-indigo-200"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                6
              </span>
              <span className="truncate">Step 6: Decision Intelligence →</span>
            </button>
          </div>
        </div>

        {/* Business Profile Banner */}
        {advisoryData && (
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-navy-900 text-white">
                  <FiBriefcase size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-navy-900">{advisoryData.business_name}</h2>
                    <span className="rounded bg-teal-100 px-2 py-0.5 text-xs font-semibold text-teal-800 capitalize">
                      {advisoryData.msme_classification} Enterprise
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Live Export Signals: Sector ({advisoryData.industry || "General"}) • Location ({advisoryData.state || "India"})
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-500 font-data">
                <span className="rounded bg-slate-100 px-2.5 py-1">
                  <b>{advisoryData.schemes?.length || 0}</b> DGFT &amp; Commerce Schemes Evaluated
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="py-20 text-center">
            <PageLoader label="Analyzing DGFT regulations, RoDTEP rebates, and export licenses..." />
          </div>
        )}

        {/* Error Banner */}
        {!isLoading && error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-xs text-rose-800 shadow-xs">
            <p className="font-bold">Export Assessment Error</p>
            <p className="mt-1">{error}</p>
            <button onClick={fetchAdvisory} className="mt-3 font-bold text-rose-900 underline">
              Retry Advisory Assessment
            </button>
          </div>
        )}

        {/* Dashboard Content */}
        {!isLoading && !error && advisoryData && (
          <div className="space-y-8">
            {/* 1. Readiness Scorecard */}
            <ExportReadinessCard readiness={advisoryData.readiness} />

            {/* 2. DGFT & Export Promotion Schemes */}
            <ExportSchemesList schemes={advisoryData.schemes} />

            {/* 3. Mandatory License & Registration Audit */}
            <ExportRegistrationAudit licenses={advisoryData.licenses} />

            {/* 4. Customs & Shipping Document Checklist */}
            <ExportDocumentChecklist documents={advisoryData.documents} />

            {/* 5. Verified Official Portals */}
            {advisoryData.official_portals && advisoryData.official_portals.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <div className="flex items-center gap-2 mb-3">
                  <FiShield size={16} className="text-teal-700" />
                  <h3 className="text-sm font-bold text-navy-900">
                    Verified Government Foreign Trade Portals &amp; Resources
                  </h3>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {advisoryData.official_portals.map((p, i) => (
                    <a
                      key={i}
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col justify-between rounded-lg border border-slate-100 bg-slate-50/70 p-3 text-xs transition hover:border-teal-300 hover:bg-white hover:shadow-card"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-bold text-navy-900">{p.name}</span>
                          <FiExternalLink size={12} className="text-teal-600 shrink-0" />
                        </div>
                        <p className="text-[11px] text-slate-500">{p.purpose}</p>
                      </div>
                      <span className="mt-2 text-[10px] font-data text-teal-700 truncate">{p.url}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
              <p className="font-bold text-slate-700 mb-1 flex items-center gap-1">
                <FiInfo size={13} className="text-teal-600 inline" /> Official Foreign Trade Guidance Notice
              </p>
              <p>{advisoryData.disclaimer}</p>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
