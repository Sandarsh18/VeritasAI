import { motion } from "framer-motion";

const COLOR_MAP = {
  TRUE: "#22c55e",
  FALSE: "#ef4444",
  MISLEADING: "#f97316",
  UNVERIFIED: "#6b7280",
  INSUFFICIENT_DATA: "#94a3b8",
};

function VerdictBadge({ verdict }) {
  const label = String(verdict || "UNVERIFIED").toUpperCase();
  const color = COLOR_MAP[label] || COLOR_MAP.UNVERIFIED;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35 }}
      style={{
        background: `${color}20`,
        border: `1px solid ${color}`,
        color,
        boxShadow: `0 0 18px ${color}55`,
      }}
      className="verdict-badge"
    >
      {label}
    </motion.div>
  );
}

export default VerdictBadge;
