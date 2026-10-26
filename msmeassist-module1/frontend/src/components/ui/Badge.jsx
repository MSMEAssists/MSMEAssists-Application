const VARIANTS = {
  success: "bg-[#EAF7EE] text-[#1F8A4D] border border-[#C5E8D1]",
  warning: "bg-[#FEF7E6] text-[#C2820A] border border-[#FBE3B3]",
  error: "bg-[#FDEEEC] text-[#C0392B] border border-[#F8C8C4]",
  neutral: "bg-warm-offwhite text-slate-dark border border-border",
  saffron: "bg-burnt-light text-burnt-orange border border-burnt-subtle",
  burnt: "bg-burnt-light text-burnt-orange border border-burnt-subtle",
  charcoal: "bg-charcoal text-white",
};

export default function Badge({ variant = "neutral", children, className = "" }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold select-none",
        VARIANTS[variant] || VARIANTS.neutral,
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
