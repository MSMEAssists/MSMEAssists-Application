import { FiAlertCircle, FiAlertTriangle, FiCheckCircle } from "react-icons/fi";

const STYLES = {
  error: { wrap: "bg-[#FDEEEC] text-[#C0392B] border border-[#F8C8C4]", Icon: FiAlertCircle },
  warning: { wrap: "bg-[#FEF7E6] text-[#C2820A] border border-[#FBE3B3]", Icon: FiAlertTriangle },
  success: { wrap: "bg-[#EAF7EE] text-[#1F8A4D] border border-[#C5E8D1]", Icon: FiCheckCircle },
};

export default function Alert({ variant = "error", children, className = "" }) {
  if (!children) return null;
  const { wrap, Icon } = STYLES[variant] || STYLES.error;
  return (
    <div className={`flex items-start gap-2.5 rounded-lg px-4 py-3 text-[13px] font-medium leading-relaxed ${wrap} ${className}`}>
      <Icon size={16} className="mt-0.5 flex-shrink-0" />
      <span>{children}</span>
    </div>
  );
}
