const WARNING_STYLES = {
  critical: {
    background: 'rgba(220,38,38,0.2)',
    border: '1px solid rgba(220,38,38,0.9)',
    color: '#fecaca',
    boxShadow: '0 0 0 0 rgba(220,38,38,0.6)',
    animation: 'pulse 1.6s infinite',
  },
  high: {
    background: 'rgba(239,68,68,0.2)',
    border: '1px solid rgba(239,68,68,0.7)',
    color: '#fecaca',
  },
  medium: {
    background: 'rgba(245,158,11,0.2)',
    border: '1px solid rgba(245,158,11,0.7)',
    color: '#fde68a',
  },
  low: {
    background: 'rgba(16,185,129,0.2)',
    border: '1px solid rgba(16,185,129,0.7)',
    color: '#bbf7d0',
  },
};

function Section({ title, children }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.06em', fontWeight: 700, marginBottom: 6 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

export default function MisinformationTracker({ data, verdict }) {
  const tracking = data?.source_tracking || {};
  const online = data?.online_presence || {};
  const level = (tracking.warning_level || 'medium').toLowerCase();
  const badgeStyle = WARNING_STYLES[level] || WARNING_STYLES.medium;

  if (!['FALSE', 'MISLEADING'].includes(verdict)) return null;

  return (
    <div className="glass-card" style={{ padding: '1rem 1.1rem', borderRadius: 14 }}>
      <div style={{ fontSize: '1rem', fontWeight: 800, marginBottom: 8, color: 'var(--text-primary)' }}>
        🕵️ Misinformation Analysis
      </div>

      <div style={{ borderTop: '1px solid rgba(148,163,184,0.3)', marginBottom: 8 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700, color: 'var(--text-secondary)' }}>⚠️ WARNING LEVEL:</span>
        <span style={{ ...badgeStyle, borderRadius: 999, padding: '4px 10px', fontWeight: 800, fontSize: '0.78rem' }}>
          {level.toUpperCase()}
        </span>
      </div>
      <div style={{ marginTop: 6, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        {tracking.warning_reason || `This claim poses ${level.toUpperCase()} risk of public harm`}
      </div>

      <Section title="📍 ORIGIN TYPE">
        <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{(tracking.origin_type || 'unknown').replaceAll('_', ' ')}</div>
      </Section>

      <Section title="📱 SPREADING ON">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(tracking.spreading_platforms || []).slice(0, 8).map((platform, idx) => (
            <span key={`${platform}-${idx}`} className="source-badge">
              {platform}
            </span>
          ))}
        </div>
      </Section>

      <Section title="🔄 HOW IT SPREADS">
        <div style={{ color: 'var(--text-secondary)' }}>{tracking.spread_pattern || 'Pattern unavailable'}</div>
      </Section>

      <Section title="💰 WHO BENEFITS">
        <div style={{ color: 'var(--text-secondary)' }}>{tracking.who_benefits || 'Cannot determine'}</div>
      </Section>

      <Section title="✅ ALREADY FACT-CHECKED BY">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(tracking.fact_checked_by || []).length > 0 ? (
            (tracking.fact_checked_by || []).map((org, idx) => (
              <span key={`${org}-${idx}`} className="source-badge">{org}</span>
            ))
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>No named fact-checkers found</span>
          )}
        </div>
      </Section>

      <Section title="🔎 FOUND IN NEWS">
        <div style={{ display: 'grid', gap: 6 }}>
          {(online.found_in_news || []).slice(0, 3).map((item, idx) => (
            <a
              key={`${item.url || item.title}-${idx}`}
              href={item.url}
              target="_blank"
              rel="noreferrer"
              style={{ color: '#c7d2fe', fontSize: '0.88rem', textDecoration: 'none' }}
            >
              • {item.source || 'Unknown'}: {item.title || 'Untitled'} 🔗
            </a>
          ))}
          {(online.found_in_news || []).length === 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>No matching news entries found.</span>
          )}
        </div>
      </Section>

      <Section title="💡 HOW TO SPOT THIS FAKE NEWS">
        <ol style={{ margin: 0, paddingLeft: 18, color: 'var(--text-secondary)' }}>
          {(tracking.how_to_spot || []).slice(0, 3).map((tip, idx) => (
            <li key={`${tip}-${idx}`} style={{ marginBottom: 4 }}>{tip}</li>
          ))}
          {(tracking.how_to_spot || []).length === 0 && (
            <li>Check official sources and verify with multiple trusted outlets.</li>
          )}
        </ol>
      </Section>
    </div>
  );
}
