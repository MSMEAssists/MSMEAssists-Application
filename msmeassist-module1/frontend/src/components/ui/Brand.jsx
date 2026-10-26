export function BrandMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Left pillar - Charcoal / slate */}
      <rect x="4" y="10" width="7" height="20" rx="3.5" fill="#202831" />
      {/* Center pillar - Burnt Orange */}
      <rect x="14.5" y="4" width="7" height="26" rx="3.5" fill="#E87545" />
      {/* Right pillar - Charcoal / dark */}
      <rect x="25" y="12" width="7" height="18" rx="3.5" fill="#202831" />
      {/* Upward chevron / peak connector accent */}
      <circle cx="18" cy="7.5" r="2" fill="#FFFFFF" />
    </svg>
  );
}

export default function Brand({ onDark = false, size = 32, showSubtitle = true }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex shrink-0 items-center justify-center">
        <BrandMark size={size} />
      </div>
      <div className="flex flex-col leading-none">
        <span className={`font-display text-[19px] font-extrabold tracking-tight ${onDark ? "text-white" : "text-charcoal"}`}>
          MSME<span className="text-burnt-orange">Assist</span>
        </span>
        {showSubtitle && (
          <span className={`text-[10px] font-medium tracking-normal mt-0.5 ${onDark ? "text-slate-muted/80" : "text-slate-text"}`}>
            Government Schemes. Made Simple.
          </span>
        )}
      </div>
    </div>
  );
}
