import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import VerdictBadge from "../components/VerdictBadge";
import { getHistory } from "../services/api";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  },
  exit: { opacity: 0, scale: 0.95, transition: { duration: 0.2 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

function History() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [hoveredClaim, setHoveredClaim] = useState("");

  useEffect(() => {
    getHistory().then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <motion.div 
      className="page"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
    >
      <motion.div className="card" variants={itemVariants} whileHover={{ scale: 1.01, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)" }}>
        <h2>Claims History</h2>
        {!!hoveredClaim && (
          <motion.div
            className="history-hover-topic"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            Hovered topic: {hoveredClaim}
          </motion.div>
        )}
        <div style={{ overflowX: "auto" }}>
          <table className="history-table">
            <thead>
              <tr>
                <th>Claim</th>
                <th>Verdict</th>
                <th>Confidence</th>
                <th>Domain</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <motion.tr 
                  key={row.id}
                  className="history-row-clickable"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ backgroundColor: "rgba(108, 99, 255, 0.05)" }}
                  onHoverStart={() => setHoveredClaim(row.claim_text)}
                  onHoverEnd={() => setHoveredClaim("")}
                  onClick={() => navigate("/", { state: { historyId: row.id, claim: row.claim_text, fromHistory: true } })}
                >
                  <td title={row.claim_text}>{row.claim_text}</td>
                  <td>
                    <VerdictBadge verdict={row.verdict} />
                  </td>
                  <td>
                    <div className="confidence-bar-bg">
                      <motion.div 
                        className="confidence-bar-fill" 
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.round(row.confidence)}%` }}
                        transition={{ duration: 1, delay: 0.2 + (index * 0.05) }}
                      />
                    </div>
                    <span>{Math.round(row.confidence)}%</span>
                  </td>
                  <td>
                    <span className="domain-chip">{row.domain}</span>
                  </td>
                  <td>{new Date(row.timestamp).toLocaleString()}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default History;
