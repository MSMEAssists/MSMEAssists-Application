import Brand from "../components/ui/Brand";
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
    <div className="min-h-screen bg-bg">
      <div className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-white px-5 py-3.5 sm:px-8">
        <Brand size={30} />
        <div className="flex items-center gap-4">
          <span className="hidden items-center gap-2 font-data text-[11.5px] text-ink-500 sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-success-600" />
            Secure Government Service Platform
          </span>
          <button
            type="button"
            onClick={logout}
            title="Sign out"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-navy-800 font-display text-xs font-semibold text-white"
          >
            {user ? initials(user.full_name) : "—"}
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}
