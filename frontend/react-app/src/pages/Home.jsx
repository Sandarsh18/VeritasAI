import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Confetti from 'react-confetti';
import { Search, Zap, AlertCircle, Share2, Bookmark } from 'lucide-react';
import toast from 'react-hot-toast';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { bookmarkClaim, shareClaim, submitFeedback, suggestClaim, verifyClaim } from '../services/api';
import PipelineVisualizer from '../components/PipelineVisualizer';
import VerdictBadge from '../components/VerdictBadge';
import ConfidenceMeter from '../components/ConfidenceMeter';
import AgentCard from '../components/AgentCard';
import EvidenceCard from '../components/EvidenceCard';
import MisinformationTracker from '../components/MisinformationTracker';
import { TwitterShareButton, WhatsappShareButton, TwitterIcon, WhatsappIcon } from 'react-share';

const SAMPLE_CLAIMS = [
  'COVID vaccines cause infertility',
  '5G towers spread coronavirus',
  'Drinking bleach cures COVID',
];

const STEP_LABELS = ['Claim Analysis', 'Evidence Search', 'Agent Debate', 'Judge Review', 'Verdict Ready'];

const BANNER_STYLES = {
  info: {
    background: 'rgba(59,130,246,0.12)',
    border: '1px solid rgba(59,130,246,0.28)',
    color: '#bfdbfe',
  },
  warning: {
    background: 'rgba(245,158,11,0.12)',
    border: '1px solid rgba(245,158,11,0.28)',
    color: '#fde68a',
  },
};

