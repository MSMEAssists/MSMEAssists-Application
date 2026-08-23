import { forwardRef } from "react";
import { FiAlertCircle } from "react-icons/fi";

const Input = forwardRef(function Input(
  { label, required, error, hint, className = "", containerClassName = "", ...rest },
  ref
) {
  return (
    <div className={containerClassName}>
      {label && (
        <label className="mb-1.5 block text-[13px] font-semibold text-ink-700">
          {label} {required && <span className="text-error-600">*</span>}
        </label>
      )}
      <input
        ref={ref}
        className={[
          "w-full rounded-sm border-[1.5px] px-3.5 py-2.5 text-[14.5px] text-ink-900 transition-colors",
          "focus:outline-none focus:ring-[3px] focus:ring-teal-500/15 focus:border-teal-500",
          error ? "border-error-600 ring-[3px] ring-error-600/10" : "border-border",
          className,
        ].join(" ")}
        {...rest}
      />
      {error && (
        <p className="mt-1.5 flex items-center gap-1.5 text-[12.5px] font-medium text-error-600">
          <FiAlertCircle size={13} /> {error}
        </p>
      )}
      {!error && hint && <p className="mt-1.5 text-xs text-ink-400">{hint}</p>}
    </div>
  );
});

export default Input;
