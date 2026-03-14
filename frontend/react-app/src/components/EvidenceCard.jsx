import { useState } from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

const SOURCE_COLORS = {
  'Reuters': '#ff8000',
  'WHO': '#009edb',
  'AFP': '#c41230',
  'FactCheck.org': '#1a56db',
  'PolitiFact': '#9c1b1b',
  'Snopes': '#0057a5',
};

export default function EvidenceCard({ article, delay = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const credibility = article.credibility_score || 0;
  const relevance = article.relevance_score ? Math.round(article.relevance_score * 100) : 0;
  const sourceColor = SOURCE_COLORS[article.source] || '#6366f1';

  const verdictColor = article.verdict === 'true' ? '#10b981'
    : article.verdict === 'false' ? '#ef4444' : '#f59e0b';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.4 }}
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 14,
        padding: '1rem',
        backdropFilter: 'blur(20px)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div style={{ flex: 1, paddingRight: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              background: `${sourceColor}22`,
              color: sourceColor,
              border: `1px solid ${sourceColor}44`,
              borderRadius: 6,
              padding: '2px 8px',
              fontSize: '0.7rem',
              fontWeight: 700,
            }}>{article.source}</span>
            <span style={{
              background: `${verdictColor}22`,
              color: verdictColor,
              border: `1px solid ${verdictColor}44`,
              borderRadius: 6,
              padding: '2px 8px',
              fontSize: '0.65rem',
              fontWeight: 600,
              textTransform: 'uppercase',
            }}>{article.verdict}</span>
          </div>
          <div style={{ fontWeight: 600, fontSize: '0.875rem', lineHeight: 1.4, opacity: 0.9 }}>
            {article.title}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 60 }}>
          <span style={{
            background: 'rgba(99,102,241,0.2)',
            color: '#a5b4fc',
            borderRadius: 8,
            padding: '3px 8px',
            fontSize: '0.75rem',
            fontWeight: 700,
          }}>{relevance}%</span>
          <span style={{ fontSize: '0.6rem', opacity: 0.5 }}>relevance</span>
        </div>
      </div>

      {/* Credibility bar */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: '0.7rem', opacity: 0.5 }}>Credibility</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: credibility > 0.7 ? '#10b981' : credibility > 0.4 ? '#f59e0b' : '#ef4444' }}>
            {Math.round(credibility * 100)}%
          </span>
        </div>
        <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${credibility * 100}%` }}
            transition={{ duration: 0.8, delay: delay + 0.2 }}
            style={{
              height: '100%',
              borderRadius: 2,
              background: credibility > 0.7 ? '#10b981' : credibility > 0.4 ? '#f59e0b' : '#ef4444',
            }}
          />
        </div>
      </div>

      {/* Excerpt */}
      <div style={{
        fontSize: '0.78rem',
        opacity: 0.65,
        lineHeight: 1.5,
        display: '-webkit-box',
        WebkitLineClamp: expanded ? 'none' : 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
        marginBottom: 6,
      }}>
        {article.content}
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: '#6366f1', fontSize: '0.75rem', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 4, padding: 0,
        }}
      >
        {expanded ? 'Show less' : 'Read more'}
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
    </motion.div>
  );
}
