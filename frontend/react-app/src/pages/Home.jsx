import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useLocation } from "react-router-dom";

import AgentCard from "../components/AgentCard";
import ConfidenceGauge from "../components/ConfidenceGauge";
import EvidenceCard from "../components/EvidenceCard";
import VerdictBadge from "../components/VerdictBadge";
import { useVoiceInput, useVoiceOutput } from "../hooks/useVoice";
import { getHistory, getHistoryDetails, verifyClaim } from "../services/api";

const STEPS = [
  "Claim Testing",
  "Evidence Retrieval",
  "Prosecutor Analysis",
  "Defender Analysis",
  "Agent Comparison",
  "Judge Verdict",
];

const STEP_ICONS = ["🧪", "🔎", "🛡️", "⚖️", "🧭", "✅"];
const STEP_MESSAGES = [
  "Testing claim…",
  "Passing claim to evidence retrieval…",
  "Passing evidence to prosecutor agent…",
  "Passing evidence to defender agent…",
  "Comparing both agents…",
  "Judge agent is generating final output…",
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.05 },
  },
  exit: { opacity: 0, x: -20, transition: { duration: 0.2 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 40, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 280, damping: 22 },
  },
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const getDisagreementLabel = (score) => {
  if (score > 0.7) return "High";
  if (score > 0.4) return "Medium";
  return "Low";
};

const getContentiousness = (score) => {
  if (score >= 0.66) return { label: "High", color: "#ef4444" };
  if (score >= 0.33) return { label: "Medium", color: "#f59e0b" };
  return { label: "Low", color: "#22c55e" };
};

