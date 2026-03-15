import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { CalendarDays, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import VerdictBadge from './VerdictBadge';

function scoreColor(score) {
  if (score > 0.9) return '#10b981';
  if (score >= 0.7) return '#f59e0b';
  return '#fb923c';
}

function toPercent(value) {
  return Math.max(0, Math.min(100, Math.round((value || 0) * 100)));
}

export default function EvidenceCard({ article, delay = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const credibility = Number(article.credibility_score || 0);
  const relevance = Number(article.relevance_score || 0);
  const credibilityPct = toPercent(credibility);
  const relevancePct = toPercent(relevance);
  const credibilityColor = scoreColor(credibility);

  const liveBadge = useMemo(() => {
    if (article.is_realtime) {
      return (
        <motion.span
          animate={{ opacity: [0.8, 1, 0.8] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          style={{
            background: 'rgba(16,185,129,0.16)',
            border: '1px solid rgba(16,185,129,0.45)',
            color: '#6ee7b7',
            borderRadius: 999,
            padding: '3px 10px',
            fontWeight: 700,
            fontSize: '0.7rem',
          }}
        >
          🌐 LIVE
        </motion.span>
      );
    }
    return (
      <span
        style={{
          background: 'rgba(148,163,184,0.15)',
          border: '1px solid rgba(148,163,184,0.3)',
          color: '#cbd5e1',
          borderRadius: 999,
          padding: '3px 10px',
          fontWeight: 700,
          fontSize: '0.7rem',
        }}
      >
        📁 ARCHIVE
      </span>
    );
  }, [article.is_realtime]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 14,
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 700 }}>{article.source_logo || '📰'} {article.source || 'Unknown'}</span>
            <span style={{ fontSize: '0.72rem', opacity: 0.75 }}>{article.source_type || 'Unknown Source'}</span>
            {liveBadge}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, opacity: 0.7, fontSize: '0.78rem' }}>
            <CalendarDays size={13} />
            <span>{article.published_date || 'Unknown date'}</span>
          </div>
        </div>
      </div>

      <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 10 }}>
        <div style={{ fontWeight: 700, lineHeight: 1.45, marginBottom: 8 }}>{article.title}</div>

        {article.image_url && (
          <img
            src={article.image_url}
            alt={article.title || 'Article image'}
            style={{ width: '100%', height: 140, objectFit: 'cover', borderRadius: 10, marginBottom: 10 }}
          />
        )}

        <div style={{ fontStyle: 'italic', opacity: 0.82, fontSize: '0.82rem', marginBottom: 8 }}>
          By {article.author || 'Staff Reporter'} • {article.source || 'Unknown'}
        </div>

        <div
          style={{
            fontSize: '0.85rem',
            lineHeight: 1.55,
            opacity: 0.78,
            display: '-webkit-box',
            WebkitLineClamp: expanded ? 'none' : 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {article.content || 'No content available.'}
        </div>
        <button
          onClick={() => setExpanded((prev) => !prev)}
          style={{
            marginTop: 6,
            border: 'none',
            background: 'transparent',
            color: '#a5b4fc',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: 0,
            fontWeight: 600,
            fontSize: '0.78rem',
          }}
        >
          {expanded ? 'Show less' : 'Read more'}
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 10, display: 'grid', gap: 8 }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: 4 }}>
            <span>Credibility</span>
            <span style={{ color: credibilityColor, fontWeight: 700 }}>{credibilityPct}%</span>
          </div>
          <div style={{ height: 7, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${credibilityPct}%` }}
              transition={{ duration: 0.6, delay: delay + 0.1 }}
              style={{ height: '100%', background: credibilityColor }}
            />
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: 4 }}>
            <span>Relevance</span>
            <span style={{ color: '#a5b4fc', fontWeight: 700 }}>{relevancePct}%</span>
          </div>
          <div style={{ height: 7, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${relevancePct}%` }}
              transition={{ duration: 0.6, delay: delay + 0.15 }}
              style={{ height: '100%', background: '#6366f1' }}
            />
          </div>
        </div>
      </div>

      <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        {article.source_url ? (
          <a
            href={article.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(99,102,241,0.14)',
              border: '1px solid rgba(99,102,241,0.35)',
              borderRadius: 10,
              padding: '7px 10px',
              fontSize: '0.8rem',
              fontWeight: 700,
              color: '#c7d2fe',
            }}
          >
            <ExternalLink size={13} /> Read Full Article
          </a>
        ) : (
          <span style={{ fontSize: '0.78rem', opacity: 0.65 }}>Source URL unavailable</span>
        )}
        <VerdictBadge verdict={article.verdict || 'UNVERIFIED'} size="small" />
      </div>
    </motion.div>
  );
}
