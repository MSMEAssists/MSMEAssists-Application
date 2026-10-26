import { FiLoader } from "react-icons/fi";

export function Spinner({ size = 16, className = "" }) {
  return <FiLoader size={size} className={`animate-spin ${className}`} />;
}

export function PageLoader({ label = "Loading…" }) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-ink-500">
      <Spinner size={26} className="text-teal-600" />
      <p className="text-sm font-medium">{label}</p>
    </div>
  );
}
