// Tailwind's JIT scanner needs complete, literal class name strings — a
// template literal like `sm:grid-cols-${columns}` is invisible to it and
// silently produces no CSS. Mapping to full literal strings fixes that.
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
              "rounded-md border-[1.5px] px-2.5 py-3.5 text-center transition-colors",
              picked ? "border-navy-900 bg-navy-900 text-white" : "border-border bg-white hover:border-teal-500",
            ].join(" ")}
          >
            {opt.icon && <opt.icon className="mx-auto mb-2" size={22} />}
            <div className={`text-[12.5px] font-semibold ${picked ? "text-white" : "text-ink-700"}`}>
              {opt.label}
            </div>
          </button>
        );
      })}
    </div>
  );
}
