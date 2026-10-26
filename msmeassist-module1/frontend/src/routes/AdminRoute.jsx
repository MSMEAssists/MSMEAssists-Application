import { useState } from "react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { FiShield, FiAlertTriangle, FiArrowLeft, FiUserCheck, FiRefreshCw } from "react-icons/fi";
import { useAuth } from "../hooks/useAuth";
import { PageLoader } from "../components/ui/Spinner";
import adminService from "../services/adminService";

export default function AdminRoute() {
  const { user, isAuthenticated, isLoading, refreshUser } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isSwitching, setIsSwitching] = useState(false);

  if (isLoading) return <PageLoader label="Verifying administrator authorization…" />;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const handleGrantAdmin = async () => {
    setIsSwitching(true);
    try {
      await adminService.toggleAdminRole();
      await refreshUser();
    } catch (err) {
      console.error("Failed to switch role:", err);
    } finally {
      setIsSwitching(false);
    }
  };

  // If user is not an admin, show strict access restriction screen
  if (user?.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
        <div className="w-full max-w-lg rounded-2xl border border-red-200 bg-white p-8 text-center shadow-lg">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-600 shadow-inner">
            <FiShield size={32} />
          </div>

          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-red-700">
            <FiAlertTriangle size={13} /> Admin Restricted Access
          </span>

          <h1 className="mt-4 font-display text-2xl font-bold text-slate-900">
            Administrator Clearance Required
          </h1>

          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            This dashboard is strictly reserved for system administrators to view, audit, check links, and delete government schemes from the knowledge base.
          </p>

          <div className="my-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Current User:</span>
              <span className="font-semibold text-slate-800">{user?.full_name} ({user?.email})</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-slate-500">Current Account Role:</span>
              <span className="inline-flex items-center gap-1 rounded bg-slate-200 px-2 py-0.5 font-mono text-[11px] font-bold text-slate-700">
                {user?.role || "msme_owner"}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <button
              onClick={() => navigate("/schemes")}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              <FiArrowLeft size={16} /> Return to MSME Schemes
            </button>
            <button
              onClick={handleGrantAdmin}
              disabled={isSwitching}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-purple-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-purple-800 disabled:opacity-60"
            >
              {isSwitching ? (
                <>
                  <FiRefreshCw className="animate-spin" size={15} /> Upgrading Role…
                </>
              ) : (
                <>
                  <FiUserCheck size={16} /> Grant Admin Clearance (Demo)
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
