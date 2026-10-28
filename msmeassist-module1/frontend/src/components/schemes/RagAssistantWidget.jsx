import { useState } from "react";
import { FiMessageSquare, FiSend, FiExternalLink, FiAlertCircle, FiInfo, FiCheck, FiFileText } from "react-icons/fi";
import schemesService from "../../services/schemesService";
import Button from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import SafeMarkdownRenderer from "../chat/SafeMarkdownRenderer";
import { cleanPortalUrl, validateDirectApplicationUrl } from "../../utils/urlSanitizer";

const SUGGESTIONS = [
  "What are the eligibility requirements for PMEGP?",
  "What government loan options are available for MSMEs?",
  "What subsidies exist for manufacturing units?",
  "How do credit guarantee schemes work for small businesses?",
];

export default function RagAssistantWidget() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await schemesService.queryAssistant({ query: query.trim() });
      setResponse(data);
    } catch (err) {
      if (err?.code === "RAG_SERVICE_UNAVAILABLE" || err?.status === 503) {
        setError("The Government Information RAG System is currently unavailable. Please make sure the service is running.");
      } else {
        setError(err?.message || "Failed to query the government knowledge assistant. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
  };

  return (
    <div className="rounded-lg border border-border bg-white p-6 shadow-card">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-100 text-teal-700">
          <FiMessageSquare size={20} />
        </div>
        <div>
          <h3 className="text-lg font-bold text-navy-900">Grounded Government AI Assistant</h3>
          <p className="text-xs text-ink-500">
            Answers strictly derived from approved official Indian government sources (.gov.in) with verifiable citations.
          </p>
        </div>
      </div>

      {/* Suggestion Chips */}
      <div className="mb-4">
        <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-ink-400">
          Suggested Queries
        </span>
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleSuggestionClick(s)}
              className="rounded border border-border bg-surface-sunken px-2.5 py-1 text-xs text-ink-700 transition hover:border-teal-500 hover:bg-teal-50 hover:text-teal-700"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="mb-5 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask any question about MSME schemes, loans, or subsidies…"
          className="flex-1 rounded-sm border border-border px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-teal-500 focus:outline-none"
        />
        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          disabled={!query.trim() || isLoading}
          className="px-5"
        >
          <FiSend size={15} />
          <span>Ask</span>
        </Button>
      </form>

      {/* Error state */}
      {error && (
        <div className="mb-4 flex items-start gap-2.5 rounded-md border border-error-100 bg-error-100/50 p-3.5 text-xs text-error-600">
          <FiAlertCircle size={16} className="mt-0.5 flex-shrink-0" />
          <div>{error}</div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-8 text-center text-ink-500">
          <Spinner size="md" label="Searching official government sources & verifying citations…" />
        </div>
      )}

      {/* Response Card */}
      {response && !isLoading && (
        <div className="rounded-md border border-border bg-surface-sunken p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-500">
              Query Result
            </span>
            {response.has_sufficient_context ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-success-600">
                <FiCheck size={12} /> Grounded in Official Sources
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-warning-600">
                <FiInfo size={12} /> Insufficient Government Context
              </span>
            )}
          </div>

          <p className="mb-3 text-xs font-semibold text-navy-900">
            "{response.query}"
          </p>

          <div className="mb-4 rounded-xl bg-white p-4 leading-relaxed border border-border shadow-xs">
            <SafeMarkdownRenderer content={response.answer_text} />
          </div>

          {/* Citations List */}
          {response.citations && response.citations.length > 0 && (
            <div>
              <span className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-ink-500">
                Mandatory Official Citations ({response.citations.length})
              </span>
              <div className="space-y-2">
                {response.citations.map((citation, idx) => (
                  <div
                    key={citation.chunk_id || idx}
                    className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-white px-3 py-2 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-navy-900">
                        {citation.title || citation.organization || "Official Source"}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink-500">
                        <span>{citation.organization}</span>
                        {citation.page_number != null && (
                          <span className="inline-flex items-center gap-0.5 text-ink-500">
                            <FiFileText size={10} /> Page {citation.page_number}
                          </span>
                        )}
                        {citation.chunk_id && (
                          <span className="font-data">Chunk {citation.chunk_id}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {(() => {
                        const appUrl = validateDirectApplicationUrl(
                          citation.official_application_url || citation.application_portal_url
                        );
                        if (appUrl) {
                          return (
                            <a
                              href={appUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-700"
                            >
                              Apply Online <FiExternalLink size={12} />
                            </a>
                          );
                        }
                        if (citation.verification_status === "verified_offline") {
                          return (
                            <span
                              className="text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 italic"
                              title="Applications are submitted offline through Member Lending Institutions / commercial banks"
                            >
                              Bank / Offline Application
                            </span>
                          );
                        }
                        return (
                          <span
                            className="text-[11px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 italic"
                            title="Direct online application link could not be verified"
                          >
                            Online portal unverified
                          </span>
                        );
                      })()}
                      {(citation.scheme_details_url || citation.official_url) && (
                        <a
                          href={cleanPortalUrl(citation.scheme_details_url || citation.official_url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded border border-border bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-teal-700 hover:underline"
                        >
                          Official Guidelines <FiExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
