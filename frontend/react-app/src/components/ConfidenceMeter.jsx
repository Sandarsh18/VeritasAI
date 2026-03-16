import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

function getEvidenceZone(confidence) {
  if (confidence >= 85) return 'Strong Evidence';
  if (confidence >= 65) return 'Moderate Evidence';
  if (confidence >= 45) return 'Weak Evidence';
  return 'Insufficient Evidence';
}

function getMeterColor(confidence, verdict) {
  if (verdict === 'TRUE') return '#10b981';   // green
  if (verdict === 'FALSE') return '#ef4444';  // red
  if (verdict === 'MISLEADING') return '#f59e0b'; // amber
  if (verdict === 'UNVERIFIED') return '#94a3b8'; // gray
  // Fallback: color by confidence zone
  if (confidence >= 85) return '#ef4444';
  if (confidence >= 65) return '#f97316';
  if (confidence >= 45) return '#f59e0b';
  return '#94a3b8';
}

export default function ConfidenceMeter({ confidence = 0, verdict = '' }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    if (!confidence) {
      setDisplayValue(0);
      return;
    }

    let start = 0;
    const step = confidence / 50;
    const timer = setInterval(() => {
      start += step;
      if (start >= confidence) {
        setDisplayValue(confidence);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(start));
      }
    }, 20);
    return () => clearInterval(timer);
  }, [confidence]);

  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const r = 80;
  const strokeWidth = 12;
  const circumference = Math.PI * r; // half circle
  const offset = circumference - (displayValue / 100) * circumference;

  const color = getMeterColor(confidence, verdict ? verdict.toUpperCase() : '');
  const zone = getEvidenceZone(confidence);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width={size} height={size / 2 + 30} viewBox={`0 0 ${size} ${size / 2 + 30}`}>
        {/* Track */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Progress */}
        <motion.path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 8px ${color})` }}
        />
        {/* Labels */}
        <text x={cx - r - 4} y={cy + 20} fill="rgba(255,255,255,0.4)" fontSize="11" textAnchor="middle">0</text>
        <text x={cx + r + 4} y={cy + 20} fill="rgba(255,255,255,0.4)" fontSize="11" textAnchor="middle">100</text>
        {/* Center value */}
        <text x={cx} y={cy + 10} fill={color} fontSize="32" fontWeight="800" textAnchor="middle"
          style={{ fontFamily: 'Inter, sans-serif' }}>
          {displayValue}%
        </text>
        <text x={cx} y={cy + 28} fill="rgba(255,255,255,0.5)" fontSize="11" textAnchor="middle">
          CONFIDENCE
        </text>
      </svg>
      {/* Evidence zone label */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.2, duration: 0.4 }}
        style={{
          display: 'inline-block',
          padding: '4px 14px',
          borderRadius: 20,
          fontSize: '0.72rem',
          fontWeight: 700,
          letterSpacing: '0.05em',
          background: `${color}22`,
          border: `1px solid ${color}55`,
          color: color,
          backdropFilter: 'blur(8px)',
        }}
      >
        {zone}
      </motion.div>
    </div>
  );
}

