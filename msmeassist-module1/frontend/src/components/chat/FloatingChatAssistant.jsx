import { useState, useRef, useEffect } from "react";
import {
  FiMessageSquare,
  FiX,
  FiSend,
  FiFileText,
  FiExternalLink,
  FiShield,
  FiCheckCircle,
  FiAlertCircle,
  FiCornerDownLeft,
} from "react-icons/fi";
import schemesService from "../../services/schemesService";
import { useLanguage } from "../../context/LanguageContext";
import SafeMarkdownRenderer from "./SafeMarkdownRenderer";
import { cleanPortalUrl, validateDirectApplicationUrl } from "../../utils/urlSanitizer";

const SUGGESTIONS_EN = [
  "Which schemes are open for my business type?",
  "What documents are required for MSME schemes?",
  "How do I check my eligibility for PMEGP?",
  "How does the CGTMSE credit guarantee work?",
  "What subsidies exist for manufacturing units?",
];

const SUGGESTIONS_TE = [
  "నా వ్యాపార రకానికి ఏ పథకాలు అందుబాటులో ఉన్నాయి?",
  "MSME పథకాలకు ఏ పత్రాలు అవసరం?",
  "PMEGP కోసం నా అర్హతను ఎలా తనిఖీ చేయాలి?",
  "CGTMSE క్రెడిట్ గ్యారెంటీ ఎలా పనిచేస్తుంది?",
  "తయారీ యూనిట్లకు ఎలాంటి సబ్సిడీలు ఉన్నాయి?",
];

