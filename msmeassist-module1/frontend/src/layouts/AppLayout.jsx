import { Link } from "react-router-dom";
import Brand from "../components/ui/Brand";
import LanguageSelector from "../components/ui/LanguageSelector";
import FloatingChatAssistant from "../components/chat/FloatingChatAssistant";
import { useAuth } from "../hooks/useAuth";

function initials(fullName = "") {
  return fullName
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-warm-offwhite flex flex-col text-slate-dark">
      {/* ── Top Header Navigation ──────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-border bg-white/95 backdrop-blur-md px-5 py-3.5 sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/">
              <Brand size={30} />
            </Link>

            <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-dark">
              <Link to="/" className="hover:text-burnt-orange transition">
                Home
              </Link>
              <Link to="/schemes" className="hover:text-burnt-orange transition">
                Schemes
              </Link>
              <Link to="/profile/completed" className="hover:text-burnt-orange transition">
                Dashboard
              </Link>
              <Link to="/#how-it-works" className="hover:text-burnt-orange transition">
                About
              </Link>
              <Link to="/#help" className="hover:text-burnt-orange transition">
                Help
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3.5">
            {user?.role === "admin" && (
              <Link
                to="/admin/schemes"
                className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-charcoal-700 bg-charcoal px-2.5 py-1 text-xs font-bold text-white shadow-xs transition hover:bg-charcoal-800"
                title="System Administrator Dashboard"
              >
                <span>Admin</span>
              </Link>
            )}

            <LanguageSelector />

            {/* User Profile Avatar & Sign Out */}
            <div className="flex items-center gap-2 pl-2 border-l border-border">
              <Link
                to="/profile/completed"
                title={user?.full_name || "Business Profile"}
                className="flex items-center gap-2 group"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-charcoal font-display text-xs font-bold text-white shadow-xs group-hover:bg-burnt-orange transition">
                  {user ? initials(user.full_name) : "MS"}
                </div>
                <span className="hidden lg:block text-xs font-bold text-charcoal group-hover:text-burnt-orange transition max-w-[120px] truncate">
                  {user?.full_name || "Profile"}
                </span>
              </Link>

              <button
                type="button"
                onClick={logout}
                title="Sign out"
                className="text-[11px] font-semibold text-slate-text hover:text-charcoal px-1.5 py-1 rounded transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Layout Body ───────────────────────────────────────── */}
      <div className="flex-1">
        {children}
      </div>

      {/* ── Global Floating Chat Assistant ─────────────────────────── */}
      <FloatingChatAssistant />
    </div>
  );
}
