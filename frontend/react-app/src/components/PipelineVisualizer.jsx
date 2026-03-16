import { motion } from 'framer-motion';

const steps = [
  { id: 0, icon: '🔍', label: 'Claim Analysis', desc: 'Classifying claim type' },
  { id: 1, icon: '📚', label: 'Evidence Search', desc: 'Retrieving articles' },
  { id: 2, icon: '⚔️', label: 'Agent Debate', desc: 'Prosecutor vs Defender' },
  { id: 3, icon: '⚖️', label: 'Judge Review', desc: 'Weighing arguments' },
  { id: 4, icon: '✅', label: 'Verdict Ready', desc: 'Analysis complete' },
];

export default function PipelineVisualizer({ activeStep = 0 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 0 }}>
      {steps.map((step, index) => {
        const isActive = activeStep === step.id;
        const isComplete = activeStep > step.id;
        const isPending = activeStep < step.id;

        return (
          <div key={step.id} style={{ display: 'flex', alignItems: 'center' }}>
            <motion.div
              className={`pipeline-step ${isActive ? 'active' : isComplete ? 'complete' : 'pending'}`}
              animate={isActive ? { boxShadow: ['0 0 0 rgba(99,102,241,0.0)', '0 0 22px rgba(99,102,241,0.55)', '0 0 0 rgba(99,102,241,0.0)'] } : {}}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={{
                width: 132,
                minHeight: 116,
                borderRadius: 14,
                border: isComplete
                  ? '1px solid rgba(16,185,129,0.65)'
                  : isActive
                  ? '1px solid rgba(99,102,241,0.7)'
                  : '1px solid rgba(148,163,184,0.35)',
                background: isComplete
                  ? 'rgba(16,185,129,0.1)'
                  : isActive
                  ? 'rgba(99,102,241,0.16)'
                  : 'rgba(148,163,184,0.08)',
                padding: '12px 10px',
                opacity: isPending ? 0.4 : 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                position: 'relative',
              }}
            >
              {isComplete && (
                <motion.span
                  initial={{ opacity: 0, scale: 0, rotate: -45 }}
                  animate={{ opacity: 1, scale: 1, rotate: 0 }}
                  transition={{ duration: 0.35 }}
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    fontSize: 12,
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    background: 'rgba(16,185,129,0.9)',
                    color: '#052e16',
                    display: 'grid',
                    placeItems: 'center',
                    fontWeight: 800,
                    animation: 'stepComplete 0.45s ease',
                  }}
                >
                  ✓
                </motion.span>
              )}

              <motion.div
                animate={isActive ? { scale: [1, 1.08, 1] } : isComplete ? { scale: 1.05 } : { scale: 1 }}
                transition={{ duration: 1, repeat: Infinity }}
                style={{ fontSize: 48, lineHeight: 1, marginBottom: 8 }}
              >
                {step.icon}
              </motion.div>

              <div className="pipeline-label" style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0' }}>
                {step.label}
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, lineHeight: 1.25 }}>
                {step.desc}
              </div>
            </motion.div>

            {index < steps.length - 1 && (
              <div
                style={{
                  width: 36,
                  height: 3,
                  margin: '0 5px',
                  borderRadius: 99,
                  border: isPending ? '1px dashed rgba(148,163,184,0.45)' : 'none',
                  background:
                    isComplete
                      ? 'linear-gradient(90deg, rgba(16,185,129,0.2), rgba(16,185,129,1), rgba(16,185,129,0.2))'
                      : isActive
                      ? 'rgba(99,102,241,0.9)'
                      : 'rgba(148,163,184,0.32)',
                  backgroundSize: isComplete ? '200% 200%' : 'auto',
                }}
              >
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: isComplete ? 1 : 0 }}
                  transition={{ duration: 0.35, ease: 'easeOut' }}
                  style={{
                    width: '100%',
                    height: '100%',
                    transformOrigin: 'left center',
                    background: 'linear-gradient(90deg, rgba(16,185,129,0.25), rgba(16,185,129,1), rgba(16,185,129,0.25))',
                    borderRadius: 99,
                    animation: isComplete ? 'lineGrow 0.35s ease forwards' : 'none',
                  }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
