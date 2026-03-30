import { motion } from "framer-motion";
import { useMemo } from "react";

function meterColor(value) {
  if (value > 75) return "#22c55e";
  if (value >= 50) return "#f97316";
  return "#ef4444";
}

function ConfidenceMeter({ value = 0 }) {
  const safe = Math.max(0, Math.min(100, value));
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const progress = (safe / 100) * circumference;
  const color = useMemo(() => meterColor(safe), [safe]);

  return (
    <div className="confidence-wrap">
      <svg width="220" height="130" viewBox="0 0 220 130">
        <path
          d="M 30 110 A 80 80 0 0 1 190 110"
          fill="none"
          stroke="#2a2a36"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <motion.path
          d="M 30 110 A 80 80 0 0 1 190 110"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="confidence-value" style={{ color }}>
        {safe}%
      </div>
    </div>
  );
}

export default ConfidenceMeter;
