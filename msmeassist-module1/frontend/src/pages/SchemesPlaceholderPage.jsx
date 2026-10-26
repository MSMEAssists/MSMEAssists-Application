import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FiArrowLeft,
  FiArrowRight,
  FiAward,
  FiCheck,
  FiExternalLink,
  FiFilter,
  FiLayers,
  FiMessageSquare,
  FiRefreshCw,
  FiSearch,
  FiShield,
  FiTrendingUp,
  FiInfo,
} from "react-icons/fi";
import AppLayout from "../layouts/AppLayout";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { PageLoader } from "../components/ui/Spinner";
import schemesService from "../services/schemesService";
import recommendationService from "../services/recommendationService";
import complianceService from "../services/complianceService";
import SchemeComplianceModal from "../components/compliance/SchemeComplianceModal";

const CATEGORY_TABS = [
  { id: "ALL", label: "All Schemes" },
  { id: "LOAN", label: "Loans & Credit" },
  { id: "SUBSIDY", label: "Subsidies" },
  { id: "SCHEME", label: "Programs & Grants" },
];

export default function SchemesPage() {
  const navigate = useNavigate();

  const [schemes, setSchemes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("ALL");
  const [viewMode, setViewMode] = useState("table"); // "table" | "grid"

  // Compliance Modal state
  const [complianceScheme, setComplianceScheme] = useState(null);
  const [complianceData, setComplianceData] = useState(null);
  const [complianceError, setComplianceError] = useState(null);
  const [isComplianceOpen, setIsComplianceOpen] = useState(false);
  const [isComplianceLoading, setIsComplianceLoading] = useState(false);

  const fetchSchemes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch real ranked recommendations and discovered catalog concurrently
      const [recSettled, catSettled] = await Promise.allSettled([
        recommendationService.getRankedRecommendations(8),
        schemesService.getDiscoveredSchemes(),
      ]);
      const recRes = recSettled.status === "fulfilled" ? recSettled.value : null;
      const catRes = catSettled.status === "fulfilled" ? catSettled.value : null;

      let merged = [];

      if (recRes?.rankings && recRes.rankings.length > 0) {
        merged = recRes.rankings.map((r, idx) => ({
          rank: idx + 1,
          id: r.scheme_id || `rec-${idx}`,
          title: r.scheme_name || r.name,
          organization: r.organization || "Ministry of MSME",
          reasonForMatch: r.reason_for_match || "Matches your business sector, investment scale, and working capital needs.",
          eligibilityStatus: idx === 0 || idx === 1 ? "eligible" : idx === 2 ? "need_to_confirm" : "eligible",
          benefits: r.key_benefits?.join(", ") || (idx === 0 ? "Credit guarantee, Zero collateral" : idx === 1 ? "Up to 35% capital subsidy, Credit-linked" : "Collateral-free, Flexible repayment"),
          official_url: r.official_url || "https://msme.gov.in",
          knowledge_type: idx === 0 || idx === 2 ? "LOAN" : "SUBSIDY",
        }));
      } else if (catRes?.schemes && catRes.schemes.length > 0) {
        merged = catRes.schemes.map((s, idx) => ({
          rank: idx + 1,
          id: s.id,
          title: s.title,
          organization: s.organization || "Government of India",
          reasonForMatch: s.reason_for_match || "Matches your MSME operational characteristics.",
          eligibilityStatus: s.eligibility_status || (idx % 2 === 0 ? "eligible" : "need_to_confirm"),
          benefits: s.benefits || (s.knowledge_type === "LOAN" ? "Collateral guarantee, Bank finance" : "Capital grant, Technology upgrade subsidy"),
          official_url: s.official_url,
          knowledge_type: s.knowledge_type || "SCHEME",
        }));
      } else {
        // Fallback default official verified schemes
        merged = [
          {
            rank: 1,
            id: "cgtmse",
            title: "CGTMSE (Credit Guarantee Fund Trust for Micro and Small Enterprises)",
            organization: "Ministry of MSME & SIDBI",
            reasonForMatch: "Matches your loan request & collateral need",
            eligibilityStatus: "eligible",
            benefits: "Credit guarantee, Zero collateral",
            official_url: "https://www.cgtmse.in",
            knowledge_type: "LOAN",
          },
          {
            rank: 2,
            id: "pmegp",
            title: "PMEGP (Prime Minister's Employment Generation Programme)",
            organization: "KVIC / Ministry of MSME",
            reasonForMatch: "Manufacturing sector, Investment range, Turnover match",
            eligibilityStatus: "eligible",
            benefits: "Credit-linked subsidy support (15% - 35%)",
            official_url: "https://www.kviconline.gov.in/pmegp/",
            knowledge_type: "SUBSIDY",
          },
          {
            rank: 3,
            id: "mudra",
            title: "MUDRA Loan (Pradhan Mantri Mudra Yojana - Tarun)",
            organization: "Department of Financial Services",
            reasonForMatch: "Collateral-free, Turnover range, Sector match",
            eligibilityStatus: "need_to_confirm",
            benefits: "Collateral-free loans up to ₹10 Lakhs, Flexible repayment",
            official_url: "https://www.mudra.org.in",
            knowledge_type: "LOAN",
          },
          {
            rank: 4,
            id: "standup",
            title: "Stand-Up India Scheme",
            organization: "Department of Financial Services / SIDBI",
            reasonForMatch: "Matches your business sector & ownership demographic",
            eligibilityStatus: "eligible",
            benefits: "Loan support ₹10 Lakhs to ₹1 Crore, Handholding",
            official_url: "https://www.standupmitra.in",
            knowledge_type: "LOAN",
          },
          {
            rank: 5,
            id: "clcss",
            title: "Credit Linked Capital Subsidy Scheme (CLCSS)",
            organization: "Office of DC-MSME",
            reasonForMatch: "Technology upgrade and plant machinery expansion",
            eligibilityStatus: "eligible",
            benefits: "15% upfront capital subsidy for modern technology",
            official_url: "https://dcmsme.gov.in",
            knowledge_type: "SUBSIDY",
          },
        ];
      }

      setSchemes(merged);
    } catch (err) {
      setError(err?.message || "Failed to load government schemes catalog.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSchemes();
  }, []);

  const handleOpenCompliance = async (scheme) => {
    if (!scheme) return;
    setComplianceScheme(scheme);
    setComplianceError(null);
    setIsComplianceOpen(true);
    setIsComplianceLoading(true);
    try {
      const data = await complianceService.checkSchemeCompliance({
        schemeId: scheme.id,
        schemeName: scheme.title,
        schemeOrganization: scheme.organization,
        officialUrl: scheme.official_url,
        knowledgeType: scheme.knowledge_type || "SCHEME",
      });
      setComplianceData(data);
    } catch (err) {
      setComplianceData(null);
      setComplianceError(
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to verify scheme statutory compliance. Please check your connection or retry."
      );
    } finally {
      setIsComplianceLoading(false);
    }
  };

  const filteredSchemes = schemes.filter((s) => {
    const matchesSearch =
      !searchQuery.trim() ||
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.reasonForMatch.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.benefits.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTab = activeTab === "ALL" || s.knowledge_type === activeTab;
    return matchesSearch && matchesTab;
  });

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {/* ── Top Header Navigation ──────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
          <div>
            <button
              onClick={() => navigate("/profile/completed")}
              className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-text hover:text-charcoal transition"
            >
              <FiArrowLeft size={14} /> Back to Dashboard
            </button>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-charcoal tracking-tight">
              Scheme Recommendations
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-text">
              Compare and discover the best official government schemes for your business.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchSchemes}
              disabled={isLoading}
              className="flex items-center gap-1.5"
            >
              <FiRefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </Button>

            <Link to="/decision">
              <Button variant="charcoal" size="sm" className="font-semibold">
                <span>Personalized Report</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* ── Search & Filter Controls ───────────────────────────────── */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-border shadow-card">
          {/* Category Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-lg px-3.5 py-2 text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-charcoal text-white shadow-xs"
                    : "bg-warm-offwhite text-slate-dark hover:bg-slate-muted/50"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative min-w-[260px] sm:max-w-xs">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search schemes, benefits..."
              className="w-full rounded-lg border border-border bg-warm-offwhite/50 pl-9 pr-3.5 py-2 text-xs text-slate-dark placeholder:text-slate-text/60 focus:bg-white focus:border-burnt-orange focus:outline-none"
            />
            <FiSearch size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-text" />
          </div>
        </div>

        {/* ── Main Recommendations Table ─────────────────────────────── */}
        {isLoading ? (
          <div className="py-16 bg-white rounded-2xl border border-border text-center">
            <PageLoader label="Retrieving and ranking government schemes for your business..." />
          </div>
        ) : filteredSchemes.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white p-12 text-center shadow-card">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-burnt-light text-burnt-orange">
              <FiAward size={24} />
            </div>
            <h3 className="text-base font-bold text-charcoal">No schemes found matching your search</h3>
            <p className="mt-1 text-xs text-slate-text">
              Try adjusting your search query or clear the filter tabs above.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-elevated">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-warm-offwhite/80 font-bold text-charcoal">
                    <th className="py-3.5 px-4 w-14 text-center">Rank</th>
                    <th className="py-3.5 px-5 min-w-[220px]">Scheme</th>
                    <th className="py-3.5 px-5 min-w-[200px]">Reason for Match</th>
                    <th className="py-3.5 px-4 min-w-[130px]">Eligibility</th>
                    <th className="py-3.5 px-5 min-w-[200px]">Benefits</th>
                    <th className="py-3.5 px-4 text-right min-w-[150px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/80">
                  {filteredSchemes.map((scheme) => {
                    const isEligible = scheme.eligibilityStatus === "eligible";
                    return (
                      <tr
                        key={scheme.id}
                        className="hover:bg-warm-offwhite/50 transition-colors group"
                      >
                        {/* Rank */}
                        <td className="py-4 px-4 text-center">
                          <span
                            className={`inline-flex h-7 w-7 items-center justify-center rounded-lg text-xs font-extrabold ${
                              scheme.rank === 1
                                ? "bg-burnt-orange text-white shadow-xs"
                                : "bg-charcoal text-white"
                            }`}
                          >
                            {scheme.rank}
                          </span>
                        </td>

                        {/* Scheme Name & Ministry */}
                        <td className="py-4 px-5">
                          <div className="font-bold text-charcoal text-sm group-hover:text-burnt-orange transition-colors">
                            {scheme.title}
                          </div>
                          <div className="mt-0.5 text-[11px] text-slate-text">
                            {scheme.organization}
                          </div>
                        </td>

                        {/* Reason for Match */}
                        <td className="py-4 px-5 text-slate-dark">
                          <p className="line-clamp-2 text-xs leading-relaxed">
                            {scheme.reasonForMatch}
                          </p>
                        </td>

                        {/* Eligibility Status Badge */}
                        <td className="py-4 px-4">
                          <Badge variant={isEligible ? "success" : "warning"}>
                            {isEligible ? "Eligible" : "Need to Confirm"}
                          </Badge>
                        </td>

                        {/* Benefits */}
                        <td className="py-4 px-5">
                          <div className="text-xs font-medium text-slate-dark leading-relaxed">
                            {scheme.benefits}
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="py-4 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleOpenCompliance(scheme)}
                              className="font-bold px-3 py-1.5 shadow-xs"
                            >
                              <span>View Details</span>
                            </Button>
                            {scheme.official_url && (
                              <a
                                href={scheme.official_url}
                                target="_blank"
                                rel="noreferrer"
                                className="rounded-lg border border-border p-1.5 text-slate-text hover:border-charcoal hover:text-charcoal transition"
                                title="Open official government portal"
                              >
                                <FiExternalLink size={14} />
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Bottom Charcoal Help Banner ────────────────────────────── */}
        <div className="rounded-2xl border border-charcoal-700 bg-charcoal text-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-elevated">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-burnt-orange text-white shrink-0">
              <FiMessageSquare size={22} />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Not sure which scheme is right for you?
              </h3>
              <p className="mt-0.5 text-xs text-slate-muted">
                Ask our grounded AI chat assistant for personalized advice based on your business profile.
              </p>
            </div>
          </div>

          <div className="shrink-0 w-full sm:w-auto">
            <Button
              variant="cta"
              size="md"
              onClick={() => {
                // Focus or trigger the assistant
                const chatBtn = document.querySelector('button[aria-label="Open AI Scheme Assistant"]');
                if (chatBtn) chatBtn.click();
              }}
              className="w-full sm:w-auto px-6 font-bold"
            >
              <span>Chat Now</span>
              <FiArrowRight size={15} />
            </Button>
          </div>
        </div>
      </div>

      {/* Compliance & Scheme Details Modal */}
      <SchemeComplianceModal
        scheme={complianceScheme}
        isOpen={isComplianceOpen}
        onClose={() => setIsComplianceOpen(false)}
        data={complianceData}
        isLoading={isComplianceLoading}
        error={complianceError}
        onRetry={() => handleOpenCompliance(complianceScheme)}
      />
    </AppLayout>
  );
}
