import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';

const AGENT_CONFIG = {
  prosecutor: {
    emoji: '🔴',
    label: 'Prosecutor',
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.08)',
    border: 'rgba(239,68,68,0.25)',
    model: 'Mistral 7B',
    modelColor: '#ef4444',
  },
  defender: {
    emoji: '🟢',
    label: 'Defender',
    color: '#10b981',
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.25)',
    model: 'Phi-3 Mini',
    modelColor: '#10b981',
  },
  judge: {
    emoji: '⚖️',
    label: 'Judge',
    color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.08)',
    border: 'rgba(139,92,246,0.25)',
    model: 'LLaMA 3',
    modelColor: '#8b5cf6',
  },
};

function TypewriterText({ text, delay = 0 }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    let index = 0;
    let interval;
    const timer = setTimeout(() => {
      interval = setInterval(() => {
        setDisplayed(text.slice(0, index));
        index += 1;
        if (index > text.length) {
          clearInterval(interval);
        }
      }, 12);
    }, delay);

    return () => {
      clearTimeout(timer);
      if (interval) clearInterval(interval);
    };
  }, [text, delay]);

  return (
    <span>
      {displayed}
      <span className="cursor">|</span>
    </span>
  );
}

export default function AgentCard({ type, data, delay = 0, index = 0, isLeft = false }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = AGENT_CONFIG[type] || AGENT_CONFIG.judge;
  const args = data?.arguments || [];

  return (
    <motion.div
      initial={{ opacity: 0, x: isLeft ? -30 : 30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.max(delay, index * 0.15), duration: 0.5 }}
      className={type === 'prosecutor' ? 'prosecutor-card' : type === 'defender' ? 'defender-card' : 'glass-card'}
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: 16,
        padding: '1.25rem',
        backdropFilter: 'blur(20px)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '1.4rem' }}>{cfg.emoji}</span>
          <div>
            <div style={{ fontWeight: 700, color: cfg.color, fontSize: '1rem' }}>{cfg.label}</div>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>Agent Analysis</div>
            {cfg.model && (
              <div style={{
                display: 'inline-block',
                marginTop: 4,
                padding: '2px 8px',
                borderRadius: 20,
                fontSize: '0.65rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                background: `${cfg.modelColor}22`,
                border: `1px solid ${cfg.modelColor}55`,
                color: cfg.modelColor,
                backdropFilter: 'blur(8px)',
              }}>
                {cfg.model}
              </div>
            )}
          </div>
        </div>
        {args.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: cfg.color, display: 'flex', alignItems: 'center', gap: 4,
              fontSize: '0.75rem', fontWeight: 600,
            }}
          >
            {expanded ? 'Less' : 'More'}
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>

      {/* Strongest point */}
      {data?.strongest_point && (
        <div style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: 10,
          padding: '10px 14px',
          marginBottom: 10,
          fontSize: '0.875rem',
          borderLeft: `3px solid ${cfg.color}`,
        }}>
          <span style={{ fontWeight: 600, color: cfg.color, fontSize: '0.75rem' }}>STRONGEST POINT: </span>
          {data.strongest_point}
        </div>
      )}

      <AnimatePresence>
        {expanded && args.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {args.map((arg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.08 }}
                  style={{
                    fontSize: '0.8rem',
                    padding: '8px 12px',
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 8,
                    lineHeight: 1.5,
                    opacity: 0.85,
                  }}
                >
                  <TypewriterText text={arg} delay={i * 140} />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
