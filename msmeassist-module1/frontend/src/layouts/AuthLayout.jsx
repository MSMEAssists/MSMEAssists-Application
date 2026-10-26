import { Link } from "react-router-dom";
import Brand from "../components/ui/Brand";
import LanguageSelector from "../components/ui/LanguageSelector";
import { FiCheckCircle } from "react-icons/fi";

export default function AuthLayout({
  mode = "login",
  heroTitle,
  heroLede,
  heroFooter = "Stronger MSMEs, a brighter India.",
  imageSrc,
  children,
}) {
  const isRegister = mode === "register";

  return (
    <div className="min-h-screen bg-warm-offwhite flex flex-col">
      {/* ── Top Header Navigation ──────────────────────────────────── */}
      <header className="border-b border-border bg-white px-5 py-3 sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="flex items-center">
            <Brand size={30} />
          </Link>

          <nav className="hidden sm:flex items-center gap-6 text-xs font-semibold text-slate-dark">
            <Link to="/" className="hover:text-burnt-orange transition">
              Home
            </Link>
            <Link to="/schemes" className="hover:text-burnt-orange transition">
              Schemes
            </Link>
            <Link to="/#how-it-works" className="hover:text-burnt-orange transition">
              About
            </Link>
            <Link to="/#help" className="hover:text-burnt-orange transition">
              Help
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <LanguageSelector />
          </div>
        </div>
      </header>

      {/* ── Main Split Content Area ─────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-10">
        <div className="w-full max-w-5xl overflow-hidden rounded-2xl border border-border bg-white shadow-elevated grid grid-cols-1 md:grid-cols-12 min-h-[580px]">
          {/* If Mode is Login: Left is Charcoal Panel, Right is Form */}
          {!isRegister && (
            <>
              {/* Charcoal Left Editorial Panel */}
              <div className="md:col-span-5 bg-charcoal text-white p-8 sm:p-10 flex flex-col justify-between relative overflow-hidden">
                <div className="space-y-4 relative z-10">
                  <Brand onDark size={30} />
                  <div className="pt-4">
                    <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                      {heroTitle || "Welcome Back"}
                    </h2>
                    <p className="mt-2 text-xs sm:text-sm text-slate-muted leading-relaxed">
                      {heroLede || "Sign in to access your personalized dashboard and scheme recommendations."}
                    </p>
                  </div>
                </div>

                {/* Naturally Blended Artisan Photo */}
                <div className="my-5 relative z-10">
                  <div className="relative overflow-hidden rounded-xl">
                    <img
                      src={imageSrc || "/images/artisan.jpg"}
                      alt="Indian MSME Artisan"
                      className="blend-editorial-panel w-full h-48 sm:h-54 object-cover object-center"
                    />
                    {/* Soft directional edge fades into Charcoal #202831 */}
                    <div
                      className="absolute inset-x-0 top-0 h-10 pointer-events-none"
                      style={{ background: "linear-gradient(to bottom, #202831 0%, transparent 100%)" }}
                      aria-hidden="true"
                    />
                    <div
                      className="absolute inset-x-0 bottom-0 h-10 pointer-events-none"
                      style={{ background: "linear-gradient(to top, #202831 0%, transparent 100%)" }}
                      aria-hidden="true"
                    />
                  </div>
                </div>

                <div className="relative z-10 pt-2 border-t border-charcoal-800 text-[11px] text-slate-muted/80 flex items-center justify-between">
                  <span>{heroFooter}</span>
                  <span className="text-burnt-orange font-bold">MSMEAssist</span>
                </div>
              </div>

              {/* Form Right Panel */}
              <div className="md:col-span-7 p-8 sm:p-12 flex flex-col justify-center bg-white">
                <div className="w-full max-w-md mx-auto">{children}</div>
              </div>
            </>
          )}

          {/* If Mode is Register: Left is Form, Right is Benefits + Photo */}
          {isRegister && (
            <>
              {/* Form Left Panel */}
              <div className="md:col-span-7 p-8 sm:p-12 flex flex-col justify-center bg-white order-2 md:order-1">
                <div className="w-full max-w-md mx-auto">{children}</div>
              </div>

              {/* Benefits + Photo Right Panel */}
              <div className="md:col-span-5 bg-warm-offwhite border-b md:border-b-0 md:border-l border-border p-8 sm:p-10 flex flex-col justify-between order-1 md:order-2">
                <div className="space-y-4">
                  {/* Naturally Blended Woman Entrepreneur Photo */}
                  <div className="relative overflow-hidden rounded-xl">
                    <img
                      src={imageSrc || "/images/woman_entrepreneur.jpg"}
                      alt="Indian MSME Entrepreneur"
                      className="blend-editorial-panel w-full h-44 sm:h-48 object-cover object-top"
                    />
                    {/* Soft directional edge fades into Warm Off-White #F7F5F1 */}
                    <div
                      className="absolute inset-x-0 top-0 h-8 pointer-events-none"
                      style={{ background: "linear-gradient(to bottom, #F7F5F1 0%, transparent 100%)" }}
                      aria-hidden="true"
                    />
                    <div
                      className="absolute inset-x-0 bottom-0 h-8 pointer-events-none"
                      style={{ background: "linear-gradient(to top, #F7F5F1 0%, transparent 100%)" }}
                      aria-hidden="true"
                    />
                  </div>

                  <div className="pt-2">
                    <h3 className="text-lg font-bold text-charcoal">
                      Your Business. <br />
                      <span className="text-burnt-orange">Our Support.</span>
                    </h3>
                    <p className="mt-1 text-xs text-slate-text">
                      We connect your enterprise with official central and state initiatives.
                    </p>
                  </div>

                  <div className="space-y-2.5 pt-3">
                    <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-dark">
                      <FiCheckCircle size={15} className="text-burnt-orange shrink-0" />
                      <span>Access official government schemes</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-dark">
                      <FiCheckCircle size={15} className="text-burnt-orange shrink-0" />
                      <span>Get personalized recommendations</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-dark">
                      <FiCheckCircle size={15} className="text-burnt-orange shrink-0" />
                      <span>Track your applications &amp; deadlines</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-dark">
                      <FiCheckCircle size={15} className="text-burnt-orange shrink-0" />
                      <span>Build a stronger future for your business</span>
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-border/80 text-[11px] text-slate-text">
                  <span>Trusted by Indian MSMEs across all 28 states &amp; UTs</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
