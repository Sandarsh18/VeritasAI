import { motion } from "framer-motion";

const STAGES = [
  { key: "claim_analysis", label: "Claim analyzed" },
  { key: "retrieval", label: "Evidence retrieved" },
  { key: "agent_reasoning", label: "Agents reasoning" },
  { key: "verdict", label: "Verdict ready" },
];

function StatusIcon({ status }) {
  // status is now "pending", "running", "completed", or "failed"
  if (status === "completed") return <span style={{ color: "#16a34a" }}>✅</span>;
  if (status === "running") return <span style={{ color: "#f59e0b" }}>⏳</span>;
  if (status === "failed") return <span style={{ color: "#ef4444" }}>⚠️</span>;
  return <span style={{ color: "#9ca3af" }}>●</span>;
}

export default function PipelineProgress({ stages = {}, pipelineMessage = "" }) {
  const totalStages = STAGES.length;
  
  // Count completed stages
  const completedStages = STAGES.reduce((count, entry) => {
    const status = stages?.[entry.key] || "pending";
    return count + (status === "completed" ? 1 : 0);
  }, 0);
  
  const progress = Math.min(100, Math.max(0, (completedStages / totalStages) * 100));
  
  // Find first incomplete stage (either running or pending)
  const firstIncomplete = STAGES.findIndex((entry) => {
    const status = stages?.[entry.key] || "pending";
    return status !== "completed";
  });

  return (
    <div className="pipeline-progress-shell">
      <div className="pipeline-track">
        <motion.div
          className="pipeline-track-fill"
          initial={false}
          animate={{ width: `${progress}%` }}
          transition={{ type: "spring", stiffness: 180, damping: 24 }}
        />
        {STAGES.map((s, idx) => {
          const status = stages?.[s.key] || "pending";
          
          // Determine display status for styling
          let displayStatus = "pending";
          if (status === "completed") {
            displayStatus = "done";
          } else if (status === "running" && idx === firstIncomplete) {
            displayStatus = "inflight";
          } else if (status === "failed") {
            displayStatus = "failed";
          }

          return (
            <motion.div
              key={s.key}
              className={`pipeline-step-card ${displayStatus}`}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08, type: "spring", stiffness: 220, damping: 20 }}
              whileHover={{ y: -2, scale: 1.01 }}
            >
              <div className="pipeline-step-icon">
                <StatusIcon status={status} />
              </div>
              <div className="pipeline-step-copy">
                <span className="pipeline-step-label">{s.label}</span>
                <span className="pipeline-step-state">
                  {status === "completed" ? "Completed" : status === "running" ? "Active now" : status === "failed" ? "Failed" : "Waiting"}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>
      {pipelineMessage && (
        <motion.div className="pipeline-message" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
          {pipelineMessage}
        </motion.div>
      )}
    </div>
  );
}
