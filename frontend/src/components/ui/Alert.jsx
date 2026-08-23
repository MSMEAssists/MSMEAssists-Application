import { FiAlertCircle, FiAlertTriangle, FiCheckCircle } from "react-icons/fi";

const STYLES = {
  error: { wrap: "bg-error-100 text-error-600", Icon: FiAlertCircle },
  warning: { wrap: "bg-warning-100 text-warning-600", Icon: FiAlertTriangle },
  success: { wrap: "bg-success-100 text-success-600", Icon: FiCheckCircle },
};

export default function Alert({ variant = "error", children, className = "" }) {
  if (!children) return null;
  const { wrap, Icon } = STYLES[variant];
  return (
    <div className={`flex items-start gap-2.5 rounded-md px-4 py-3 text-[13px] font-medium ${wrap} ${className}`}>
      <Icon size={16} className="mt-0.5 flex-shrink-0" />
      <span>{children}</span>
    </div>
  );
}