function ResultBanner({ variant, title, message }) {
  const style = BANNER_STYLES[variant] || BANNER_STYLES.info;
  return (
    <div style={{ ...style, borderRadius: 14, padding: '14px 16px', textAlign: 'left', maxWidth: 640, margin: '0 auto 1rem' }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{message}</div>
    </div>
  );
}

export default function Home() {
  const { isLoading, setIsLoading, activeStep, setActiveStep, result, setResult } = useApp();
  const { user, isAuthenticated } = useAuth();
  const [claim, setClaim] = useState('');
  const [error, setError] = useState('');
  const [rating, setRating] = useState(0);
  const [suggestion, setSuggestion] = useState(null);

  const handleVerify = useCallback(async (claimText) => {
    const text = (claimText || claim).trim();
    if (!text || text.length < 10) {
      setError('Please enter a claim of at least 10 characters.');
      return;
    }
    setError('');
    setResult(null);
    setIsLoading(true);
    setActiveStep(0);

    const stepInterval = setInterval(() => {
      setActiveStep(prev => {
        if (prev >= 3) { clearInterval(stepInterval); return prev; }
        return prev + 1;
      });
    }, 5000);

    try {
      const data = await verifyClaim(text);
      clearInterval(stepInterval);
      setActiveStep(4);
      setResult(data);
      if (isAuthenticated) {
        localStorage.setItem('veritasai_first_login_done', '1');
      }
      toast.success('Verification complete!');
    } catch (err) {
      clearInterval(stepInterval);
      setActiveStep(-1);
      const msg = err?.response?.data?.detail || err.message || 'Verification failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  }, [claim, setIsLoading, setActiveStep, setResult]);

  const handleClaimBlur = useCallback(async () => {
    const text = claim.trim();
    if (!text || text.length < 8) {
      setSuggestion(null);
      return;
    }

    try {
      const data = await suggestClaim(text);
      if (data?.type && data.type !== 'factual_claim' && data?.suggestion && data.suggestion.toLowerCase() !== text.toLowerCase()) {
        setSuggestion(data);
      } else {
        setSuggestion(null);
      }
    } catch {
      setSuggestion(null);
    }
  }, [claim]);

  // Ctrl+Enter shortcut
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleVerify();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleVerify]);

  return (
    <main className="home-main" style={{ maxWidth: 1280, width: '100%', margin: '0 auto', padding: '2rem 1.5rem 4rem' }}>
      {result?.verdict === 'TRUE' && <Confetti recycle={false} numberOfPieces={160} />}
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ textAlign: 'center', marginBottom: '2.5rem' }}
      >
        <motion.div
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 3, repeat: Infinity }}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: 'rgba(99,102,241,0.12)',
            border: '1px solid rgba(99,102,241,0.25)',
            borderRadius: 100, padding: '6px 16px',
            fontSize: '0.75rem', fontWeight: 600, color: '#a5b4fc',
            marginBottom: '1rem',
          }}
        >
          <Zap size={13} /> Powered by Multi-Agent AI + RAG + Knowledge Graphs
        </motion.div>
        <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)', marginBottom: '0.75rem' }}>
          <span style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>Fake News</span>{' '}
          Detector
        </h1>
        <p style={{ opacity: 0.6, fontSize: '1.05rem', maxWidth: 520, margin: '0 auto' }}>
          Submit any news claim and our AI agents will debate, analyze and deliver a verdict
        </p>
        {isAuthenticated ? (
          <p style={{ marginTop: 10, opacity: 0.85 }}>Welcome back, {user?.full_name?.split(' ')[0] || user?.username}! 👋 <span style={{ marginLeft: 10, fontSize: '0.9rem', opacity: 0.8 }}>Claims verified: {user?.total_claims || 0}</span></p>
        ) : (
          <p style={{ marginTop: 10, opacity: 0.75 }}>Sign in to save your history</p>
        )}
      </motion.div>

      {/* Input card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass"
        style={{ padding: '1.5rem', marginBottom: '1.5rem' }}
      >
        <textarea
          value={claim}
          onChange={e => { setClaim(e.target.value); setError(''); setSuggestion(null); }}
          placeholder={"Enter a specific factual claim...\ne.g. 'Vaccines cause autism' or\n'5G towers spread coronavirus'"}
          disabled={isLoading}
          style={{
            width: '100%', minHeight: 110, resize: 'vertical',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12, padding: '1rem',
            fontSize: '1rem', color: 'inherit', outline: 'none',
            fontFamily: 'inherit', lineHeight: 1.6,
            transition: 'border-color 0.2s',
            boxSizing: 'border-box',
          }}
          onFocus={e => e.target.style.borderColor = 'rgba(99,102,241,0.5)'}
          onBlur={(e) => {
            e.target.style.borderColor = 'rgba(255,255,255,0.1)';
            handleClaimBlur();
          }}
        />

        {suggestion?.suggestion && (
          <div style={{
            marginTop: 12,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            alignItems: 'center',
            background: 'rgba(59,130,246,0.12)',
            border: '1px solid rgba(59,130,246,0.24)',
            borderRadius: 999,
            padding: '10px 14px',
            fontSize: '0.85rem',
          }}>
            <span style={{ color: '#bfdbfe' }}>💡 Did you mean: '{suggestion.suggestion}'?</span>
            <button
              onClick={() => {
                setClaim(suggestion.suggestion);
                setSuggestion(null);
              }}
              style={{
                border: 'none',
                borderRadius: 999,
                padding: '6px 12px',
                cursor: 'pointer',
                background: 'rgba(255,255,255,0.12)',
                color: 'inherit',
                fontWeight: 600,
              }}
            >
              Use this →
            </button>
          </div>
        )}

        {/* Sample claims */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '12px 0' }}>
          <span style={{ fontSize: '0.75rem', opacity: 0.5, alignSelf: 'center' }}>Try:</span>
          {SAMPLE_CLAIMS.map(sample => (
            <button
              key={sample}
              onClick={() => { setClaim(sample); setError(''); }}
              style={{
                background: 'rgba(99,102,241,0.1)',
                border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: 20, padding: '4px 12px',
                fontSize: '0.75rem', color: '#a5b4fc',
                cursor: 'pointer', fontFamily: 'inherit',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => e.target.style.background = 'rgba(99,102,241,0.2)'}
              onMouseLeave={e => e.target.style.background = 'rgba(99,102,241,0.1)'}
            >
              {sample}
            </button>
          ))}
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 10, padding: '10px 14px', color: '#fca5a5',
              fontSize: '0.85rem', marginBottom: 12,
            }}
          >
            <AlertCircle size={16} /> {error}
          </motion.div>
        )}

        <motion.button
          whileHover={{ scale: 1.02, boxShadow: '0 0 30px rgba(99,102,241,0.5)' }}
          whileTap={{ scale: 0.97 }}
          onClick={() => handleVerify()}
          disabled={isLoading || !claim.trim()}
          style={{
            width: '100%', padding: '14px',
            background: isLoading || !claim.trim()
              ? 'rgba(99,102,241,0.3)'
              : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            border: 'none', borderRadius: 12,
            color: '#fff', fontWeight: 700, fontSize: '1rem',
            cursor: isLoading || !claim.trim() ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit', display: 'flex', alignItems: 'center',
            justifyContent: 'center', gap: 8,
            transition: 'all 0.2s',
          }}
        >
          {isLoading ? (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%' }}
              />
              Analyzing...
            </>
          ) : (
            <><Search size={18} /> Verify Claim <span style={{ opacity: 0.6, fontSize: '0.8rem', fontWeight: 400 }}>(Ctrl+Enter)</span></>
          )}
        </motion.button>
      </motion.div>

      {/* Pipeline visualizer */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass"
            style={{ padding: '1rem', marginBottom: '1.5rem', overflow: 'hidden' }}
          >
            <div style={{ fontSize: '0.75rem', fontWeight: 600, opacity: 0.5, marginBottom: 8, textAlign: 'center' }}>
              PIPELINE STATUS
            </div>
            <PipelineVisualizer activeStep={activeStep} />
            <div style={{ textAlign: 'center', fontSize: '0.85rem', opacity: 0.6, marginTop: 8 }}>
              {activeStep >= 0 && activeStep < STEP_LABELS.length ? STEP_LABELS[activeStep] + '...' : ''}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
          >
            {/* Verdict */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass"
              style={{ padding: '2rem', textAlign: 'center', ...(result.verdict === 'FALSE' ? { boxShadow: '0 0 25px rgba(239,68,68,0.45)' } : result.verdict === 'MISLEADING' ? { boxShadow: '0 0 25px rgba(245,158,11,0.45)' } : {}) }}
            >
              {result.claim_type === 'opinion' && (
                <ResultBanner
                  variant="info"
                  title="💡 Opinion Detected"
                  message="This looks like a subjective opinion rather than a fact-checkable claim. Try rewriting it as a measurable statement such as 'RVCE is ranked #1 in Karnataka by NIRF' instead."
                />
              )}
              {result.claim_type === 'question' && (
                <ResultBanner
                  variant="info"
                  title="💡 Question Detected"
                  message="Try rephrasing this as a statement. Instead of 'Is X true?' write 'X is true' and then verify that claim."
                />
              )}
              {result.pipeline_note === 'Insufficient evidence' && (
                <ResultBanner
                  variant="warning"
                  title="⚠️ Limited Evidence"
                  message="No relevant articles were found in the current database for this specific claim. The verdict is based on limited data."
                />
              )}
              <div style={{ marginBottom: '1.5rem' }}>
                <VerdictBadge verdict={result.verdict} size="large" />
              </div>
              <ConfidenceMeter confidence={result.confidence} verdict={result.verdict} />
              {result.reasoning && (
                <p style={{
                  color: '#e2e8f0',
                  fontSize: '1rem',
                  lineHeight: '1.7',
                  textAlign: 'center',
                  padding: '0 20px',
                  marginTop: '1rem',
                }}>
                  {result.reasoning}
                </p>
              )}
              {result.key_evidence?.length > 0 && (
                <div style={{ marginTop: '1rem', textAlign: 'left', maxWidth: 600, margin: '1rem auto 0' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.8rem', opacity: 0.5, marginBottom: 8 }}>KEY EVIDENCE</div>
                  {result.key_evidence.map((ev, i) => (
                    <div key={i} style={{
                      display: 'flex', gap: 8, alignItems: 'flex-start',
                      fontSize: '0.85rem', marginBottom: 6, opacity: 0.8,
                    }}>
                      <span style={{ color: '#6366f1', fontWeight: 700, marginTop: 1 }}>•</span>
                      {ev}
                    </div>
                  ))}
                </div>
              )}
              {result.recommendation && (
                <div className="recommendation-box" style={{ maxWidth: 600, margin: '1rem auto 0' }}>
                  <span style={{color:'#a5b4fc', fontWeight:600}}>
                    Recommendation:{' '}
                  </span>
                  <span style={{color:'#e0e7ff'}}>
                    {result.recommendation}
                  </span>
                </div>
              )}

              <div style={{ marginTop: 14, display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
                <TwitterShareButton url={window.location.href} title={`VeritasAI verdict: ${result.verdict}`}><TwitterIcon size={34} round /></TwitterShareButton>
                <WhatsappShareButton url={window.location.href} title={`VeritasAI verdict: ${result.verdict}`}><WhatsappIcon size={34} round /></WhatsappShareButton>
                <button onClick={async () => { await navigator.clipboard.writeText(window.location.href); toast.success('Link copied'); }} style={{ border: '1px solid var(--border-dark)', borderRadius: 10, background: 'transparent', color: 'inherit', padding: '6px 10px', cursor: 'pointer' }}>🔗 Copy Link</button>
                {isAuthenticated && result?.id && (
                  <>
                    <button onClick={async () => { await bookmarkClaim(result.id); toast.success('Save to My Claims ✅'); }} style={{ border: '1px solid var(--border-dark)', borderRadius: 10, background: 'transparent', color: 'inherit', padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}><Bookmark size={14} /> Save to My Claims ✅</button>
                    <button onClick={async () => { const d = await shareClaim(result.id); await navigator.clipboard.writeText(`${window.location.origin}${d.share_url}`); toast.success('Share link copied'); }} style={{ border: '1px solid var(--border-dark)', borderRadius: 10, background: 'transparent', color: 'inherit', padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}><Share2 size={14} /> Share Result 🔗</button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      {[1, 2, 3, 4, 5].map((s) => (
                        <button
                          key={s}
                          onClick={async () => {
                            setRating(s);
                            await submitFeedback(result.id, s, '');
                            toast.success('Thanks for rating ⭐');
                          }}
                          style={{ border: 'none', background: 'transparent', color: rating >= s ? '#fbbf24' : '#94a3b8', cursor: 'pointer' }}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </motion.div>

            {['FALSE', 'MISLEADING'].includes(result.verdict) && result.misinformation_analysis && (
              <MisinformationTracker
                data={result.misinformation_analysis}
                claim={result.claim}
                verdict={result.verdict}
              />
            )}

            {/* Agent debate */}
            <div>
              <div style={{ fontWeight: 700, marginBottom: 12, fontSize: '1rem', opacity: 0.8 }}>Agent Debate</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                {result.prosecutor && <AgentCard type="prosecutor" data={result.prosecutor} delay={0.1} />}
                {result.defender   && <AgentCard type="defender"   data={result.defender}   delay={0.2} />}
              </div>
            </div>

            {/* Evidence */}
            {result.evidence?.length > 0 && (
              <div>
                <div style={{ fontWeight: 700, marginBottom: 12, fontSize: '1rem', opacity: 0.8 }}>
                  Retrieved Evidence ({result.evidence.length} articles)
                </div>
                {result.evidence_summary && (
                  <div
                    className="glass"
                    style={{
                      marginBottom: 12,
                      border: '1px solid rgba(99,102,241,0.25)',
                      padding: '12px 14px',
                      borderRadius: 12,
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: 5 }}>📰 Evidence Retrieved</div>
                    <div style={{ fontSize: '0.88rem', opacity: 0.84, lineHeight: 1.55 }}>
                      {result.evidence_summary.total || result.evidence.length} articles • {result.evidence_summary.realtime || 0} live • {result.evidence_summary.archive || 0} archived
                    </div>
                    <div style={{ fontSize: '0.84rem', opacity: 0.75, marginTop: 4 }}>
                      Sources: {(result.evidence_summary.sources_used || []).join(', ') || 'Unknown'}
                    </div>
                    <div style={{ fontSize: '0.84rem', opacity: 0.75, marginTop: 2 }}>
                      Avg credibility: {Math.round((result.evidence_summary.avg_credibility || 0) * 100)}% • Latest: {result.evidence_summary.freshest_date || 'Unknown'}
                    </div>
                  </div>
                )}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
                  {result.evidence.map((ev, i) => (
                    <EvidenceCard key={ev.id || i} article={ev} index={i} delay={i * 0.1} />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
