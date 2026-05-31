import { motion } from "framer-motion";

function EvidenceCard({ article }) {
  const title = article?.title || "Untitled source";
  const source = article?.source || "Unknown source";
  const content = article?.content || "No summary available.";
  const sourceUrl = article?.url || article?.source_url || "#";
  const credibilityValue = Number(article?.credibility ?? article?.credibility_score ?? 0.5);
  const credibilityScore = credibilityValue > 1 ? credibilityValue / 100 : credibilityValue;
  const evidenceSource = article?.evidence_source || article?.source || "";
  const stance = String(article?.stance || "").toUpperCase();

  // Source quality badge
  const getSourceBadge = (score) => {
    if (score >= 0.90)
      return {
        label: "✅ Verified Source",
        bg: "#dcfce7",
        color: "#166534",
      };
    if (score >= 0.75)
      return {
        label: "📰 News Source",
        bg: "#dbeafe",
        color: "#1e40af",
      };
    return {
      label: "⚠️ Unverified Source",
      bg: "#fef3c7",
      color: "#92400e",
    };
  };

  // Evidence source tag
  const getSourceTag = (source) => {
    const tags = {
      serpapi: "🔍 Web Search",
      newsapi: "📰 NewsAPI",
      rss: "📡 RSS Live",
      knowledge_base: "✅ Verified Fact",
      curated_fact_base: "✅ Verified Fact",
    };
    return tags[source] || "📄 Source";
  };

  const getStanceBadge = (value) => {
    if (value === "SUPPORTS")
      return {
        label: "Supports claim",
        bg: "#dcfce7",
        color: "#166534",
      };
    if (value === "CONTRADICTS")
      return {
        label: "Contradicts claim",
        bg: "#fee2e2",
        color: "#991b1b",
      };
    return null;
  };

  const sourceBadge = getSourceBadge(credibilityScore);
  const stanceBadge = getStanceBadge(stance);

  return (
    <motion.div
      className="card evidence-card interactive-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      whileHover={{ 
        scale: 1.01,
        boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)",
        borderColor: "var(--accent)"
      }}
    >
      <motion.h3 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        transition={{ delay: 0.1 }}
      >
        {title}
      </motion.h3>
      <div className="meta-line">
        <motion.span whileHover={{ scale: 1.05 }}>
          {article?.source_logo || "🌐"} {source}
        </motion.span>
        <motion.span 
          style={{ 
            color: credibilityScore > 0.7 ? "var(--true)" : 
                   credibilityScore > 0.4 ? "var(--misleading)" : "var(--false)",
            fontWeight: "bold"
          }}
        >
          Credibility: {(credibilityScore * 100).toFixed(0)}%
        </motion.span>
      </div>
      <div className="meta-line" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
        <span
          style={{
            background: sourceBadge.bg,
            color: sourceBadge.color,
            padding: "0.2rem 0.5rem",
            borderRadius: "999px",
            fontWeight: 600,
            fontSize: "0.8rem",
          }}
        >
          {sourceBadge.label}
        </span>
        <span
          style={{
            background: "rgba(255,255,255,0.1)",
            padding: "0.2rem 0.5rem",
            borderRadius: "999px",
            fontSize: "0.8rem",
          }}
        >
          {getSourceTag(evidenceSource)}
        </span>
        {stanceBadge && (
          <span
            style={{
              background: stanceBadge.bg,
              color: stanceBadge.color,
              padding: "0.2rem 0.5rem",
              borderRadius: "999px",
              fontWeight: 600,
              fontSize: "0.8rem",
            }}
          >
            {stanceBadge.label}
          </span>
        )}
      </div>
      <motion.p 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        transition={{ delay: 0.2 }}
      >
        {content}
      </motion.p>
      <motion.a 
        href={sourceUrl} 
        target="_blank" 
        rel="noreferrer"
        onClick={(e) => {
          if (!sourceUrl || sourceUrl === "#") e.preventDefault();
        }}
        whileHover={{ x: 5, color: "var(--accent)" }}
        style={{ display: "inline-block", marginTop: "0.5rem" }}
      >
        Open source →
      </motion.a>
    </motion.div>
  );
}

export default EvidenceCard;
