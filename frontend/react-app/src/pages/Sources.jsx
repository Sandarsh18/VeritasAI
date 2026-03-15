import { useEffect, useMemo, useState } from 'react';
import { getSources } from '../services/api';

function scoreColor(score) {
  if (score > 0.9) return '#10b981';
  if (score >= 0.75) return '#f59e0b';
  return '#fb923c';
}

function countryFlag(country) {
  if (country === 'India') return '🇮🇳';
  if (country === 'International') return '🌍';
  return '🏳️';
}

function SourceCard({ source }) {
  const pct = Math.round((source.score || 0) * 100);
  const barColor = scoreColor(source.score || 0);
  return (
    <div
      className="glass"
      title={`Why trusted? ${source.name} is tracked as ${source.type} with a credibility score of ${pct}% based on historical reliability.`}
      style={{
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 12,
        padding: '12px',
        display: 'grid',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ fontWeight: 700, lineHeight: 1.2 }}>
          <span style={{ marginRight: 6 }}>{source.logo || '📰'}</span>
          {source.name}
        </div>
        <span style={{ fontSize: '0.85rem' }}>{countryFlag(source.country)}</span>
      </div>

      <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>{source.type}</div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: 4 }}>
          <span>Score</span>
          <span style={{ color: barColor, fontWeight: 700 }}>{pct}%</span>
        </div>
        <div style={{ height: 7, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: barColor }} />
        </div>
      </div>

      <div style={{ fontSize: '0.72rem', opacity: 0.68 }}>Why trusted? Hover this card</div>
    </div>
  );
}

function SourceSection({ title, sources }) {
  if (!sources.length) return null;
  return (
    <section style={{ marginTop: '1.3rem' }}>
      <div style={{ fontWeight: 700, opacity: 0.8, marginBottom: 10, fontSize: '0.86rem', letterSpacing: '0.04em' }}>{title}</div>
      <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))' }}>
        {sources.map((source) => (
          <SourceCard key={source.domain} source={source} />
        ))}
      </div>
    </section>
  );
}

export default function Sources() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getSources();
        setSources(data.sources || []);
      } catch {
        setError('Failed to load sources registry.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const { international, indian, factCheckers } = useMemo(() => {
    const internationalItems = [];
    const indianItems = [];
    const factCheckerItems = [];

    sources.forEach((source) => {
      if ((source.type || '').toLowerCase().includes('fact checker')) {
        factCheckerItems.push(source);
      }
      if (source.country === 'India') {
        indianItems.push(source);
      } else {
        internationalItems.push(source);
      }
    });

    return {
      international: internationalItems,
      indian: indianItems,
      factCheckers: factCheckerItems,
    };
  }, [sources]);

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem 4rem' }}>
      <div className="glass" style={{ borderRadius: 14, padding: '1.2rem', border: '1px solid rgba(99,102,241,0.25)' }}>
        <div style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: 6 }}>🏛️ Trusted Sources Registry</div>
        <div style={{ opacity: 0.8, fontSize: '0.92rem' }}>Sources VeritasAI uses for fact-checking and real-time evidence retrieval.</div>

        {loading && <div style={{ marginTop: 14, opacity: 0.75 }}>Loading sources…</div>}
        {error && <div style={{ marginTop: 14, color: '#fca5a5' }}>{error}</div>}

        {!loading && !error && (
          <>
            <SourceSection title="INTERNATIONAL SOURCES" sources={international} />
            <SourceSection title="INDIAN SOURCES" sources={indian} />
            <SourceSection title="FACT CHECKERS" sources={factCheckers} />
          </>
        )}
      </div>
    </main>
  );
}
