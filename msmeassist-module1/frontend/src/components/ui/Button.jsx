import { forwardRef } from "react";
import { FiLoader } from "react-icons/fi";

const VARIANTS = {
  primary: "bg-burnt-orange text-white hover:bg-burnt-hover active:bg-burnt-active shadow-sm disabled:opacity-50",
  secondary: "bg-white text-slate-dark border border-border hover:border-charcoal hover:bg-warm-offwhite disabled:opacity-50",
  charcoal: "bg-charcoal text-white hover:bg-charcoal-800 disabled:opacity-50",
  ghost: "bg-transparent text-slate-text hover:text-charcoal hover:bg-warm-offwhite/80",
  cta: "bg-burnt-orange text-white hover:bg-burnt-hover active:bg-burnt-active shadow-sm font-bold disabled:opacity-50",
  danger: "bg-white text-error-600 border border-error-100 hover:bg-error-100",
};

const Button = forwardRef(function Button(
  { variant = "primary", isLoading = false, fullWidth = false, size = "md", className = "", children, disabled, ...rest },
  ref
) {
  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs rounded-md",
    md: "px-4.5 py-2.5 text-sm rounded-lg",
    lg: "px-6 py-3.5 text-base rounded-lg",
  }[size] || "px-4.5 py-2.5 text-sm rounded-lg";

  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={[
        "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 cursor-pointer disabled:cursor-not-allowed select-none",
        sizeClasses,
        VARIANTS[variant] || VARIANTS.primary,
        fullWidth ? "w-full" : "",
        className,
      ].join(" ")}
      {...rest}
    >
      {isLoading && <FiLoader className="animate-spin shrink-0" size={15} />}
      {children}
    </button>
  );
});

export default Button;
