import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download } from "lucide-react";
import { useLocation } from "react-router-dom";

import AgentCard from "../components/AgentCard";
import ConfidenceGauge from "../components/ConfidenceGauge";
import EvidenceCard from "../components/EvidenceCard";
import PipelineProgress from "../components/PipelineProgress";
import SkeletonCard from "../components/SkeletonCard";
import VerdictBadge from "../components/VerdictBadge";
import { useVoiceInput, useVoiceOutput } from "../hooks/useVoice";
import { exportPdf, getHistory, getHistoryDetails, verifyClaim } from "../services/api";

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

const sanitizeStages = (stages = {}) => {
  const allowed = new Set(["pending", "running", "completed", "failed"]);
  return {
    claim_analysis: allowed.has(stages?.claim_analysis) ? stages.claim_analysis : "pending",
    retrieval: allowed.has(stages?.retrieval) ? stages.retrieval : "pending",
    agent_reasoning: allowed.has(stages?.agent_reasoning) ? stages.agent_reasoning : "pending",
    verdict: allowed.has(stages?.verdict) ? stages.verdict : "pending",
  };
};

const normalizeVerificationResult = (payload) => {
  const safe = payload && typeof payload === "object" ? payload : {};
  const prosecutor = safe.prosecutor || safe.prosecutor_analysis || {};
  const defender = safe.defender || safe.defender_analysis || {};

  return {
    ...safe,
    success: Boolean(safe.success),
    claim: safe.claim || "",
    evidence: Array.isArray(safe.evidence) ? safe.evidence : [],
    prosecutor: {
      ...prosecutor,
      arguments: Array.isArray(prosecutor.arguments) ? prosecutor.arguments : [],
    },
    defender: {
      ...defender,
      arguments: Array.isArray(defender.arguments) ? defender.arguments : [],
    },
    prosecutor_analysis: safe.prosecutor_analysis || prosecutor,
    defender_analysis: safe.defender_analysis || defender,
    prosecutor_evidence: Array.isArray(safe.prosecutor_evidence) ? safe.prosecutor_evidence : [],
    defender_evidence: Array.isArray(safe.defender_evidence) ? safe.defender_evidence : [],
    verdict: safe.verdict || "INSUFFICIENT_DATA",
    reasoning: safe.reasoning || "No reasoning generated.",
    reasoning_points: Array.isArray(safe.reasoning_points) ? safe.reasoning_points : [],
    pipeline_status: safe.pipeline_status || (safe.success ? "completed" : "failed"),
    stages: sanitizeStages(safe.stages),
  };
};

/** Derive a pipeline message from backend stages */
function derivePipelineMessage(stages, pipelineWarning) {
  if (pipelineWarning) return pipelineWarning;
  if (!stages) return "";
  if (stages.verdict === "completed") return "Final verdict generated.";
  if (stages.agent_reasoning === "running") return "Agents are reasoning over evidence.";
  if (stages.retrieval === "running") return "Retrieving evidence from APIs.";
  if (stages.retrieval === "failed") return "Evidence retrieval failed; no relevant sources found.";
  if (stages.claim_analysis === "running") return "Analyzing claim.";
  return "";
}

