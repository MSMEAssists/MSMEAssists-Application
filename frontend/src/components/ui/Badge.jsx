const VARIANTS = {
  success: "bg-success-100 text-success-600",
  warning: "bg-warning-100 text-warning-600",
  error: "bg-error-100 text-error-600",
  neutral: "bg-surface-sunken text-ink-500",
  saffron: "bg-saffron-100 text-saffron-600",
};

export default function Badge({ variant = "neutral", children, className = "" }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
        VARIANTS[variant],
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
