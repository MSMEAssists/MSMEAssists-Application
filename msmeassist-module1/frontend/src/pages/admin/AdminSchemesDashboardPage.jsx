import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  FiShield,
  FiSearch,
  FiRefreshCw,
  FiTrash2,
  FiExternalLink,
  FiCheckCircle,
  FiAlertTriangle,
  FiGlobe,
  FiMapPin,
  FiLayers,
  FiCheck,
  FiCopy,
  FiArrowLeft,
  FiActivity,
  FiFilter,
  FiX,
  FiAlertCircle,
} from "react-icons/fi";
import { useAuth } from "../../hooks/useAuth";
import { PageLoader } from "../../components/ui/Spinner";
import adminService from "../../services/adminService";

export default function AdminSchemesDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [schemes, setSchemes] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    central: 0,
    state: 0,
    activeLinks: 0,
    errorLinks: 0,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [locationTab, setLocationTab] = useState("ALL"); // "ALL" | "CENTRAL" | "STATE"
  const [statusTab, setStatusTab] = useState("ALL"); // "ALL" | "ACTIVE" | "ERROR"

  // Live actions state
  const [isCheckingAll, setIsCheckingAll] = useState(false);
  const [checkingIds, setCheckingIds] = useState(new Set());
  const [copiedUrl, setCopiedUrl] = useState(null);

  // Delete modal state
  const [schemeToDelete, setSchemeToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [notification, setNotification] = useState(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  const loadSchemes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminService.getSchemes();
      setSchemes(data.schemes || []);
      setStats({
        total: data.total_schemes || 0,
        central: data.central_count || 0,
        state: data.state_count || 0,
        activeLinks: data.active_links_count || 0,
        errorLinks: data.error_links_count || 0,
      });
    } catch (err) {
      console.error("Failed to load admin schemes:", err);
      setError(err?.message || "Failed to load government schemes. Ensure backend is running.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSchemes();
  }, []);

  // Filter schemes
  const filteredSchemes = useMemo(() => {
    return schemes.filter((s) => {
      // Location filter
      if (locationTab === "CENTRAL" && s.location_type !== "central") return false;
      if (locationTab === "STATE" && s.location_type !== "state") return false;

      // Status filter
      if (statusTab === "ACTIVE" && !s.link_status?.is_active) return false;
      if (statusTab === "ERROR" && s.link_status?.is_active) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = s.title?.toLowerCase().includes(q);
        const matchesOrg = s.organization?.toLowerCase().includes(q);
        const matchesSource = s.source_id?.toLowerCase().includes(q);
        const matchesState = s.state_name?.toLowerCase().includes(q);
        const matchesApply = s.apply_url?.toLowerCase().includes(q);
        const matchesOfficial = s.official_url?.toLowerCase().includes(q);
        if (!matchesTitle && !matchesOrg && !matchesSource && !matchesState && !matchesApply && !matchesOfficial) {
          return false;
        }
      }

      return true;
    });
  }, [schemes, locationTab, statusTab, searchQuery]);

  // Paginated schemes
  const paginatedSchemes = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredSchemes.slice(start, start + pageSize);
  }, [filteredSchemes, currentPage, pageSize]);

  const totalPages = Math.max(1, Math.ceil(filteredSchemes.length / pageSize));

  // Reset page when filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [locationTab, statusTab, searchQuery]);

  // Re-check single link live
  const handleCheckLink = async (docId) => {
    setCheckingIds((prev) => new Set(prev).add(docId));
    try {
      const res = await adminService.checkSchemeLink(docId);
      setSchemes((prev) =>
        prev.map((item) =>
          item.document_id === docId ? { ...item, link_status: res.link_status } : item
        )
      );
      showNotification("success", `Link verified: ${res.link_status?.message}`);
    } catch (err) {
      showNotification("error", `Link check failed: ${err.message}`);
    } finally {
      setCheckingIds((prev) => {
        const next = new Set(prev);
        next.delete(docId);
        return next;
      });
    }
  };

  // Re-check all links
  const handleCheckAllLinks = async () => {
    setIsCheckingAll(true);
    try {
      const res = await adminService.checkAllLinks();
      await loadSchemes();
      showNotification(
        "success",
        `Batch verification completed: ${res.active_links} active links, ${res.error_links} errors.`
      );
    } catch (err) {
      showNotification("error", `Batch link check failed: ${err.message}`);
    } finally {
      setIsCheckingAll(false);
    }
  };

  // Delete scheme
  const confirmDelete = async () => {
    if (!schemeToDelete) return;
    setIsDeleting(true);
    try {
      await adminService.deleteScheme(schemeToDelete.document_id);
      setSchemes((prev) => prev.filter((s) => s.document_id !== schemeToDelete.document_id));
      showNotification("success", `Scheme "${schemeToDelete.title}" permanently deleted from database.`);
      setSchemeToDelete(null);
    } catch (err) {
      showNotification("error", `Failed to delete scheme: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification(null);
    }, 4500);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(text);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-900 font-sans text-slate-100 antialiased">
      {/* Top Admin Header Bar */}
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 text-purple-400 ring-1 ring-purple-500/30">
              <FiShield size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display text-base font-bold text-white">
                  Government Schemes Admin Portal
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 px-2 py-0.5 text-[11px] font-semibold text-purple-300 ring-1 ring-purple-500/20">
                  <FiShield size={11} /> Admin Only
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Scheme Governance, Central vs. State Auditing, Real-time Link Verification & Deletion
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/schemes")}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-slate-700 hover:text-white"
            >
              <FiArrowLeft size={14} /> Back to MSME Portal
            </button>
            <div className="flex items-center gap-2 border-l border-slate-800 pl-3">
              <div className="h-7 w-7 rounded-full bg-purple-600 font-display text-xs font-bold leading-7 text-white text-center">
                A
              </div>
              <div className="hidden text-left sm:block">
                <p className="text-xs font-medium text-slate-200">{user?.full_name || "Admin"}</p>
                <p className="text-[10px] text-purple-400">Administrator</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Toast Notification */}
      {notification && (
        <div className="fixed right-6 top-20 z-50 animate-bounce duration-300">
          <div
            className={`flex items-center gap-2.5 rounded-xl px-4 py-3 text-xs font-semibold shadow-2xl ring-1 ${
              notification.type === "success"
                ? "bg-emerald-950 text-emerald-200 ring-emerald-500/40"
                : "bg-red-950 text-red-200 ring-red-500/40"
            }`}
          >
            {notification.type === "success" ? (
              <FiCheckCircle className="text-emerald-400" size={16} />
            ) : (
              <FiAlertCircle className="text-red-400" size={16} />
            )}
            <span>{notification.message}</span>
            <button onClick={() => setNotification(null)} className="ml-2 hover:opacity-75">
              <FiX size={14} />
            </button>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Metric Summary Cards */}
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {/* Card 1: Total */}
          <div className="rounded-2xl border border-slate-800 bg-slate-800/50 p-5 shadow-lg backdrop-blur transition hover:border-slate-700">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Total Ingested Schemes</span>
              <span className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
                <FiLayers size={18} />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white">{stats.total}</span>
              <span className="text-xs text-slate-400">in Knowledge Base</span>
            </div>
          </div>

          {/* Card 2: Central */}
          <div className="rounded-2xl border border-slate-800 bg-slate-800/50 p-5 shadow-lg backdrop-blur transition hover:border-slate-700">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Central Schemes</span>
              <span className="rounded-lg bg-indigo-500/10 p-2 text-indigo-400">
                <FiGlobe size={18} />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-indigo-300">{stats.central}</span>
              <span className="text-xs text-slate-400">Govt. of India</span>
            </div>
          </div>

          {/* Card 3: State */}
          <div className="rounded-2xl border border-slate-800 bg-slate-800/50 p-5 shadow-lg backdrop-blur transition hover:border-slate-700">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">State Schemes</span>
              <span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                <FiMapPin size={18} />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-emerald-300">{stats.state}</span>
              <span className="text-xs text-slate-400">Telangana & States</span>
            </div>
          </div>

          {/* Card 4: Active Links */}
          <div className="rounded-2xl border border-slate-800 bg-slate-800/50 p-5 shadow-lg backdrop-blur transition hover:border-slate-700">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Active Working Links</span>
              <span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                <FiCheckCircle size={18} />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-emerald-300">{stats.activeLinks}</span>
              <span className="text-xs text-emerald-400/80">Opening Correctly</span>
            </div>
          </div>
        </div>

        {/* Controls, Filters & Action Bar */}
        <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-800/40 p-5 shadow-md backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Input */}
            <div className="relative flex-1">
              <FiSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search scheme name, ministry, state (e.g. Telangana), portal URL, keyword…"
                className="w-full rounded-xl border border-slate-700 bg-slate-900/90 py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <FiX size={15} />
                </button>
              )}
            </div>

            {/* Filter Tabs & Action Buttons */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Location Scope Filter */}
              <div className="flex rounded-xl border border-slate-700 bg-slate-900 p-1 text-xs font-semibold">
                <button
                  onClick={() => setLocationTab("ALL")}
                  className={`rounded-lg px-3 py-1.5 transition ${
                    locationTab === "ALL" ? "bg-purple-600 text-white shadow" : "text-slate-400 hover:text-white"
                  }`}
                >
                  All ({stats.total})
                </button>
                <button
                  onClick={() => setLocationTab("CENTRAL")}
                  className={`rounded-lg px-3 py-1.5 transition ${
                    locationTab === "CENTRAL" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Central ({stats.central})
                </button>
                <button
                  onClick={() => setLocationTab("STATE")}
                  className={`rounded-lg px-3 py-1.5 transition ${
                    locationTab === "STATE" ? "bg-emerald-600 text-white shadow" : "text-slate-400 hover:text-white"
                  }`}
                >
                  State ({stats.state})
                </button>
              </div>

              {/* Status Filter */}
              <div className="flex rounded-xl border border-slate-700 bg-slate-900 p-1 text-xs font-semibold">
                <button
                  onClick={() => setStatusTab("ALL")}
                  className={`rounded-lg px-2.5 py-1.5 transition ${
                    statusTab === "ALL" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  All Links
                </button>
                <button
                  onClick={() => setStatusTab("ACTIVE")}
                  className={`flex items-center gap-1 rounded-lg px-2.5 py-1.5 transition ${
                    statusTab === "ACTIVE" ? "bg-emerald-700 text-white" : "text-emerald-400 hover:text-emerald-300"
                  }`}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Active
                </button>
                <button
                  onClick={() => setStatusTab("ERROR")}
                  className={`flex items-center gap-1 rounded-lg px-2.5 py-1.5 transition ${
                    statusTab === "ERROR" ? "bg-red-700 text-white" : "text-red-400 hover:text-red-300"
                  }`}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-red-400" /> Errors
                </button>
              </div>

              {/* Verify All Links Button */}
              <button
                onClick={handleCheckAllLinks}
                disabled={isCheckingAll}
                className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/40 bg-emerald-600/20 px-3.5 py-2 text-xs font-semibold text-emerald-300 shadow transition hover:bg-emerald-600/30 disabled:opacity-50"
              >
                <FiActivity className={isCheckingAll ? "animate-spin" : ""} size={14} />
                {isCheckingAll ? "Checking Portals…" : "Verify All Links"}
              </button>

              {/* Refresh Button */}
              <button
                onClick={loadSchemes}
                disabled={isLoading}
                title="Reload schemes from database"
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:opacity-50"
              >
                <FiRefreshCw className={isLoading ? "animate-spin" : ""} size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Content Table / Main Area */}
        {isLoading ? (
          <div className="py-24 text-center">
            <PageLoader label="Fetching official schemes and verifying portal links…" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-500/30 bg-red-950/30 p-8 text-center text-red-300">
            <FiAlertTriangle size={36} className="mx-auto mb-3 text-red-400" />
            <h3 className="text-lg font-bold">Failed to load schemes</h3>
            <p className="mt-1 text-sm">{error}</p>
            <button
              onClick={loadSchemes}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700"
            >
              <FiRefreshCw size={14} /> Retry
            </button>
          </div>
        ) : filteredSchemes.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-800/30 py-16 text-center text-slate-400">
            <FiFilter size={36} className="mx-auto mb-3 text-slate-500" />
            <h3 className="text-base font-semibold text-slate-200">No schemes found matching criteria</h3>
            <p className="mt-1 text-xs">Try clearing the search query or switching the location filter.</p>
            <button
              onClick={() => {
                setSearchQuery("");
                setLocationTab("ALL");
                setStatusTab("ALL");
              }}
              className="mt-4 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-800/40 shadow-xl backdrop-blur">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                {/* Table Header */}
                <thead className="border-b border-slate-800 bg-slate-900/90 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  <tr>
                    <th scope="col" className="px-5 py-4 w-12 text-center">#</th>
                    <th scope="col" className="px-5 py-4 min-w-[280px]">Scheme & Ministry</th>
                    <th scope="col" className="px-5 py-4 min-w-[140px]">Location (Central/State)</th>
                    <th scope="col" className="px-5 py-4 min-w-[200px]">Apply on Portal URL</th>
                    <th scope="col" className="px-5 py-4 min-w-[180px]">Official URL</th>
                    <th scope="col" className="px-5 py-4 min-w-[170px]">Link Status</th>
                    <th scope="col" className="px-5 py-4 w-28 text-center">Action</th>
                  </tr>
                </thead>

                {/* Table Body */}
                <tbody className="divide-y divide-slate-800/80">
                  {paginatedSchemes.map((s, idx) => {
                    const rowNumber = (currentPage - 1) * pageSize + idx + 1;
                    const isChecking = checkingIds.has(s.document_id);

                    return (
                      <tr
                        key={s.document_id}
                        className="transition hover:bg-slate-800/70"
                      >
                        {/* 1. Index */}
                        <td className="px-5 py-4 text-center font-mono text-slate-500">
                          {rowNumber}
                        </td>

                        {/* 2. Scheme & Organization */}
                        <td className="px-5 py-4">
                          <div className="font-semibold text-slate-100 line-clamp-2" title={s.title}>
                            {s.title}
                          </div>
                          <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400 line-clamp-1" title={s.organization}>
                            <span>{s.organization}</span>
                          </div>
                          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                            <span className="rounded bg-slate-700/60 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                              {s.knowledge_type}
                            </span>
                            <span className="rounded bg-purple-500/10 px-1.5 py-0.5 font-mono text-[10px] text-purple-300">
                              {s.chunks_count} chunks
                            </span>
                          </div>
                        </td>

                        {/* 3. Location (Central or State) */}
                        <td className="px-5 py-4">
                          {s.location_type === "state" ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 font-medium text-emerald-300 ring-1 ring-emerald-500/30">
                              <FiMapPin size={12} className="text-emerald-400" />
                              <span>State ({s.state_name})</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/15 px-3 py-1 font-medium text-blue-300 ring-1 ring-blue-500/30">
                              <FiGlobe size={12} className="text-blue-400" />
                              <span>Central (Govt of India)</span>
                            </span>
                          )}
                        </td>

                        {/* 4. Apply on Portal URL */}
                        <td className="px-5 py-4">
                          <div className="flex flex-col gap-1">
                            <a
                              href={s.apply_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="group inline-flex items-center gap-1.5 font-semibold text-emerald-400 hover:text-emerald-300 hover:underline"
                              title={s.apply_url}
                            >
                              <span>Apply on Portal</span>
                              <FiExternalLink size={13} className="transition group-hover:translate-x-0.5" />
                            </a>
                            <div className="flex items-center gap-1 font-mono text-[11px] text-slate-400">
                              <span className="truncate max-w-[160px]" title={s.apply_url}>
                                {s.apply_url.replace(/^https?:\/\//, "")}
                              </span>
                              <button
                                onClick={() => copyToClipboard(s.apply_url)}
                                title="Copy full URL"
                                className="text-slate-500 hover:text-slate-300"
                              >
                                {copiedUrl === s.apply_url ? (
                                  <FiCheck size={12} className="text-emerald-400" />
                                ) : (
                                  <FiCopy size={12} />
                                )}
                              </button>
                            </div>
                          </div>
                        </td>

                        {/* 5. Official URL */}
                        <td className="px-5 py-4">
                          <div className="flex flex-col gap-1">
                            <a
                              href={s.official_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="group inline-flex items-center gap-1 font-medium text-purple-400 hover:text-purple-300 hover:underline"
                              title={s.official_url}
                            >
                              <span>Official Portal</span>
                              <FiExternalLink size={12} className="transition group-hover:translate-x-0.5" />
                            </a>
                            <span className="truncate max-w-[150px] font-mono text-[11px] text-slate-500" title={s.official_url}>
                              {s.official_url.replace(/^https?:\/\//, "")}
                            </span>
                          </div>
                        </td>

                        {/* 6. Link Active Status (Opening correctly or not) */}
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            {s.link_status?.is_active ? (
                              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 text-[11px] font-semibold text-emerald-300 ring-1 ring-emerald-500/30">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                <span>Active (200 OK)</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/15 px-2.5 py-1 text-[11px] font-semibold text-red-300 ring-1 ring-red-500/30">
                                <FiAlertTriangle size={12} className="text-red-400" />
                                <span>{s.link_status?.message || "Error"}</span>
                              </span>
                            )}
                            <button
                              onClick={() => handleCheckLink(s.document_id)}
                              disabled={isChecking}
                              title="Re-check this link live"
                              className="rounded p-1 text-slate-400 hover:bg-slate-700 hover:text-white disabled:opacity-50"
                            >
                              <FiRefreshCw size={12} className={isChecking ? "animate-spin text-purple-400" : ""} />
                            </button>
                          </div>
                          <div className="mt-1 text-[10px] text-slate-500">
                            Verified active
                          </div>
                        </td>

                        {/* 7. Action: Delete Option */}
                        <td className="px-5 py-4 text-center">
                          <button
                            type="button"
                            onClick={() => setSchemeToDelete(s)}
                            title="Delete this scheme from knowledge base"
                            className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-400 transition hover:bg-red-500/20 hover:text-red-300"
                          >
                            <FiTrash2 size={13} />
                            <span>Delete</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-800 bg-slate-900/60 px-5 py-4 sm:flex-row">
              <span className="text-xs text-slate-400">
                Showing <span className="font-semibold text-slate-200">{(currentPage - 1) * pageSize + 1}</span> to{" "}
                <span className="font-semibold text-slate-200">
                  {Math.min(currentPage * pageSize, filteredSchemes.length)}
                </span>{" "}
                of <span className="font-semibold text-slate-200">{filteredSchemes.length}</span> schemes
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-slate-700 disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="px-2 text-xs font-medium text-slate-400">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-slate-700 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Delete Confirmation Modal */}
      {schemeToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border border-red-500/30 bg-slate-900 p-6 shadow-2xl ring-1 ring-red-500/20">
            <div className="flex items-center gap-3 text-red-400">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-500/15 ring-1 ring-red-500/30">
                <FiTrash2 size={22} />
              </div>
              <div>
                <h3 className="font-display text-base font-bold text-white">Delete Government Scheme?</h3>
                <p className="text-xs text-red-300">Permanent Knowledge Base Deletion</p>
              </div>
            </div>

            <p className="mt-4 text-xs leading-relaxed text-slate-300">
              Are you sure you want to permanently delete this scheme from the government knowledge base?
            </p>

            <div className="my-4 rounded-xl border border-slate-800 bg-slate-950 p-3.5">
              <p className="font-semibold text-sm text-slate-100 line-clamp-2">
                {schemeToDelete.title}
              </p>
              <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
                <span className="font-mono text-slate-500">{schemeToDelete.document_id}</span>
                <span>•</span>
                <span>{schemeToDelete.location_label}</span>
                <span>•</span>
                <span className="text-purple-400">{schemeToDelete.chunks_count} chunks</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400">
              This action will permanently delete all associated documents, chunk embeddings from the vector store, and provenance records.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setSchemeToDelete(null)}
                disabled={isDeleting}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 transition hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-xs font-semibold text-white shadow-lg transition hover:bg-red-700 disabled:opacity-60"
              >
                {isDeleting ? (
                  <>
                    <FiRefreshCw className="animate-spin" size={13} /> Deleting…
                  </>
                ) : (
                  <>
                    <FiTrash2 size={13} /> Permanently Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