function Home() {
  const location = useLocation();
  const [claim, setClaim] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pipelineMessage, setPipelineMessage] = useState("");
  const [recentClaims, setRecentClaims] = useState([]);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [, setPendingStages] = useState(null);
  const handledNavClaimRef = useRef("");
  const ttsEnabled = false;

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
      setPipelineMessage("Loaded cached verification. Refreshing with latest evidence…");
      setLoading(true);
      try {
        const fresh = normalizeVerificationResult(await verifyClaim(claimText));
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
    setPendingStages(null);
    setPipelineMessage("");
    try {
      const data = normalizeVerificationResult(await verifyClaim(claimText));
      setPipelineMessage(derivePipelineMessage(data.stages, data.pipeline_warning));
      setResult(data);
      setPendingStages(null);
      persistResult(claimText, data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Failed to load verification result");
      setPendingStages(null);
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
          setResult(details ? normalizeVerificationResult(details) : null);
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
    if (!ttsEnabled || !result || !result.verdict) return;
    const verdictText =
      `Verdict: ${result.verdict}. ` +
      `Confidence: ${result.confidence} percent. ` +
      `${result.reasoning || ""}`;

    const timerId = setTimeout(() => speak(verdictText), 500);
    return () => clearTimeout(timerId);
  }, [result?.verdict, result?.confidence, speak]);

  const canSubmit = useMemo(() => claim.trim().length > 2 && !loading, [claim, loading]);

  // Use backend stages only.
  const currentStages = result?.stages || {};
  const retrievalFailed = currentStages.retrieval === "failed";

  const handleVerify = async () => {
    if (!canSubmit) return;
    const claimText = claim.trim();

    setError("");

    const cache = readResultCache();
    if (cache[claimText]) {
      setResult(cache[claimText]);
      setPipelineMessage("Loaded cached result instantly. Refreshing with latest evidence…");
      setLoading(true);
      try {
        const fresh = normalizeVerificationResult(await verifyClaim(claimText));
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
    setPendingStages(null);
    setPipelineMessage("");

    try {
      const data = normalizeVerificationResult(await verifyClaim(claimText));
      setPipelineMessage(derivePipelineMessage(data.stages, data.pipeline_warning));
      setResult(data);
      setPendingStages(null);
      persistResult(claimText, data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Failed to verify claim");
      setPendingStages(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setClaim("");
    setResult(null);
    setError("");
    setLoading(false);
    setPdfLoading(false);
    setPipelineMessage("");
    setPendingStages(null);
  };

  const handleDownloadPdf = async () => {
    const verificationId = result?.history_id || result?.short_id;
    if (!verificationId || pdfLoading) return;

    setPdfLoading(true);
    try {
      const blob = await exportPdf(verificationId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      anchor.href = url;
      anchor.download = `verification_${timestamp}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Failed to download PDF");
    } finally {
      setPdfLoading(false);
    }
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

      {/* Pipeline Progress — uses backend stages, no fake timers */}
      {(loading || result) && (
        <motion.div className="card pipeline-card" variants={itemVariants}>
          <PipelineProgress stages={currentStages} pipelineMessage={pipelineMessage} />
        </motion.div>
      )}

      {/* Skeleton loading during pipeline execution */}
      {loading && !result && (
        <motion.div className="skeleton-section" variants={containerVariants} initial="hidden" animate="visible">
          <div className="two-col">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </motion.div>
      )}

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
            {/* Warning for failed retrieval or pipeline issues */}
            {(result.pipeline_warning || retrievalFailed) && (
              <motion.div className="card warning-box" variants={itemVariants}>
                  <h4 style={{ color: "#f59e0b", marginTop: 0 }}>{result.pipeline_warning || "Evidence retrieval failed"}</h4>
                {result.verdict === "INSUFFICIENT_DATA" && (
                  <p>No evidence was retrieved for this claim. Unable to provide a reliable verdict.</p>
                )}
                {result.review_flags && result.review_flags.includes("low_evidence_count") && (
                  <p>Very few evidence sources were found. Results may be unreliable.</p>
                )}
                {retrievalFailed && !result.pipeline_warning && (
                  <p>No relevant evidence sources could be retrieved. The verdict is based on limited information.</p>
                )}
              </motion.div>
            )}

            {/* Final Verdict + Reasoning: same row on desktop, stacked on mobile */}
            <div className="two-col verdict-reasoning-row">
              <motion.div className="result-top card" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16)", borderColor: "var(--accent)" }}>
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
                  <button
                    type="button"
                    className="secondary-btn pdf-download-btn"
                    onClick={handleDownloadPdf}
                    disabled={pdfLoading || !(result?.history_id || result?.short_id)}
                    title="Download PDF report"
                  >
                    <Download size={16} aria-hidden="true" />
                    {pdfLoading ? "Preparing PDF..." : "Download PDF"}
                  </button>
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
                  {ttsEnabled && result && result.verdict && (
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

              <motion.div className="card reasoning-card" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16)", borderColor: "var(--accent)" }}>
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

            {(result.prosecutor || result.prosecutor_analysis) && (result.defender || result.defender_analysis) && (
              <motion.div data-aos="fade-up" data-aos-duration="1000" className="two-col agent-two-col" variants={containerVariants}>
                <motion.div className="agent-col" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16)", borderColor: "var(--accent)" }}>
                  <AgentCard role="prosecutor" result={result.prosecutor || result.prosecutor_analysis} evidence={result.prosecutor_evidence || result.evidence || []} emptyMessage="No prosecutor analysis generated." />
                </motion.div>
                <motion.div className="agent-col" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16)", borderColor: "var(--accent)" }}>
                  <AgentCard role="defender" result={result.defender || result.defender_analysis} evidence={result.defender_evidence || result.evidence || []} emptyMessage="No defender analysis generated." />
                </motion.div>
              </motion.div>
            )}

            <motion.div className="evidence-section" data-aos="fade-up" data-aos-duration="1200" variants={containerVariants}>
              <motion.h3 variants={itemVariants} style={{ marginBottom: "1rem" }}>
                Evidence Sources
              </motion.h3>
              {(result.evidence || []).length === 0 ? (
                <motion.div className="no-evidence-box" variants={itemVariants}>
                  <p style={{ color: "#6b7280", fontStyle: "italic" }}>No evidence retrieved for this claim.</p>
                </motion.div>
              ) : (
                <div className="evidence-grid">
                  {(result.evidence || []).map((article, idx) => (
                    <motion.div key={article.id || article.title || idx} variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16)", borderColor: "var(--accent)" }}>
                      <EvidenceCard article={article} />
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default Home;
