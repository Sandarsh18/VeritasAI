import { motion } from "framer-motion";

const COLOR_MAP = {
  TRUE: "#22c55e",
  FALSE: "#ef4444",
  MISLEADING: "#f97316",
  UNVERIFIED: "#6b7280",
};

function VerdictBadge({ verdict }) {
  const color = COLOR_MAP[verdict] || COLOR_MAP.UNVERIFIED;

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
      {verdict}
    </motion.div>
  );
}

export default VerdictBadge;
