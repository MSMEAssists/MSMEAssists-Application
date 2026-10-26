const COLUMN_CLASS = {
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-3",
  4: "sm:grid-cols-4",
};

export default function SelectCard({ options, value, onChange, columns = 4 }) {
  return (
    <div className={`grid grid-cols-2 gap-2.5 ${COLUMN_CLASS[columns] || COLUMN_CLASS[4]}`}>
      {options.map((opt) => {
        const picked = opt.value === value;
        return (
          <button
            type="button"
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={[
              "rounded-xl border px-3 py-3.5 text-center transition-all cursor-pointer",
              picked
                ? "border-burnt-orange bg-burnt-light text-burnt-orange font-bold ring-2 ring-burnt-orange/20 shadow-xs"
                : "border-border bg-white text-slate-dark hover:border-slate-muted hover:bg-warm-offwhite/50",
            ].join(" ")}
          >
            {opt.icon && (
              <opt.icon
                className={`mx-auto mb-2 ${picked ? "text-burnt-orange" : "text-slate-text"}`}
                size={22}
              />
            )}
            <div className={`text-xs font-semibold ${picked ? "text-burnt-orange" : "text-slate-dark"}`}>
              {opt.label}
            </div>
          </button>
        );
      })}
    </div>
  );
}
