import { Link, useNavigate } from "react-router-dom";
import {
  FiArrowRight,
  FiSearch,
  FiCheckCircle,
  FiCompass,
  FiAward,
  FiShield,
  FiFileText,
  FiUsers,
  FiTrendingUp,
} from "react-icons/fi";
import Brand from "../components/ui/Brand";
import Button from "../components/ui/Button";
import LanguageSelector from "../components/ui/LanguageSelector";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../context/LanguageContext";

export default function HomePage() {
  const { isAuthenticated, user, logout } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-warm-offwhite flex flex-col">
      {/* ── Top Navigation Bar ───────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-18 items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center">
              <Brand size={32} />
            </Link>

            {/* Desktop Navigation Links */}
            <nav className="hidden md:flex items-center gap-8 text-[14px] font-semibold text-slate-dark">
              <Link to="/" className="text-burnt-orange font-bold transition">
                {t("home")}
              </Link>
              <Link to="/schemes" className="hover:text-burnt-orange transition">
                {t("schemes")}
              </Link>
              <a href="#how-it-works" className="hover:text-burnt-orange transition">
                {t("about")}
              </a>
              <a href="#help" className="hover:text-burnt-orange transition">
                {t("help")}
              </a>
            </nav>

            {/* Right Controls: Language Selector + Auth Buttons */}
            <div className="flex items-center gap-3">
              <LanguageSelector />

              {isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <Link to="/profile/completed">
                    <Button variant="primary" size="sm">
                      {t("dashboard")}
                    </Button>
                  </Link>
                  <button
                    onClick={logout}
                    className="text-xs font-semibold text-slate-text hover:text-charcoal px-2 py-1.5"
                  >
                    {t("logout")}
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link to="/login">
                    <Button variant="secondary" size="sm">
                      {t("login")}
                    </Button>
                  </Link>
                  <Link to="/register">
                    <Button variant="primary" size="sm">
                      {t("register")}
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ── Hero Section (Charcoal #202831) ──────────────────────────── */}
      <section
        className="relative overflow-hidden bg-charcoal text-white pt-12 pb-16 lg:pt-16 lg:pb-20"
        style={{ backgroundColor: "#202831", color: "#FFFFFF" }}
      >
        {/* Subtle warm ambient lighting in the hero background behind the photograph */}
        <div
          className="absolute top-0 right-0 w-[680px] h-[680px] pointer-events-none"
          style={{
            background: "radial-gradient(circle at 75% 35%, rgba(232, 117, 69, 0.09) 0%, rgba(40, 51, 62, 0.45) 42%, transparent 72%)",
          }}
          aria-hidden="true"
        />

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            {/* Left Column: Headlines & Call to Action */}
            <div className="lg:col-span-7 space-y-6">
              <div
                className="inline-flex items-center gap-2 rounded-full px-3.5 py-1 text-[11px] font-bold tracking-wider uppercase"
                style={{ backgroundColor: "#28333E", borderColor: "#364350", borderWidth: "1px", color: "#D9E0E5" }}
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "#E87545" }} />
                <span>{t("heroEyebrow")}</span>
              </div>

              <h1
                className="text-4xl sm:text-5xl lg:text-[58px] font-extrabold leading-[1.08] tracking-tight"
                style={{ color: "#FFFFFF" }}
              >
                Right Schemes. <br />
                <span style={{ color: "#FFFFFF" }}>Real Growth.</span>
              </h1>

              <p
                className="max-w-xl text-base sm:text-lg leading-relaxed font-normal"
                style={{ color: "#D9E0E5" }}
              >
                {t("heroSubtitle")}
              </p>

              <div className="pt-2 flex flex-wrap items-center gap-4">
                <Link to={isAuthenticated ? "/onboarding/business" : "/register"}>
                  <Button
                    variant="cta"
                    size="lg"
                    className="px-7 py-3.5 font-bold shadow-elevated"
                    style={{ backgroundColor: "#E87545", color: "#FFFFFF" }}
                  >
                    <span>{t("getStarted")}</span>
                    <FiArrowRight size={17} />
                  </Button>
                </Link>

                <Link to="/schemes">
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-lg px-5 py-3.5 text-sm font-semibold transition"
                    style={{
                      backgroundColor: "rgba(40, 51, 62, 0.7)",
                      borderColor: "#49596B",
                      borderWidth: "1px",
                      color: "#FFFFFF",
                    }}
                  >
                    <FiSearch size={15} style={{ color: "#E87545" }} />
                    <span>Explore Official Catalog</span>
                  </button>
                </Link>
              </div>

              {/* Trust Strip */}
              <div className="pt-4 flex items-center gap-6 text-xs" style={{ color: "#D9E0E5" }}>
                <div className="flex items-center gap-1.5">
                  <FiCheckCircle size={14} style={{ color: "#E87545" }} />
                  <span>100% Official .gov.in Sources</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <FiShield size={14} style={{ color: "#E87545" }} />
                  <span>Verified Eligibility Rules</span>
                </div>
              </div>
            </div>

            {/* Right Column: Naturally Integrated Hero Photography (Indian MSME Owner) */}
            <div className="lg:col-span-5 relative flex justify-center lg:justify-end">
              {/* Soft warm aura reflecting the entrepreneur's workshop & store lighting */}
              <div
                className="absolute inset-0 bg-radial from-burnt-orange/10 via-charcoal-800/35 to-transparent blur-3xl pointer-events-none scale-105"
                aria-hidden="true"
              />

              <div className="relative w-full max-w-[480px] lg:max-w-none">
                {/* Seamlessly Blended Photograph Stage (No card borders or artificial boxes) */}
                <div className="relative overflow-hidden">
                  <img
                    src="/images/hero_owner.jpg"
                    alt="Indian MSME Business Owner"
                    className="blend-hero-charcoal w-full h-[380px] sm:h-[460px] lg:h-[500px] xl:h-[540px] object-cover object-[55%_25%] select-none pointer-events-none"
                    loading="eager"
                  />

                  {/* Left Edge Dissolve into Typography Column */}
                  <div
                    className="absolute inset-y-0 left-0 w-24 sm:w-36 lg:w-44 pointer-events-none"
                    style={{
                      background: "linear-gradient(to right, #202831 0%, rgba(32, 40, 49, 0.85) 30%, rgba(32, 40, 49, 0) 100%)",
                    }}
                    aria-hidden="true"
                  />

                  {/* Bottom Edge Dissolve into Hero Section Floor */}
                  <div
                    className="absolute inset-x-0 bottom-0 h-24 sm:h-32 pointer-events-none"
                    style={{
                      background: "linear-gradient(to bottom, rgba(32, 40, 49, 0) 0%, rgba(32, 40, 49, 0.85) 60%, #202831 100%)",
                    }}
                    aria-hidden="true"
                  />

                  {/* Top Edge Feathering */}
                  <div
                    className="absolute inset-x-0 top-0 h-16 pointer-events-none"
                    style={{
                      background: "linear-gradient(to top, rgba(32, 40, 49, 0) 0%, rgba(32, 40, 49, 0.6) 70%, #202831 100%)",
                    }}
                    aria-hidden="true"
                  />

                  {/* Right Edge Soft Feathering */}
                  <div
                    className="hidden lg:block absolute inset-y-0 right-0 w-16 pointer-events-none"
                    style={{
                      background: "linear-gradient(to left, #202831 0%, rgba(32, 40, 49, 0) 100%)",
                    }}
                    aria-hidden="true"
                  />
                </div>

                {/* Floating Proof Badge - Grounded cleanly over the composition */}
                <div
                  className="absolute -bottom-2 left-2 sm:left-4 lg:-left-4 rounded-xl border border-white/20 bg-white/95 backdrop-blur-md p-3.5 shadow-elevated flex items-center gap-3 z-20"
                  style={{ color: "#202831" }}
                >
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-lg shrink-0"
                    style={{ backgroundColor: "#FDF1EB", color: "#E87545" }}
                  >
                    <FiAward size={20} />
                  </div>
                  <div>
                    <div className="text-xs font-bold leading-tight" style={{ color: "#202831" }}>
                      Grounded Government Guidance
                    </div>
                    <div className="text-[11px] font-medium" style={{ color: "#58626C" }}>
                      Central &amp; State MSME Portals
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4 Benefit Pillars Strip ──────────────────────────────────── */}
      <section className="bg-warm-offwhite py-8 border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Pillar 1 */}
            <div className="flex items-start gap-3.5 rounded-xl border border-border bg-white p-4.5 shadow-card hover:border-burnt-subtle transition">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-burnt-light text-burnt-orange">
                <FiSearch size={18} />
              </div>
              <div className="text-xs font-semibold text-slate-dark leading-snug">
                {t("pillar1")}
              </div>
            </div>

            {/* Pillar 2 */}
            <div className="flex items-start gap-3.5 rounded-xl border border-border bg-white p-4.5 shadow-card hover:border-burnt-subtle transition">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-burnt-light text-burnt-orange">
                <FiCheckCircle size={18} />
              </div>
              <div className="text-xs font-semibold text-slate-dark leading-snug">
                {t("pillar2")}
              </div>
            </div>

            {/* Pillar 3 */}
            <div className="flex items-start gap-3.5 rounded-xl border border-border bg-white p-4.5 shadow-card hover:border-burnt-subtle transition">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-burnt-light text-burnt-orange">
                <FiCompass size={18} />
              </div>
              <div className="text-xs font-semibold text-slate-dark leading-snug">
                {t("pillar3")}
              </div>
            </div>

            {/* Pillar 4 */}
            <div className="flex items-start gap-3.5 rounded-xl border border-border bg-white p-4.5 shadow-card hover:border-burnt-subtle transition">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-burnt-light text-burnt-orange">
                <FiShield size={18} />
              </div>
              <div className="text-xs font-semibold text-slate-dark leading-snug">
                {t("pillar4")}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section: How MSMEAssist Helps You ────────────────────────── */}
      <section id="how-it-works" className="py-16 sm:py-20 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-charcoal">
              {t("howTitle")}
            </h2>
            <p className="mt-3 text-sm sm:text-base text-slate-text">
              {t("howSubtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="rounded-2xl border border-border bg-warm-offwhite p-7 text-left space-y-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-charcoal text-white font-bold text-lg font-display">
                01
              </div>
              <h3 className="text-lg font-bold text-charcoal">Single Business Profile</h3>
              <p className="text-xs sm:text-sm text-slate-text leading-relaxed">
                Provide your basic business details, industry sector, Udyam registration, and turnover once. No repetitive forms.
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-warm-offwhite p-7 text-left space-y-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-burnt-orange text-white font-bold text-lg font-display">
                02
              </div>
              <h3 className="text-lg font-bold text-charcoal">Smart Eligibility Check</h3>
              <p className="text-xs sm:text-sm text-slate-text leading-relaxed">
                Our engine cross-checks your profile against official criteria for subsidies, collateral guarantees, and loan terms.
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-warm-offwhite p-7 text-left space-y-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-charcoal text-white font-bold text-lg font-display">
                03
              </div>
              <h3 className="text-lg font-bold text-charcoal">Step-by-Step Action Plan</h3>
              <p className="text-xs sm:text-sm text-slate-text leading-relaxed">
                Download a personalized report with required documents, official application links, and clear next steps.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section: Government Schemes, Made Personal ────────────────── */}
      <section className="py-16 bg-warm-offwhite border-t border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            {/* Left Content */}
            <div className="lg:col-span-7 space-y-6">
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-charcoal leading-tight">
                {t("personalTitle")}
              </h2>
              <p className="text-sm sm:text-base text-slate-text leading-relaxed max-w-lg">
                {t("personalSubtitle")}
              </p>

              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-3 text-xs sm:text-sm font-semibold text-slate-dark">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-burnt-light text-burnt-orange">
                    ✓
                  </span>
                  <span>Credit guarantee schemes for collateral-free loans</span>
                </div>
                <div className="flex items-center gap-3 text-xs sm:text-sm font-semibold text-slate-dark">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-burnt-light text-burnt-orange">
                    ✓
                  </span>
                  <span>Capital investment &amp; interest subsidies</span>
                </div>
                <div className="flex items-center gap-3 text-xs sm:text-sm font-semibold text-slate-dark">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-burnt-light text-burnt-orange">
                    ✓
                  </span>
                  <span>Special programs for women and rural enterprises</span>
                </div>
              </div>

              <div className="pt-4">
                <Link to="/register">
                  <Button variant="primary" size="lg" className="px-7 font-bold">
                    <span>{t("getStarted")}</span>
                    <FiArrowRight size={16} />
                  </Button>
                </Link>
              </div>
            </div>

            {/* Right Photo: Naturally Integrated Woman Entrepreneur */}
            <div className="lg:col-span-5 relative flex justify-center lg:justify-end">
              {/* Subtle warm halo */}
              <div
                className="absolute inset-0 bg-radial from-burnt-orange/8 via-warm-muted/30 to-transparent blur-2xl pointer-events-none scale-110"
                aria-hidden="true"
              />

              <div className="relative w-full max-w-[420px]">
                <div className="relative overflow-hidden">
                  <img
                    src="/images/woman_entrepreneur.jpg"
                    alt="Indian Woman Entrepreneur"
                    className="blend-warm-offwhite w-full h-[380px] sm:h-[440px] object-cover object-top select-none pointer-events-none"
                    loading="lazy"
                  />

                  {/* Directional Softening Overlays merging seamlessly into #F7F5F1 */}
                  {/* Left Edge Fade */}
                  <div
                    className="absolute inset-y-0 left-0 w-20 pointer-events-none"
                    style={{
                      background: "linear-gradient(to right, #F7F5F1 0%, rgba(247, 245, 241, 0.7) 40%, rgba(247, 245, 241, 0) 100%)",
                    }}
                    aria-hidden="true"
                  />

                  {/* Bottom Edge Fade */}
                  <div
                    className="absolute inset-x-0 bottom-0 h-24 pointer-events-none"
                    style={{
                      background: "linear-gradient(to bottom, rgba(247, 245, 241, 0) 0%, rgba(247, 245, 241, 0.85) 65%, #F7F5F1 100%)",
                    }}
                    aria-hidden="true"
                  />

                  {/* Top Edge Fade */}
                  <div
                    className="absolute inset-x-0 top-0 h-14 pointer-events-none"
                    style={{
                      background: "linear-gradient(to top, rgba(247, 245, 241, 0) 0%, rgba(247, 245, 241, 0.6) 70%, #F7F5F1 100%)",
                    }}
                    aria-hidden="true"
                  />
                </div>

                {/* Floating Verified Highlight Chip */}
                <div className="absolute -bottom-2 right-2 sm:right-4 z-20 rounded-xl bg-white/95 backdrop-blur-md border border-border/80 shadow-card p-3 flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-burnt-light text-burnt-orange shrink-0">
                    <FiTrendingUp size={16} />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-charcoal">Up to 35% Capital Aid</div>
                    <div className="text-[10px] text-slate-text">PMEGP &amp; State Handloom Grants</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer (Charcoal #202831) ─────────────────────────────────── */}
      <footer
        id="help"
        className="bg-charcoal text-white mt-auto pt-14 pb-10 border-t border-charcoal-800"
        style={{ backgroundColor: "#202831", color: "#FFFFFF" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-10 border-b border-charcoal-800">
            <div className="space-y-3 md:col-span-2">
              <Brand onDark size={32} />
              <p className="text-xs text-slate-muted max-w-sm leading-relaxed mt-2">
                Empowering Indian micro, small, and medium enterprises with transparent, verified, and personalized access to government schemes.
              </p>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-muted mb-3">Quick Links</h4>
              <ul className="space-y-2 text-xs text-slate-muted">
                <li><Link to="/schemes" className="hover:text-white transition">Government Schemes</Link></li>
                <li><Link to="/login" className="hover:text-white transition">Sign In</Link></li>
                <li><Link to="/register" className="hover:text-white transition">Create Profile</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-muted mb-3">Official Portals</h4>
              <ul className="space-y-2 text-xs text-slate-muted">
                <li><a href="https://msme.gov.in" target="_blank" rel="noreferrer" className="hover:text-white transition">Ministry of MSME</a></li>
                <li><a href="https://udyamregistration.gov.in" target="_blank" rel="noreferrer" className="hover:text-white transition">Udyam Registration</a></li>
                <li><a href="https://www.cgtmse.in" target="_blank" rel="noreferrer" className="hover:text-white transition">CGTMSE Portal</a></li>
              </ul>
            </div>
          </div>

          <div className="pt-6 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-muted/70">
            <div>© 2026 MSMEAssist. All rights reserved. Grounded in Official Government Policies.</div>
            <div className="flex items-center gap-4">
              <span className="hover:text-white cursor-pointer">Privacy Policy</span>
              <span>•</span>
              <span className="hover:text-white cursor-pointer">Terms of Service</span>
              <span>•</span>
              <span className="hover:text-white cursor-pointer">Support</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
