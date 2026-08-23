import { forwardRef } from "react";

const Select = forwardRef(function Select(
  { label, required, error, hint, options, placeholder, className = "", containerClassName = "", ...rest },
  ref
) {
  return (
    <div className={containerClassName}>
      {label && (
        <label className="mb-1.5 block text-[13px] font-semibold text-ink-700">
          {label} {required && <span className="text-error-600">*</span>}
        </label>
      )}
      <select
        ref={ref}
        className={[
          "w-full rounded-sm border-[1.5px] bg-white px-3.5 py-2.5 text-[14.5px] text-ink-900 transition-colors",
          "focus:outline-none focus:ring-[3px] focus:ring-teal-500/15 focus:border-teal-500",
          error ? "border-error-600" : "border-border",
          className,
        ].join(" ")}
        {...rest}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1.5 text-[12.5px] font-medium text-error-600">{error}</p>}
      {!error && hint && <p className="mt-1.5 text-xs text-ink-400">{hint}</p>}
    </div>
  );
});

export default Select;
