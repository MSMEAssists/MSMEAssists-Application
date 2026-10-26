import { forwardRef } from "react";

const TextArea = forwardRef(function TextArea(
  { label, required, error, hint, className = "", containerClassName = "", ...rest },
  ref
) {
  return (
    <div className={containerClassName}>
      {label && (
        <label className="mb-1.5 block text-[13px] font-semibold text-slate-dark">
          {label} {required && <span className="text-burnt-orange">*</span>}
        </label>
      )}
      <textarea
        ref={ref}
        className={[
          "w-full rounded-lg border bg-white px-3.5 py-2.5 text-sm text-slate-dark transition-all placeholder:text-slate-text/50",
          "focus:outline-none focus:ring-2 focus:ring-burnt-orange/20 focus:border-burnt-orange",
          error ? "border-error-600 ring-2 ring-error-600/10" : "border-border hover:border-slate-muted",
          className,
        ].join(" ")}
        {...rest}
      />
      {error && <p className="mt-1.5 text-[12.5px] font-medium text-error-600">{error}</p>}
      {!error && hint && <p className="mt-1.5 text-xs text-slate-text">{hint}</p>}
    </div>
  );
});

export default TextArea;
