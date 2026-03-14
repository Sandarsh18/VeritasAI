import { motion } from 'framer-motion';
import { Search, Scale, Shield, Gavel, CheckCircle } from 'lucide-react';

const STEPS = [
  { id: 0, label: 'Evidence\nRetrieval', icon: Search, color: '#6366f1', model: 'FAISS + RAG' },
  { id: 1, label: 'Prosecutor\nAnalysis', icon: Scale, color: '#ef4444', model: 'Mistral 7B' },
  { id: 2, label: 'Defender\nAnalysis', icon: Shield, color: '#10b981', model: 'Phi-3 Mini' },
  { id: 3, label: 'Judge\nDeliberation', icon: Gavel, color: '#8b5cf6', model: 'LLaMA 3' },
  { id: 4, label: 'Final\nVerdict', icon: CheckCircle, color: '#f59e0b', model: '' },
];

export default function PipelineVisualizer({ activeStep }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 0,
      flexWrap: 'wrap',
      padding: '1rem 0',
    }}>
      {STEPS.map((step, i) => {
        const Icon = step.icon;
        const isActive = activeStep === step.id;
        const isDone = activeStep > step.id;
        const isPending = activeStep < step.id;

        return (
          <div key={step.id} style={{ display: 'flex', alignItems: 'center' }}>
            <motion.div
              animate={isActive ? {
                boxShadow: [`0 0 0px ${step.color}`, `0 0 25px ${step.color}`, `0 0 0px ${step.color}`],
              } : {}}
              transition={{ duration: 1.2, repeat: Infinity }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                padding: '12px 16px',
                borderRadius: 16,
                background: isActive ? `${step.color}22` : isDone ? 'rgba(255,255,255,0.08)' : 'transparent',
                border: `1px solid ${isActive ? step.color : isDone ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.06)'}`,
                opacity: isPending ? 0.4 : 1,
                transition: 'all 0.4s ease',
                minWidth: 80,
              }}
            >
              <motion.div
                animate={isActive ? { scale: [1, 1.15, 1] } : {}}
                transition={{ duration: 0.8, repeat: Infinity }}
                style={{ color: isDone || isActive ? step.color : 'rgba(255,255,255,0.4)' }}
              >
                <Icon size={22} />
              </motion.div>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: isActive ? step.color : isDone ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.4)',
                textAlign: 'center',
                whiteSpace: 'pre-line',
                lineHeight: 1.3,
              }}>
                {step.label}
              </span>
              {step.model ? (
                <span style={{
                  fontSize: '0.55rem',
                  fontWeight: 700,
                  color: isActive ? step.color : 'rgba(255,255,255,0.3)',
                  background: isActive ? `${step.color}22` : 'rgba(255,255,255,0.05)',
                  border: `1px solid ${isActive ? step.color + '44' : 'rgba(255,255,255,0.08)'}`,
                  borderRadius: 10,
                  padding: '1px 5px',
                  textAlign: 'center',
                }}>
                  {step.model}
                </span>
              ) : null}
            </motion.div>

            {i < STEPS.length - 1 && (
              <motion.div
                style={{
                  width: 32,
                  height: 2,
                  background: isDone ? 'linear-gradient(90deg, rgba(255,255,255,0.3), rgba(255,255,255,0.1))' : 'rgba(255,255,255,0.08)',
                  margin: '0 4px',
                  marginBottom: 24,
                  transition: 'background 0.5s ease',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