export default function FloatingChatAssistant() {
  const { lang } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState(() => [
    {
      id: "initial",
      sender: "assistant",
      text:
        lang === "te"
          ? "నమస్కారం! నేను మీ MSMEAssist AI సహాయకుడిని.\n\nప్రభుత్వ పథకాలు, అర్హత ప్రమాణాలు, సబ్సిడీలు మరియు దరఖాస్తు ప్రక్రియ గురించి నన్ను ఏదైనా అడగండి."
          : "Hello! I am your **MSMEAssist Government AI Assistant**.\n\nAsk me anything about official government schemes, eligibility guidelines, capital subsidies, or statutory application processes.",
      citations: [],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const isSubmittingRef = useRef(false);
  const abortControllerRef = useRef(null);

  const suggestions = lang === "te" ? SUGGESTIONS_TE : SUGGESTIONS_EN;

  const lastMsg = messages[messages.length - 1];
  const activeSuggestions = (() => {
    if (lastMsg && lastMsg.sender === "assistant") {
      if (lastMsg.intent === "SCHEME_RECONSIDERATION") {
        return [
          "How to qualify for PMEGP?",
          "I need a collateral-free loan",
          "What documents are required?",
        ];
      }
      if (lastMsg.intent === "PROFILE_IMPROVEMENT_ADVISORY") {
        return [
          "Show alternative schemes for my profile",
          "What documents are needed for Udyam?",
          "Can I get a machinery loan?",
        ];
      }
      if (lastMsg.intent === "BEST_SCHEME_ADVISORY") {
        return [
          "Why am I not eligible for other schemes?",
          "I want a higher subsidy",
          "Suggest machinery loan options",
        ];
      }
    }
    return suggestions.slice(0, 3);
  })();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSend = async (textToSend) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading || isSubmittingRef.current) return;

    isSubmittingRef.current = true;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    const timeoutId = setTimeout(() => abortController.abort(), 25000);

    const currentTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsgId = Date.now().toString();

    // Append user message immediately
    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        sender: "user",
        text: query,
        timestamp: currentTime,
      },
    ]);
    setInput("");
    setIsLoading(true);

    const historyPayload = messages
      .filter((m) => m.id !== "initial" && !m.isError)
      .slice(-6)
      .map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text,
      }));

    try {
      const result = await schemesService.queryAssistant({
        query,
        conversationHistory: historyPayload,
        signal: abortController.signal,
      });
      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text:
          result?.answer_text ||
          "I retrieved information from official government scheme repositories for your query.",
        citations: result?.citations || [],
        sufficient: result?.has_sufficient_context,
        intent: result?.intent,
        recommendedSchemes: result?.recommended_schemes,
        eligibilityGaps: result?.eligibility_gaps,
        nextSteps: result?.next_steps,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const isAborted =
        err?.name === "AbortError" ||
        err?.name === "CanceledError" ||
        err?.code === "ERR_CANCELED";

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: isAborted
            ? "The government knowledge retrieval took longer than expected. Please try again or ask a more specific query."
            : err?.response?.data?.detail ||
              err?.message ||
              "The official government knowledge service is momentarily unreachable. Please check your network connection or try again in a few moments.",
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      clearTimeout(timeoutId);
      isSubmittingRef.current = false;
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Floating Trigger Button when closed */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="group flex items-center gap-2.5 rounded-full bg-charcoal px-4.5 py-3 text-white shadow-elevated hover:bg-burnt-orange transition-all duration-200 cursor-pointer border-2 border-white/20 active:scale-95"
          aria-label="Open AI Scheme Assistant"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-burnt-orange text-white group-hover:bg-charcoal transition-colors">
            <FiMessageSquare size={15} />
          </div>
          <span className="text-xs font-bold tracking-wide">
            {lang === "te" ? "సహాయక చాట్" : "Chat Assistant"}
          </span>
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
      )}

      {/* Slide-up Chat Panel when open */}
      {isOpen && (
        <div className="flex flex-col w-[390px] sm:w-[440px] h-[600px] max-h-[88vh] rounded-2xl border border-border bg-white shadow-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border bg-charcoal px-4 py-3.5 text-white">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-burnt-orange text-white shadow-xs">
                <FiMessageSquare size={16} />
              </div>
              <div>
                <h3 className="text-xs font-bold leading-tight flex items-center gap-1.5">
                  <span>MSMEAssist Assistant</span>
                  <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.2 text-[9px] font-bold bg-burnt-orange/20 text-burnt-orange border border-burnt-orange/30">
                    AI
                  </span>
                </h3>
                <p className="text-[10px] text-slate-muted flex items-center gap-1 mt-0.5">
                  <FiShield size={10} className="text-burnt-orange" />
                  <span>Grounded in Official .gov.in Sources</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="rounded-lg p-1.5 text-slate-muted hover:bg-charcoal-800 hover:text-white transition"
                aria-label="Close chat"
              >
                <FiX size={17} />
              </button>
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-warm-offwhite/40">
            {messages.map((msg) => {
              const isUser = msg.sender === "user";
              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? "items-end ml-8" : "items-start mr-4"}`}
                >
                  {/* Sender Label & Timestamp */}
                  <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium text-slate-text px-1">
                    <span>{isUser ? "You" : "MSMEAssist AI"}</span>
                    <span>•</span>
                    <span>{msg.timestamp || "Now"}</span>
                  </div>

                  {/* Message Bubble */}
                  <div
                    className={[
                      "w-full rounded-2xl px-4 py-3 shadow-xs text-xs leading-relaxed transition-all",
                      isUser
                        ? "bg-burnt-orange text-white rounded-tr-xs font-medium max-w-[92%]"
                        : "bg-white text-slate-dark border border-border/80 rounded-tl-xs max-w-full",
                      msg.isError ? "border-error-100 bg-[#FDEEEC] text-error-700" : "",
                    ].join(" ")}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                    ) : msg.isError ? (
                      <div className="flex items-start gap-2">
                        <FiAlertCircle size={15} className="text-error-600 mt-0.5 shrink-0" />
                        <div className="leading-relaxed">{msg.text}</div>
                      </div>
                    ) : (
                      <SafeMarkdownRenderer content={msg.text} />
                    )}

                    {/* Citations snippet if present */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-border/70 space-y-1.5">
                        <div className="flex items-center gap-1 text-[10px] font-bold text-slate-text uppercase tracking-wider">
                          <FiCheckCircle size={10} className="text-emerald-600" />
                          <span>Official Government Citations:</span>
                        </div>
                        <div className="space-y-1">
                          {msg.citations.slice(0, 3).map((c, i) => (
                            <div
                              key={i}
                              className="flex items-center justify-between text-[11px] bg-warm-offwhite/80 p-2 rounded-lg border border-border/80"
                            >
                              <div className="truncate max-w-[210px] sm:max-w-[240px]">
                                <span className="font-semibold text-charcoal block truncate">
                                  {c.title || c.organization || "Official Gazette / Guideline"}
                                </span>
                                {c.organization && (
                                  <span className="text-[10px] text-slate-text block truncate">
                                    {c.organization} {c.page_number ? `(Page ${c.page_number})` : ""}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0 ml-2">
                                {(() => {
                                  const appUrl = validateDirectApplicationUrl(c.official_application_url || c.application_portal_url);
                                  if (appUrl) {
                                    return (
                                      <a
                                        href={appUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-white font-semibold hover:bg-emerald-700 inline-flex items-center gap-1 bg-emerald-600 px-2 py-1 rounded text-[10px] shadow-xs"
                                        title={`Apply directly on official portal: ${appUrl}`}
                                      >
                                        <span>Apply</span> <FiExternalLink size={10} />
                                      </a>
                                    );
                                  }
                                  return null;
                                })()}
                                {(c.scheme_details_url || c.official_url) && (
                                  <a
                                    href={cleanPortalUrl(c.scheme_details_url || c.official_url)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-burnt-orange font-semibold hover:underline inline-flex items-center gap-0.5 bg-white px-2 py-1 rounded border border-border text-[10px]"
                                    title="Official guidelines and scheme information"
                                  >
                                    <span>Guidelines</span> <FiExternalLink size={10} />
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Subtle Loading Indicator inside an assistant bubble */}
            {isLoading && (
              <div className="flex flex-col items-start mr-4 animate-in fade-in duration-150">
                <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium text-slate-text px-1">
                  <span>MSMEAssist AI</span>
                  <span>•</span>
                  <span>Thinking...</span>
                </div>
                <div className="rounded-2xl rounded-tl-xs bg-white border border-border/80 px-4 py-3 shadow-xs">
                  <div className="flex items-center gap-2.5 text-xs text-slate-text">
                    <span className="flex gap-1">
                      <span className="h-2 w-2 rounded-full bg-burnt-orange animate-bounce" />
                      <span className="h-2 w-2 rounded-full bg-burnt-orange animate-bounce [animation-delay:0.2s]" />
                      <span className="h-2 w-2 rounded-full bg-burnt-orange animate-bounce [animation-delay:0.4s]" />
                    </span>
                    <span className="text-[11px] font-medium text-charcoal">
                      Searching official government schemes & gazettes…
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestions Chips */}
          <div className="border-t border-border bg-white px-3.5 py-2.5 overflow-x-auto">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold text-slate-text uppercase shrink-0">
                Suggested:
              </span>
              {activeSuggestions.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleSend(s)}
                  className="rounded-full border border-border bg-warm-offwhite/80 px-3 py-1 text-[11px] font-medium text-slate-dark hover:border-burnt-orange hover:text-burnt-orange hover:bg-burnt-light/20 transition whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 border-t border-border bg-white p-3"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              disabled={isLoading}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                lang === "te"
                  ? "పథకాల గురించి ఏదైనా అడగండి..."
                  : "Ask about MSME schemes, loans, subsidies..."
              }
              className="flex-1 rounded-xl border border-border px-3.5 py-2.5 text-xs text-slate-dark placeholder:text-slate-text/60 focus:border-burnt-orange focus:outline-none disabled:bg-warm-offwhite/50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-burnt-orange text-white hover:bg-burnt-hover disabled:opacity-40 transition cursor-pointer shrink-0 shadow-xs active:scale-95"
              aria-label="Send message"
            >
              <FiSend size={14} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
