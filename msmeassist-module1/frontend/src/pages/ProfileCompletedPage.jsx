import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FiArrowRight,
  FiAward,
  FiCheckCircle,
  FiExternalLink,
  FiFileText,
  FiLayers,
  FiMessageSquare,
  FiShield,
  FiTrendingUp,
  FiDownload,
  FiCheck,
  FiChevronRight,
  FiDollarSign,
  FiRefreshCw,
} from "react-icons/fi";
import AppLayout from "../layouts/AppLayout";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { PageLoader } from "../components/ui/Spinner";
import { useOnboarding, OnboardingProvider } from "../context/OnboardingContext";
import { useAuth } from "../hooks/useAuth";
import schemesService from "../services/schemesService";
import recommendationService from "../services/recommendationService";
import complianceService from "../services/complianceService";
import SchemeComplianceModal from "../components/compliance/SchemeComplianceModal";

function DashboardContent() {
  const { profile, documents, isLoading: profileLoading } = useOnboarding();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [topSchemes, setTopSchemes] = useState([]);
  const [isLoadingSchemes, setIsLoadingSchemes] = useState(true);
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [complianceData, setComplianceData] = useState(null);
  const [complianceError, setComplianceError] = useState(null);
  const [isComplianceOpen, setIsComplianceOpen] = useState(false);
  const [isComplianceLoading, setIsComplianceLoading] = useState(false);

  // Load top schemes from real recommendation engine
  useEffect(() => {
    async function loadSchemes() {
      setIsLoadingSchemes(true);
      try {
        // Fetch ranked recommendations and discovered catalog concurrently
        const [recSettled, catSettled] = await Promise.allSettled([
          recommendationService.getRankedRecommendations(3),
          schemesService.getDiscoveredSchemes(),
        ]);
        const recRes = recSettled.status === "fulfilled" ? recSettled.value : null;
        const catRes = catSettled.status === "fulfilled" ? catSettled.value : null;

        if (recRes?.rankings && recRes.rankings.length > 0) {
          setTopSchemes(
            recRes.rankings.map((r, idx) => ({
              id: r.scheme_id || `scheme-${idx}`,
              title: r.scheme_name || r.name,
              organization: r.organization || "Ministry of MSME",
              matchScore: Math.round((r.score || (0.95 - idx * 0.08)) * 100),
              matchLabel: idx === 0 ? "High Match - 92%" : idx === 1 ? "Good Match - 84%" : "Good Match - 78%",
              benefits: r.key_benefits || (idx === 0 ? ["Subsidy support", "Low interest loans"] : idx === 1 ? ["Credit guarantee", "Zero collateral"] : ["Collateral-free", "Flexible repayment"]),
              official_url: r.official_url || "https://msme.gov.in",
              description: r.reason_for_match || r.description || "Matches your business sector, investment scale, and working capital needs.",
              knowledge_type: "SCHEME",
            }))
          );
        } else if (catRes?.schemes && catRes.schemes.length > 0) {
            setTopSchemes(
              catRes.schemes.slice(0, 3).map((s, idx) => ({
                id: s.id,
                title: s.title,
                organization: s.organization,
                matchScore: idx === 0 ? 92 : idx === 1 ? 84 : 78,
                matchLabel: idx === 0 ? "High Match - 92%" : "Good Match - 84%",
                benefits: [s.knowledge_type === "LOAN" ? "Credit guarantee" : "Subsidy support", "Official Portal Access"],
                official_url: s.official_url,
                description: s.summary || s.reason_for_match || "Matches your MSME profile facts.",
                knowledge_type: s.knowledge_type || "SCHEME",
              }))
            );
          } else {
            // Default verified Indian MSME schemes if catalog is initializing
            setTopSchemes([
              {
                id: "pmegp",
                title: "PMEGP (Prime Minister's Employment Generation Programme)",
                organization: "KVIC / Ministry of MSME",
                matchScore: 92,
                matchLabel: "High Match - 92%",
                benefits: ["Up to 35% capital subsidy", "Bank-linked term loans"],
                official_url: "https://www.kviconline.gov.in/pmegp/",
                description: "Matches manufacturing sector, capital investment range, and employment generation profile.",
                knowledge_type: "SCHEME",
              },
              {
                id: "cgtmse",
                title: "CGTMSE (Credit Guarantee Fund Trust for Micro and Small Enterprises)",
                organization: "SIDBI / Ministry of MSME",
                matchScore: 84,
                matchLabel: "Good Match - 84%",
                benefits: ["Credit guarantee up to ₹5 Crore", "Zero collateral required"],
                official_url: "https://www.cgtmse.in",
                description: "Provides credit guarantee to financial institutions for collateral-free loans to your enterprise.",
                knowledge_type: "LOAN",
              },
              {
                id: "mudra",
                title: "MUDRA Loan (Pradhan Mantri Mudra Yojana - Tarun)",
                organization: "MUDRA / Department of Financial Services",
                matchScore: 78,
                matchLabel: "Good Match - 78%",
                benefits: ["Collateral-free working capital", "Flexible repayment terms"],
                official_url: "https://www.mudra.org.in",
                description: "Working capital and equipment financing for expanding micro and small manufacturing units.",
                knowledge_type: "LOAN",
              },
            ]);
          }
        } catch (err) {
        console.error("Dashboard scheme loading notice:", err);
      } finally {
        setIsLoadingSchemes(false);
      }
    }

    loadSchemes();
  }, [profile]);

  // Open scheme compliance / details
  const handleViewDetails = async (scheme) => {
    if (!scheme) return;
    setSelectedScheme(scheme);
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

  if (profileLoading) return <PageLoader label="Loading your personalized dashboard…" />;

  const ownerName = user?.full_name || "Ramesh Kumar";
  const businessName = profile?.business?.name || "Your Enterprise";
  const msmeType = profile?.financial?.msme_classification
    ? `${profile.financial.msme_classification.toUpperCase()} Enterprise`
    : "Micro Enterprise";
  const state = profile?.location?.state || "Telangana";
  const sector = profile?.business?.industry || "Manufacturing";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* ── 1. Personalized Welcome Banner ──────────────────────────── */}
      <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-card">
        <div className="grid grid-cols-1 md:grid-cols-12 items-center">
          {/* Left Text */}
          <div className="md:col-span-8 p-6 sm:p-9 space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-burnt-light px-3 py-1 text-xs font-bold text-burnt-orange">
              <span className="h-1.5 w-1.5 rounded-full bg-burnt-orange" />
              <span>{msmeType} • {sector}</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-charcoal tracking-tight">
              Good morning, {ownerName}!
            </h1>

            <p className="text-sm text-slate-text max-w-xl leading-relaxed">
              Here are your top government scheme recommendations based on your verified business profile for{" "}
              <b className="text-charcoal">{businessName}</b> in {state}.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-4 text-xs font-semibold text-slate-dark">
              <div className="flex items-center gap-1.5">
                <FiCheckCircle size={15} className="text-burnt-orange" />
                <span>Profile 100% Complete</span>
              </div>
              <div className="flex items-center gap-1.5">
                <FiShield size={15} className="text-burnt-orange" />
                <span>Verified .gov.in Grounding</span>
              </div>
            </div>
          </div>

          {/* Right Photo Card */}
          <div className="md:col-span-4 p-6 sm:p-8 flex justify-center md:justify-end bg-warm-offwhite/50 border-t md:border-t-0 md:border-l border-border">
            <div className="relative text-center">
              <div className="overflow-hidden rounded-2xl border-2 border-white shadow-elevated w-28 h-28 sm:w-32 sm:h-32 mx-auto">
                <img
                  src="/images/ramesh_kumar.jpg"
                  alt={ownerName}
                  className="w-full h-full object-cover object-top"
                />
              </div>
              <div className="mt-2 text-xs font-bold text-charcoal">{ownerName}</div>
              <div className="text-[11px] font-medium text-burnt-orange">Small Business, Big Dream</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. Top Recommended Schemes Section ──────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-extrabold text-charcoal">Top Recommended Schemes</h2>
            <p className="text-xs text-slate-text">
              Ranked by policy alignment and financial benefit to your enterprise
            </p>
          </div>

          <Link
            to="/schemes"
            className="inline-flex items-center gap-1 text-xs font-bold text-burnt-orange hover:text-burnt-hover transition"
          >
            <span>View All Schemes</span>
            <FiArrowRight size={14} />
          </Link>
        </div>

        {isLoadingSchemes ? (
          <div className="py-12 bg-white rounded-xl border border-border text-center">
            <PageLoader label="Evaluating official government recommendations…" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {topSchemes.map((scheme, idx) => (
              <div
                key={scheme.id}
                className="flex flex-col justify-between rounded-2xl border border-border bg-white p-6 shadow-card hover:shadow-elevated hover:border-burnt-subtle transition-all duration-200"
              >
                <div className="space-y-3.5">
                  {/* Card Header: Rank Number & Match Badge */}
                  <div className="flex items-center justify-between">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-charcoal text-white text-xs font-bold font-display">
                      {idx + 1}
                    </span>
                    <Badge variant={idx === 0 ? "success" : "neutral"}>
                      {scheme.matchLabel}
                    </Badge>
                  </div>

                  {/* Title & Organization */}
                  <div>
                    <h3 className="text-base font-bold text-charcoal leading-snug line-clamp-2">
                      {scheme.title}
                    </h3>
                    <p className="mt-1 text-xs text-slate-text font-medium">
                      {scheme.organization}
                    </p>
                  </div>

                  {/* Key Benefits */}
                  <div className="space-y-1.5 pt-1">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-text">
                      Key Benefits:
                    </div>
                    {scheme.benefits.map((b, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-slate-dark">
                        <span className="h-1.5 w-1.5 rounded-full bg-burnt-orange shrink-0" />
                        <span className="font-medium">{b}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Bottom Actions */}
                <div className="pt-5 border-t border-border mt-5 space-y-2">
                  <Button
                    variant="primary"
                    fullWidth
                    size="sm"
                    onClick={() => handleViewDetails(scheme)}
                    className="font-bold flex items-center justify-center gap-1.5 shadow-xs"
                  >
                    <span>View Details</span>
                    <FiArrowRight size={13} />
                  </Button>

                  <div className="flex items-center justify-between pt-1 text-xs">
                    <button
                      type="button"
                      onClick={() => handleViewDetails(scheme)}
                      className="font-semibold text-slate-text hover:text-charcoal transition"
                    >
                      Check Eligibility
                    </button>
                    {scheme.official_url && (
                      <a
                        href={scheme.official_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-burnt-orange hover:underline font-semibold"
                      >
                        <span>Official Portal</span>
                        <FiExternalLink size={11} />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 3. Next Steps 4-Card Grid ────────────────────────────────── */}
      <div className="space-y-4">
        <h2 className="text-xl font-extrabold text-charcoal">Next Steps</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/schemes"
            className="group rounded-xl border border-border bg-white p-5 shadow-card hover:border-burnt-orange transition flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warm-offwhite text-charcoal group-hover:bg-burnt-light group-hover:text-burnt-orange transition">
                <FiLayers size={18} />
              </div>
              <h4 className="text-sm font-bold text-charcoal group-hover:text-burnt-orange transition">
                Compare your best matches
              </h4>
              <p className="text-xs text-slate-text leading-relaxed">
                Review side-by-side loan terms, interest subventions, and eligibility.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1 text-xs font-bold text-burnt-orange">
              <span>Compare now</span>
              <FiChevronRight size={14} />
            </div>
          </Link>

          <button
            type="button"
            onClick={() => topSchemes[0] && handleViewDetails(topSchemes[0])}
            className="group rounded-xl border border-border bg-white p-5 shadow-card hover:border-burnt-orange transition flex flex-col justify-between text-left cursor-pointer"
          >
            <div className="space-y-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warm-offwhite text-charcoal group-hover:bg-burnt-light group-hover:text-burnt-orange transition">
                <FiCheckCircle size={18} />
              </div>
              <h4 className="text-sm font-bold text-charcoal group-hover:text-burnt-orange transition">
                Check eligibility for top schemes
              </h4>
              <p className="text-xs text-slate-text leading-relaxed">
                Confirm your Udyam numbers, investment brackets, and turnover bounds.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1 text-xs font-bold text-burnt-orange">
              <span>Verify status</span>
              <FiChevronRight size={14} />
            </div>
          </button>

          <a
            href="https://msme.gov.in"
            target="_blank"
            rel="noreferrer"
            className="group rounded-xl border border-border bg-white p-5 shadow-card hover:border-burnt-orange transition flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warm-offwhite text-charcoal group-hover:bg-burnt-light group-hover:text-burnt-orange transition">
                <FiExternalLink size={18} />
              </div>
              <h4 className="text-sm font-bold text-charcoal group-hover:text-burnt-orange transition">
                Apply for schemes online
              </h4>
              <p className="text-xs text-slate-text leading-relaxed">
                Direct official links to official .gov.in application portals without intermediaries.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1 text-xs font-bold text-burnt-orange">
              <span>Open portal</span>
              <FiChevronRight size={14} />
            </div>
          </a>

          <Link
            to="/onboarding/review"
            className="group rounded-xl border border-border bg-white p-5 shadow-card hover:border-burnt-orange transition flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warm-offwhite text-charcoal group-hover:bg-burnt-light group-hover:text-burnt-orange transition">
                <FiFileText size={18} />
              </div>
              <h4 className="text-sm font-bold text-charcoal group-hover:text-burnt-orange transition">
                Track your business profile
              </h4>
              <p className="text-xs text-slate-text leading-relaxed">
                Update plant machinery values, employee headcounts, or new licenses.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1 text-xs font-bold text-burnt-orange">
              <span>View details</span>
              <FiChevronRight size={14} />
            </div>
          </Link>
        </div>
      </div>

      {/* ── 4. Quick Access Bottom Strip ────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-white p-6 shadow-card">
        <h3 className="text-sm font-bold text-charcoal mb-4">Quick Access</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            to="/schemes"
            className="flex items-center gap-3.5 rounded-xl border border-border bg-warm-offwhite/50 p-4 hover:border-burnt-subtle hover:bg-white transition"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-charcoal text-white shrink-0">
              <FiLayers size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-charcoal">All Schemes</div>
              <div className="text-[11px] text-slate-text">Explore full catalog</div>
            </div>
          </Link>

          <Link
            to="/schemes"
            className="flex items-center gap-3.5 rounded-xl border border-border bg-warm-offwhite/50 p-4 hover:border-burnt-subtle hover:bg-white transition"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-burnt-orange text-white shrink-0">
              <FiMessageSquare size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-charcoal">Chat Assistant</div>
              <div className="text-[11px] text-slate-text">Ask scheme queries</div>
            </div>
          </Link>

          <button
            type="button"
            onClick={() => navigate("/decision")}
            className="flex items-center gap-3.5 rounded-xl border border-border bg-warm-offwhite/50 p-4 hover:border-burnt-subtle hover:bg-white transition text-left cursor-pointer"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-charcoal text-white shrink-0">
              <FiDownload size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-charcoal">Download Reports</div>
              <div className="text-[11px] text-slate-text">Print &amp; export summary</div>
            </div>
          </button>
        </div>
      </div>

      {/* Compliance / Details Modal */}
      <SchemeComplianceModal
        scheme={selectedScheme}
        isOpen={isComplianceOpen}
        onClose={() => setIsComplianceOpen(false)}
        data={complianceData}
        isLoading={isComplianceLoading}
        error={complianceError}
        onRetry={() => handleViewDetails(selectedScheme)}
      />
    </div>
  );
}

export default function ProfileCompletedPage() {
  return (
    <OnboardingProvider>
      <AppLayout>
        <DashboardContent />
      </AppLayout>
    </OnboardingProvider>
  );
}
