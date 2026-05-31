import { motion } from "framer-motion";

function AgentCard({ role, title, result, emptyMessage = "No agent reasoning available." }) {
  const roleLabel = role === "prosecutor" ? "⚔️ Prosecutor" : "🛡️ Defender";

  const entries = result?.arguments || [];

  return (
    <motion.div
      className="card interactive-card"
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 280, damping: 22 }}
      whileHover={{ 
        scale: 1.01,
        boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)",
        borderColor: "var(--accent)"
      }}
    >
      <div className="card-header">
        <motion.h3 
          initial={{ x: -10, opacity: 0 }} 
          animate={{ x: 0, opacity: 1 }} 
          transition={{ delay: 0.1 }}
        >
          {title || roleLabel}
        </motion.h3>
      </div>

      {entries.length > 0 ? (
        <ul className="bullet-list" style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem", listStyle: "none", padding: 0 }}>
          {entries.map((entry, idx) => {
            const isString = typeof entry === "string";
            const summary = isString ? entry : (entry.summary || entry.text || "");
            const source = isString ? "" : (entry.source || entry.title || "");
            const quote = isString ? "" : (entry.evidence_quote || "");

            return (
              <motion.li
                key={`arg-${idx}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + idx * 0.08 }}
                style={{ padding: "1rem", background: "var(--surface)", borderRadius: "8px", border: "1px solid var(--border)" }}
              >
                {source && (
                  <div style={{ fontWeight: 600, color: "var(--accent)", marginBottom: "0.25rem", fontSize: "0.9rem" }}>
                    Source: {source}
                  </div>
                )}
                <div style={{ marginBottom: "0.5rem" }}>
                  {summary}
                </div>
                {quote && (
                  <div style={{ 
                    fontStyle: "italic", 
                    fontSize: "0.85rem", 
                    color: "var(--muted-text)", 
                    paddingLeft: "0.75rem", 
                    borderLeft: "2px solid var(--border-strong)" 
                  }}>
                    "{quote}"
                  </div>
                )}
              </motion.li>
            );
          })}
        </ul>
      ) : (
        <p className="muted-text">{emptyMessage}</p>
      )}
    </motion.div>
  );
}

export default AgentCard;
