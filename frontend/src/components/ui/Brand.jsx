export function BrandMark({ size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M20 2 L36 10 V22 C36 30.5 29 36.5 20 38 C11 36.5 4 30.5 4 22 V10 L20 2Z"
        stroke="currentColor"
        strokeWidth="2"
        fill="currentColor"
        fillOpacity="0.08"
      />
      <path
        d="M12 24 L17 17 L22 21 L29 12"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="12" cy="24" r="2" fill="currentColor" />
      <circle cx="17" cy="17" r="2" fill="white" />
      <circle cx="22" cy="21" r="2" fill="currentColor" />
      <circle cx="29" cy="12" r="2" fill="white" />
    </svg>
  );
}

export default function Brand({ onDark = false, size = 34 }) {
  return (
    <div className={`flex items-center gap-2.5 ${onDark ? "text-teal-100" : "text-teal-600"}`}>
      <BrandMark size={size} />
      <span className={`font-display text-lg font-bold ${onDark ? "text-white" : "text-navy-900"}`}>
        MSME<span className={onDark ? "text-teal-300" : "text-teal-600"}>Assist</span>
      </span>
    </div>
  );
}
