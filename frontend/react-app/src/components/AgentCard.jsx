import { motion } from "framer-motion";

function AgentCard({ role, result, evidence = [] }) {
  const strength = result?.prosecution_strength || result?.defense_strength || "none";

  const sourceLinks = (evidence || [])
    .filter((item) => item?.source_url)
    .map((item) => ({
      title: item?.title || item?.source || "Source",
      url: item?.source_url,
    }));

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
          {role === "prosecutor" ? "🛡️ Prosecutor" : "⚖️ Defender"}
        </motion.h3>
        <motion.span 
          className={`strength strength-${strength}`}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 10, delay: 0.2 }}
        >
          {strength}
        </motion.span>
      </div>

      <ul className="bullet-list">
        {(result?.arguments || []).map((arg, idx) => (
          <motion.li 
            key={`${role}-arg-${idx}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 + (idx * 0.1) }}
          >
            {arg}
          </motion.li>
        ))}
      </ul>

      <motion.div 
        className="strongest-point"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        whileHover={{ scale: 1.02 }}
      >
        <strong>Strongest point:</strong> {result?.strongest_point || "N/A"}
      </motion.div>

      {sourceLinks.length > 0 && (
        <div className="agent-sources">
          <strong>Related sources:</strong>
          <div className="agent-source-links">
            {sourceLinks.map((link, index) => (
              <a key={`${role}-source-${index}`} href={link.url} target="_blank" rel="noreferrer">
                {index + 1}. {link.title}
              </a>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default AgentCard;
