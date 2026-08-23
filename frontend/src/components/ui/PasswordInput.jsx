import { useState } from "react";
import { FiEye, FiEyeOff } from "react-icons/fi";
import { passwordStrength } from "../../utils/validators";

export default function PasswordInput({ label, required, error, value, onChange, showStrength = false, ...rest }) {
  const [visible, setVisible] = useState(false);
  const strength = showStrength ? passwordStrength(value) : null;

  return (
    <div>
      {label && (
        <label className="mb-1.5 block text-[13px] font-semibold text-ink-700">
          {label} {required && <span className="text-error-600">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          className={[
            "w-full rounded-sm border-[1.5px] px-3.5 py-2.5 pr-16 text-[14.5px] text-ink-900 transition-colors",
            "focus:outline-none focus:ring-[3px] focus:ring-teal-500/15 focus:border-teal-500",
            error ? "border-error-600" : "border-border",
          ].join(" ")}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-700"
          tabIndex={-1}
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <FiEyeOff size={16} /> : <FiEye size={16} />}
        </button>
      </div>
      {showStrength && value && (
        <div className="mt-2">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={[
                  "h-1 flex-1 rounded-full",
                  i < strength.score
                    ? strength.score === 1
                      ? "bg-error-600"
                      : strength.score === 2
                      ? "bg-warning-600"
                      : "bg-success-600"
                    : "bg-surface-sunken",
                ].join(" ")}
              />
            ))}
          </div>
          <p className="mt-1 font-data text-[11.5px] text-ink-400">{strength.label}</p>
        </div>
      )}
      {error && <p className="mt-1.5 text-[12.5px] font-medium text-error-600">{error}</p>}
    </div>
  );
}
