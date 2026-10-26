import { useState, useRef, useEffect } from "react";
import { FiChevronDown, FiGlobe } from "react-icons/fi";
import { useLanguage } from "../../context/LanguageContext";

export default function LanguageSelector({ onDark = false }) {
  const { lang, setLang } = useLanguage();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={[
          "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors",
          onDark
            ? "text-slate-muted hover:text-white bg-charcoal-800/80 border border-charcoal-700"
            : "text-slate-dark hover:text-charcoal bg-white/90 border border-border shadow-xs",
        ].join(" ")}
        aria-label="Select language"
      >
        <FiGlobe size={13} className={onDark ? "text-burnt-orange" : "text-burnt-orange"} />
        <span>{lang === "te" ? "తెలుగు" : "English"}</span>
        <FiChevronDown size={12} className="opacity-70" />
      </button>

      {open && (
        <div className="absolute right-0 mt-1.5 w-32 origin-top-right rounded-lg border border-border bg-white p-1 shadow-elevated z-50">
          <button
            type="button"
            onClick={() => {
              setLang("en");
              setOpen(false);
            }}
            className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-medium transition-colors ${
              lang === "en" ? "bg-burnt-light font-bold text-burnt-orange" : "text-slate-dark hover:bg-warm-offwhite"
            }`}
          >
            <span>English</span>
            {lang === "en" && <span className="text-burnt-orange">✓</span>}
          </button>
          <button
            type="button"
            onClick={() => {
              setLang("te");
              setOpen(false);
            }}
            className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-medium transition-colors ${
              lang === "te" ? "bg-burnt-light font-bold text-burnt-orange" : "text-slate-dark hover:bg-warm-offwhite"
            }`}
          >
            <span>తెలుగు</span>
            {lang === "te" && <span className="text-burnt-orange">✓</span>}
          </button>
        </div>
      )}
    </div>
  );
}
