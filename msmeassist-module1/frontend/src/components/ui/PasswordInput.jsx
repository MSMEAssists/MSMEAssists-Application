import { useState } from "react";
import { FiEye, FiEyeOff } from "react-icons/fi";
import { passwordStrength } from "../../utils/validators";

export default function PasswordInput({ label, required, error, value, onChange, showStrength = false, ...rest }) {
  const [visible, setVisible] = useState(false);
  const strength = showStrength ? passwordStrength(value) : null;

  return (
    <div>
      {label && (
        <label className="mb-1.5 block text-[13px] font-semibold text-slate-dark">
          {label} {required && <span className="text-burnt-orange">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          className={[
            "w-full rounded-lg border bg-white px-3.5 py-2.5 pr-12 text-sm text-slate-dark transition-all placeholder:text-slate-text/50",
            "focus:outline-none focus:ring-2 focus:ring-burnt-orange/20 focus:border-burnt-orange",
            error ? "border-error-600 ring-2 ring-error-600/10" : "border-border hover:border-slate-muted",
          ].join(" ")}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-text/60 hover:text-slate-dark p-1"
          tabIndex={-1}
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <FiEyeOff size={16} /> : <FiEye size={16} />}
        </button>
      </div>
      {showStrength && value && (
        <div className="mt-2">
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={[
                  "h-1.5 flex-1 rounded-full transition-colors",
                  i < strength.score
                    ? strength.score === 1
                      ? "bg-error-600"
                      : strength.score === 2
                      ? "bg-warning-600"
                      : "bg-success-600"
                    : "bg-slate-muted/40",
                ].join(" ")}
              />
            ))}
          </div>
          <p className="mt-1 font-data text-[11px] text-slate-text">{strength.label}</p>
        </div>
      )}
      {error && <p className="mt-1.5 text-[12.5px] font-medium text-error-600">{error}</p>}
    </div>
  );
}
