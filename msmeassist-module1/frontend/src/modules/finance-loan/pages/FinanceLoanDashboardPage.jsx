import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  FiBriefcase,
  FiRefreshCw,
  FiArrowLeft,
  FiCheckCircle,
  FiDollarSign,
  FiShield,
  FiFileText,
  FiInfo,
  FiAlertTriangle,
  FiGlobe,
} from "react-icons/fi";
import AppLayout from "../../../layouts/AppLayout";
import Button from "../../../components/ui/Button";
import { PageLoader } from "../../../components/ui/Spinner";
import financeLoanService from "../services/financeLoanService";
import FinancialSummaryCard from "../components/FinancialSummaryCard";
import LoanRequirementCard from "../components/LoanRequirementCard";
import RecommendedOptionsList from "../components/RecommendedOptionsList";
import FinancialRisksCard from "../components/FinancialRisksCard";
import MissingInfoAlert from "../components/MissingInfoAlert";

export default function FinanceLoanDashboardPage() {
  const navigate = useNavigate();

  const [advisoryData, setAdvisoryData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // User input overrides for missing info form
  const [customInputs, setCustomInputs] = useState({});

  const fetchAdvisory = async (overrideInputs = {}) => {
    setIsLoading(true);
    setError(null);
    try {
      const mergedInputs = { ...customInputs, ...overrideInputs };
      const response = await financeLoanService.getLoanRecommendations(
        mergedInputs,
        { requested_amount_inr: mergedInputs.requested_amount_inr },
        {},
        true
      );
      setAdvisoryData(response);
    } catch (err) {
      setError(err?.message || "Failed to load Finance & Loan Agent advisory recommendations.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAdvisory();
  }, []);

  const handleUpdateInputs = (newInputs) => {
    const updated = { ...customInputs, ...newInputs };
    setCustomInputs(updated);
    fetchAdvisory(updated);
  };

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
              Module 4: Finance & Loan Agent Dashboard
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Personalized financial analysis, funding requirement estimation, and government-backed loan advisory.
            </p>
          </div>

          <Button
            variant="secondary"
            onClick={() => fetchAdvisory()}
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

            {/* Step 4 ACTIVE */}
            <div className="flex items-center gap-2 rounded-md bg-teal-50 px-3 py-2 font-bold text-teal-800 ring-1 ring-teal-400">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-600 text-xs text-white">
                4
              </span>
              <span className="truncate">Step 4: Finance Agent</span>
            </div>

            {/* Step 5 */}
            <button
              onClick={() => navigate("/export")}
              className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-left font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-navy-900 border border-slate-100"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-600">
                5
              </span>
              <span className="truncate">Step 5: Export Agent</span>
            </button>

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

        {/* Advisory Disclaimer Notice */}
        <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 text-xs text-blue-900 shadow-xs">
          <div className="flex items-start gap-2.5">
            <FiInfo size={16} className="text-blue-700 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold block">Advisory Disclaimer</span>
              <p className="mt-0.5 text-blue-800">
                {advisoryData?.disclaimer ||
                  "Final loan approval, interest rate, sanctioned amount, and eligibility are determined solely by the respective bank, financial institution, or government authority."}
              </p>
            </div>
          </div>
        </div>

        {/* Business Profile Strip */}
        {advisoryData && (
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-900 text-white">
                <FiBriefcase size={18} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-navy-900">{advisoryData.business_name}</h2>
                <span className="text-xs text-slate-500 capitalize">
                  {advisoryData.msme_classification} Enterprise Profile Connected
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="rounded bg-slate-100 px-2.5 py-1">
                Repayment Rating: <b>{advisoryData.financial_summary?.repayment_capacity_rating}</b>
              </span>
            </div>
          </div>
        )}

        {/* Loading Spinner */}
        {isLoading && (
          <div className="py-16">
            <PageLoader label="Analyzing financial parameters, calculating DSCR & retrieving loan options…" />
          </div>
        )}

        {/* Error Banner */}
        {error && !isLoading && (
          <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700">
            <div className="flex items-start gap-2">
              <FiAlertTriangle size={16} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold">Finance & Loan Agent Notice</p>
                <p className="mt-1">{error}</p>
                <button onClick={() => fetchAdvisory()} className="mt-2 font-semibold text-rose-800 underline">
                  Retry analysis
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Main Content Dashboard */}
        {!isLoading && advisoryData && (
          <div className="space-y-6">
            {/* Missing Information Prompt */}
            <MissingInfoAlert
              missingItems={advisoryData.missing_information}
              onUpdateInputs={handleUpdateInputs}
              isSubmitting={isLoading}
            />

            {/* Financial Summary & Health Score */}
            <FinancialSummaryCard summary={advisoryData.financial_summary} />

            {/* Loan Requirement Card */}
            <LoanRequirementCard requirement={advisoryData.loan_requirement} />

            {/* Recommended Loan Options List */}
            <RecommendedOptionsList options={advisoryData.recommended_options} />

            {/* Financial Risks & Improvement Areas */}
            <FinancialRisksCard
              risks={advisoryData.financial_risks}
              improvements={advisoryData.improvement_areas}
            />

            {/* Explainable Financial Advisory Synthesis Box */}
            {advisoryData.explanation && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                <h3 className="text-sm font-bold text-navy-900 border-b border-slate-100 pb-2 mb-3">
                  Explainable Financial Advisory Summary
                </h3>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {advisoryData.explanation}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
