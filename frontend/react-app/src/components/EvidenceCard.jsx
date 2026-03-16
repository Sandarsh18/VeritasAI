import { motion } from 'framer-motion';

export default function EvidenceCard({ article, index = 0 }) {
  const credibility = Math.round((Number(article?.credibility_score || 0) || 0) * 100);
  const relevance = Math.round((Number(article?.relevance_score || 0.5) || 0.5) * 100);

  return (
    <motion.div
      className="evidence-card glass-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      style={{ borderRadius: 14, padding: '1rem', display: 'flex', flexDirection: 'column', gap: 10 }}
    >
      <div className="evidence-header" style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="source-logo" style={{ fontSize: '1.1rem' }}>
            {article.source_logo || '📰'}
          </span>
          <div className="source-info" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span className="evidence-source">{article.source || 'Unknown'}</span>
            <span className="source-type-badge source-badge">{article.source_type || 'Unknown Source'}</span>
          </div>
        </div>

        <div className="right-badges">
          {article.is_realtime ? (
            <span className="live-badge source-badge">🌐 LIVE</span>
          ) : (
            <span className="archive-badge source-badge">📁 ARCHIVE</span>
          )}
        </div>
      </div>

      <h3 className="evidence-title">{article.title || 'Untitled'}</h3>

      <div className="evidence-meta" style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <span className="evidence-author">✍️ {article.author || 'Staff Reporter'}</span>
        <span className="evidence-date">📅 {article.published_date || 'Recent'}</span>
      </div>

      <p className="evidence-content">{(article.content || 'No content available.').slice(0, 200)}...</p>

      <div className="score-bars" style={{ display: 'grid', gap: 8 }}>
        <div className="score-row" style={{ display: 'grid', gridTemplateColumns: '92px 1fr 48px', alignItems: 'center', gap: 8 }}>
          <span className="score-label" style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Credibility</span>
          <div className="score-bar" style={{ background: 'rgba(148,163,184,0.18)', height: 8, borderRadius: 99, overflow: 'hidden' }}>
            <div className="score-fill credibility" style={{ width: `${credibility}%`, height: '100%', background: '#10b981' }} />
          </div>
          <span className="score-pct" style={{ color: '#86efac', fontWeight: 700, fontSize: '0.8rem' }}>{credibility}%</span>
        </div>

        <div className="score-row" style={{ display: 'grid', gridTemplateColumns: '92px 1fr 48px', alignItems: 'center', gap: 8 }}>
          <span className="score-label" style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Relevance</span>
          <div className="score-bar" style={{ background: 'rgba(148,163,184,0.18)', height: 8, borderRadius: 99, overflow: 'hidden' }}>
            <div className="score-fill relevance" style={{ width: `${relevance}%`, height: '100%', background: '#6366f1' }} />
          </div>
          <span className="score-pct" style={{ color: '#a5b4fc', fontWeight: 700, fontSize: '0.8rem' }}>{relevance}%</span>
        </div>
      </div>

      {article.source_url && (
        <a
          href={article.source_url}
          target="_blank"
          rel="noreferrer"
          className="read-article-btn"
          style={{
            display: 'inline-flex',
            width: 'fit-content',
            marginTop: 6,
            textDecoration: 'none',
            background: 'rgba(99,102,241,0.15)',
            border: '1px solid rgba(99,102,241,0.35)',
            color: '#c7d2fe',
            borderRadius: 10,
            padding: '8px 12px',
            fontWeight: 700,
            fontSize: '0.82rem',
          }}
        >
          🔗 Read Full Article at {article.source || 'source'}
        </a>
      )}
    </motion.div>
  );
}
