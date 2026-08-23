import { forwardRef } from "react";
import { FiLoader } from "react-icons/fi";

const VARIANTS = {
  primary: "bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-60",
  secondary: "bg-transparent text-navy-900 border-[1.5px] border-border-strong hover:border-navy-900 hover:bg-surface-sunken",
  ghost: "bg-transparent text-ink-500 hover:text-navy-900",
  cta: "bg-gradient-to-br from-teal-600 to-teal-700 text-white hover:brightness-110",
  danger: "bg-transparent text-error-600 border-[1.5px] border-error-100 hover:bg-error-100",
};

const Button = forwardRef(function Button(
  { variant = "primary", isLoading = false, fullWidth = false, className = "", children, disabled, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-sm px-5 py-3 text-sm font-semibold transition-colors",
        VARIANTS[variant],
        fullWidth ? "w-full" : "",
        className,
      ].join(" ")}
      {...rest}
    >
      {isLoading && <FiLoader className="animate-spin" size={15} />}
      {children}
    </button>
  );
});

export default Button;