function Home() {
  const location = useLocation();
  const [claim, setClaim] = useState("");
  const [result, setResult] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pipelineMessage, setPipelineMessage] = useState("");
  const [recentClaims, setRecentClaims] = useState([]);
  const handledNavClaimRef = useRef("");

  const handleTranscript = useCallback((text) => {
    setClaim(text);
  }, []);

  const {
    isListening,
    isSupported: voiceInputSupported,
    startListening,
    stopListening,
  } = useVoiceInput(handleTranscript);

  const { isSpeaking, speak, stopSpeaking } = useVoiceOutput();

  const readResultCache = () => {
    try {
      return JSON.parse(localStorage.getItem("veritas-results-cache") || "{}");
    } catch {
      return {};
    }
  };

  const persistResult = (claimText, payload) => {
    if (!claimText || !payload) return;
    const existing = readResultCache();
    const next = {
      ...existing,
      [claimText]: {
        ...payload,
        __savedAt: Date.now(),
      },
    };
    localStorage.setItem("veritas-results-cache", JSON.stringify(next));
    localStorage.setItem("veritas-last-claim", claimText);
  };

  const replayClaim = async (claimText) => {
    if (!claimText) return;
    setClaim(claimText);
    setError("");

    const cache = readResultCache();
    if (cache[claimText]) {
      setResult(cache[claimText]);
      setActiveStep(STEPS.length);
      setPipelineMessage("Loaded cached verification. Refreshing with latest evidence…");
      setLoading(true);
      try {
        const fresh = await verifyClaim(claimText);
        setResult(fresh);
        persistResult(claimText, fresh);
        setPipelineMessage("Updated with latest analysis.");
      } catch {
        setPipelineMessage("Using cached verification (refresh failed).");
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    setActiveStep(1);
    setPipelineMessage(STEP_MESSAGES[0]);
    try {
      const data = await verifyClaim(claimText);
      setResult(data);
      setActiveStep(STEPS.length);
      setPipelineMessage("Final verdict generated.");
      persistResult(claimText, data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Failed to load verification result");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const historyId = location.state?.historyId;
    if (historyId && handledNavClaimRef.current !== `history-${historyId}`) {
      handledNavClaimRef.current = `history-${historyId}`;
      setLoading(true);
      setError("");
      getHistoryDetails(historyId)
        .then((details) => {
          setClaim(details?.claim || location.state?.claim || "");
          setResult(details || null);
          setActiveStep(STEPS.length);
          setPipelineMessage("Loaded selected history snapshot.");
          if (details?.claim) {
            persistResult(details.claim, details);
          }
        })
        .catch((err) => {
          setError(err?.response?.data?.detail || "Failed to load selected history details");
        })
        .finally(() => setLoading(false));
      return;
    }

    const navClaim = location.state?.claim;
    if (navClaim && handledNavClaimRef.current !== navClaim) {
      handledNavClaimRef.current = navClaim;
      replayClaim(navClaim);
      return;
    }
  }, [location.state]);

  useEffect(() => {
    getHistory()
      .then((rows) => {
        const unique = [];
        const seen = new Set();
        for (const row of rows || []) {
          const txt = (row?.claim_text || "").trim();
          if (!txt || seen.has(txt)) continue;
          seen.add(txt);
          unique.push({ id: row.id, claim_text: txt });
          if (unique.length >= 5) break;
        }
        setRecentClaims(unique);
      })
      .catch(() => setRecentClaims([]));
  }, [result]);

  useEffect(() => {
    if (!result || !result.verdict) return;
    const verdictText =
      `Verdict: ${result.verdict}. ` +
      `Confidence: ${result.confidence} percent. ` +
      `${result.reasoning || ""}`;

    const timerId = setTimeout(() => speak(verdictText), 500);
    return () => clearTimeout(timerId);
  }, [result?.verdict, result?.confidence, speak]);

  const canSubmit = useMemo(() => claim.trim().length > 2 && !loading, [claim, loading]);
  const pipelineProgress = Math.min(100, (activeStep / STEPS.length) * 100);

  const handleVerify = async () => {
    if (!canSubmit) return;
    const claimText = claim.trim();

    setError("");

    const cache = readResultCache();
    if (cache[claimText]) {
      setResult(cache[claimText]);
      setActiveStep(STEPS.length);
      setPipelineMessage("Loaded cached result instantly. Refreshing with latest evidence…");
      setLoading(true);
      try {
        const fresh = await verifyClaim(claimText);
        setResult(fresh);
        persistResult(claimText, fresh);
        setPipelineMessage("Updated with latest analysis.");
      } catch {
        setPipelineMessage("Using cached result (refresh failed).");
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    setResult(null);
    setActiveStep(1);
    setPipelineMessage(STEP_MESSAGES[0]);

    let interval = null;
    try {
      const startedAt = Date.now();
      const minPipelineMs = 4300;

      interval = setInterval(() => {
        setActiveStep((prev) => {
          const next = Math.min(prev + 1, STEPS.length - 1);
          setPipelineMessage(STEP_MESSAGES[next - 1] || "Processing…");
          return next;
        });
      }, 800);

      const data = await verifyClaim(claimText);

      const elapsed = Date.now() - startedAt;
      if (elapsed < minPipelineMs) {
        await sleep(minPipelineMs - elapsed);
      }

      clearInterval(interval);
      setActiveStep(STEPS.length);
      setPipelineMessage("Judge verdict generated.");
      setResult(data);
      persistResult(claimText, data);
    } catch (err) {
      if (interval) clearInterval(interval);
      setError(err?.response?.data?.detail || err.message || "Failed to verify claim");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setClaim("");
    setResult(null);
    setError("");
    setLoading(false);
    setActiveStep(0);
    setPipelineMessage("");
  };

  return (
    <motion.div className="page" variants={containerVariants} initial="hidden" animate="visible" exit="exit">
      <motion.div className="hero card" variants={itemVariants}>
        <motion.textarea
          className="claim-input"
          placeholder="Enter a claim to verify..."
          value={claim}
          onChange={(event) => setClaim(event.target.value)}
          whileFocus={{ scale: 1.01, boxShadow: "inset 0 0 0 2px var(--accent)" }}
          transition={{ type: "spring", stiffness: 300 }}
        />
        <div className="hero-actions">
          {voiceInputSupported && (
            <button
              type="button"
              onClick={isListening ? stopListening : startListening}
              title={
                isListening
                  ? "Click to stop recording"
                  : "Click to speak your claim"
              }
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "10px 20px",
                marginRight: "8px",
                borderRadius: "8px",
                border: isListening
                  ? "2px solid #ef4444"
                  : "2px solid #d1d5db",
                background: isListening
                  ? "#fef2f2"
                  : "#ffffff",
                cursor: "pointer",
                fontSize: "14px",
                color: isListening ? "#dc2626" : "#374151",
                fontWeight: 600,
                transition: "all 0.2s",
                boxShadow: isListening
                  ? "0 0 0 3px rgba(239,68,68,0.2)"
                  : "none",
                animation: isListening
                  ? "micPulse 1.5s ease-in-out infinite"
                  : "none",
              }}
            >
              <span style={{ fontSize: "18px" }}>
                {isListening ? "🔴" : "🎤"}
              </span>
              {isListening ? "Listening..." : "Speak"}
            </button>
          )}
          <motion.button className="primary-btn verify-btn" onClick={handleVerify} disabled={!canSubmit} whileTap={canSubmit ? { scale: 0.95 } : {}}>
            {loading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                style={{ display: "inline-block", marginRight: "8px" }}
              >
                ⚙️
              </motion.div>
            ) : null}
            {loading ? "Processing..." : "Verify Now"}
          </motion.button>
          <motion.button className="secondary-btn" onClick={handleClear} whileTap={{ scale: 0.95 }}>
            Clear
          </motion.button>
        </div>

        {recentClaims.length > 0 && (
          <div className="recent-claims-wrap">
            <p className="recent-claims-title">Recent 5 claims:</p>
            <div className="recent-claims-list">
              {recentClaims.map((item) => (
                <button
                  key={item.id}
                  className="recent-claim-chip"
                  onClick={() => {
                    setClaim(item.claim_text);
                    replayClaim(item.claim_text);
                  }}
                >
                  {item.claim_text}
                </button>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      <motion.div className="card pipeline-card" variants={itemVariants}>
        <div className="pipeline-header-row">
          <h3>Pipeline Execution</h3>
          <span className="pipeline-progress-text">{Math.round(pipelineProgress)}% complete</span>
        </div>
        {(loading || pipelineMessage) && <p className="pipeline-live-status">{pipelineMessage || "Ready"}</p>}
        <div className="pipeline-progress-track">
          <motion.div
            className="pipeline-progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${pipelineProgress}%` }}
            transition={{ type: "spring", stiffness: 120, damping: 20 }}
          />
        </div>
        <div className="pipeline-grid">
          {STEPS.map((step, idx) => {
            const isActive = activeStep >= idx + 1;
            const isCurrent = activeStep === idx + 1;
            return (
              <motion.div
                key={step}
                className={`pipeline-step ${isActive ? "active" : ""}`}
                animate={{
                  opacity: isActive ? 1 : 0.4,
                  scale: isCurrent ? 1.08 : isActive ? 1.02 : 1,
                  borderColor: isCurrent ? "var(--accent)" : "transparent",
                  boxShadow: isCurrent ? "0 0 15px rgba(108, 99, 255, 0.3)" : "none",
                }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              >
                <div className="step-indicator">
                  {isActive ? (
                    <motion.span initial={{ scale: 0 }} animate={{ scale: isCurrent ? [1, 1.2, 1] : 1 }} transition={{ duration: 1.2, repeat: isCurrent ? Infinity : 0 }}>
                      {STEP_ICONS[idx]}
                    </motion.span>
                  ) : (
                    <span>{idx + 1}</span>
                  )}
                </div>
                <strong>{step}</strong>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      <AnimatePresence>
        {error && (
          <motion.div
            className="card error"
            initial={{ opacity: 0, height: 0, y: -20 }}
            animate={{ opacity: 1, height: "auto", y: 0 }}
            exit={{ opacity: 0, height: 0, scale: 0.9 }}
            transition={{ type: "spring" }}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {result && (
          <motion.div key="results-section" className="results-wrapper" variants={containerVariants} initial="hidden" animate="visible" exit="exit">
            <div className="two-col">
              <motion.div className="result-top card" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)", borderColor: "var(--accent)" }}>
                <div className="verdict-insights">
                  <VerdictBadge verdict={result.verdict} />
                  <p className="verdict-summary">{result?.verdict_insights?.summary || result.reasoning}</p>
                  <div className="verdict-counts">
                    <span className="insight-chip support-chip">Support: {result?.verdict_insights?.supporting_sources ?? 0}</span>
                    <span className="insight-chip contradict-chip">Contradict: {result?.verdict_insights?.contradicting_sources ?? 0}</span>
                    {result?.verdict_insights?.disagreement_score != null && (
                      <span className="insight-chip">
                        Contentiousness: {getDisagreementLabel(result.verdict_insights.disagreement_score)}
                      </span>
                    )}
                  </div>
                  {(result?.verdict_insights?.top_supporting || []).length > 0 && (
                    <div className="insight-links">
                      <strong>Top supporting source:</strong>
                      <a href={result.verdict_insights.top_supporting[0].url} target="_blank" rel="noreferrer">
                        {result.verdict_insights.top_supporting[0].title || result.verdict_insights.top_supporting[0].url}
                      </a>
                    </div>
                  )}
                  {(result?.verdict_insights?.top_contradicting || []).length > 0 && (
                    <div className="insight-links">
                      <strong>Top contradictory source:</strong>
                      <a href={result.verdict_insights.top_contradicting[0].url} target="_blank" rel="noreferrer">
                        {result.verdict_insights.top_contradicting[0].title || result.verdict_insights.top_contradicting[0].url}
                      </a>
                    </div>
                  )}
                  {result && result.verdict && (
                    <button
                      type="button"
                      onClick={
                        isSpeaking
                          ? stopSpeaking
                          : () =>
                              speak(
                                `Verdict: ${result.verdict}. ` +
                                  `Confidence ${result.confidence} percent. ` +
                                  `${result.reasoning || ""}`
                              )
                      }
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "8px 16px",
                        borderRadius: "8px",
                        border: "1.5px solid #d1d5db",
                        background: isSpeaking ? "#fef9c3" : "#f9fafb",
                        cursor: "pointer",
                        fontSize: "13px",
                        fontWeight: 500,
                        color: "#374151",
                        marginTop: "8px",
                      }}
                      title="Listen to verdict"
                    >
                      <span>{isSpeaking ? "🔇" : "🔊"}</span>
                      {isSpeaking ? "Stop Reading" : "Read Verdict"}
                    </button>
                  )}
                </div>
                <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.3, type: "spring" }}>
                  <ConfidenceGauge confidence={(Number(result.confidence) || 0) / 100} />
                  <div style={{ marginTop: "10px", fontSize: "0.9rem" }}>
                    Claim Contentiousness:{" "}
                    <span style={{ color: getContentiousness(result.disagreement_score ?? 0).color, fontWeight: 700 }}>
                      {getContentiousness(result.disagreement_score ?? 0).label}
                    </span>
                  </div>
                </motion.div>
              </motion.div>

              <motion.div className="card reasoning-card" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)", borderColor: "var(--accent)" }}>
                <h3>Reasoning</h3>
                {(result.reasoning_points || []).length > 0 ? (
                  <ul className="bullet-list">
                    {result.reasoning_points.map((point, idx) => (
                      <li key={`reasoning-point-${idx}`}>{point}</li>
                    ))}
                  </ul>
                ) : (
                  <p>{result.reasoning}</p>
                )}
              </motion.div>
            </div>

            {result.prosecutor && result.defender && (
              <motion.div data-aos="fade-up" data-aos-duration="1000" className="two-col agent-two-col" variants={containerVariants}>
                <motion.div className="agent-col" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)", borderColor: "var(--accent)" }}>
                  <AgentCard role="prosecutor" result={result.prosecutor} evidence={result.prosecutor_evidence || result.evidence || []} />
                </motion.div>
                <motion.div className="agent-col" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)", borderColor: "var(--accent)" }}>
                  <AgentCard role="defender" result={result.defender} evidence={result.defender_evidence || result.evidence || []} />
                </motion.div>
              </motion.div>
            )}

            <motion.div className="evidence-section" data-aos="fade-up" data-aos-duration="1200" variants={containerVariants}>
              <motion.h3 variants={itemVariants} style={{ marginBottom: "1rem" }}>
                Evidence Sources
              </motion.h3>
              <div className="evidence-grid">
                {(result.evidence || []).map((article, idx) => (
                  <motion.div key={article.id || article.title} variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)", borderColor: "var(--accent)" }}>
                    <EvidenceCard article={article} />
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default Home;
