import { motion } from "framer-motion";
import { useCompleteness } from "../../hooks/useCompleteness";

export default function CompletenessWidget() {
  const { percentage, completedCount, totalSections } = useCompleteness();

  return (
    <div className="rounded-lg bg-gradient-to-br from-navy-900 to-navy-800 p-5 text-white">
      <div className="font-data text-xs uppercase tracking-wider text-teal-100/70">Profile Completeness</div>
      <div className="mb-3.5 font-display text-4xl font-bold leading-none">{percentage}%</div>
      <div className="mb-2.5 h-2 overflow-hidden rounded-full bg-white/15">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-teal-300 to-teal-500"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
      <div className="text-[12.5px] text-teal-100/70">
        {completedCount} of {totalSections} sections complete
      </div>
    </div>
  );
}
