import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';

const VERDICTS = {
  TRUE: {
    color: '#10b981',
    bg: 'rgba(16,185,129,0.15)',
    border: 'rgba(16,185,129,0.4)',
    icon: CheckCircle,
    glow: '0 0 30px rgba(16,185,129,0.5)',
    label: 'TRUE'
  },
  FALSE: {
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.15)',
    border: 'rgba(239,68,68,0.4)',
    icon: XCircle,
    glow: '0 0 30px rgba(239,68,68,0.5)',
    label: 'FALSE'
  },
  MISLEADING: {
    color: '#f59e0b',
    bg: 'rgba(245,158,11,0.15)',
    border: 'rgba(245,158,11,0.4)',
    icon: AlertTriangle,
    glow: '0 0 30px rgba(245,158,11,0.5)',
    label: 'MISLEADING'
  },
  UNVERIFIED: {
    color: '#94a3b8',
    bg: 'rgba(148,163,184,0.15)',
    border: 'rgba(148,163,184,0.4)',
    icon: HelpCircle,
    glow: '0 0 30px rgba(148,163,184,0.3)',
    label: 'UNVERIFIED'
  }
};

export default function VerdictBadge({ verdict, size = 'large' }) {
  const v = VERDICTS[verdict] || VERDICTS.UNVERIFIED;
  const Icon = v.icon;
  const isLarge = size === 'large';

  return (
    <motion.div
      initial={{ scale: 0, rotate: -10 }}
      animate={{ scale: 1, rotate: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.2 }}
      className="verdict-glow"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: isLarge ? 12 : 6,
        padding: isLarge ? '16px 32px' : '6px 14px',
        borderRadius: isLarge ? 100 : 20,
        background: v.bg,
        border: `2px solid ${v.border}`,
        boxShadow: v.glow,
        animation: 'verdictGlow 2s ease-in-out infinite',
        color: v.color,
      }}
    >
      <motion.div
        animate={{ scale: [1, 1.1, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <Icon size={isLarge ? 32 : 16} strokeWidth={2.5} />
      </motion.div>
      <span style={{
        fontWeight: 800,
        fontSize: isLarge ? '1.8rem' : '0.875rem',
        letterSpacing: isLarge ? '0.05em' : '0.03em',
      }}>
        {v.label}
      </span>
    </motion.div>
  );
}
