import { useEffect, useMemo, useState } from 'react';
import { getTrending } from '../services/api';

export default function Trending() {
  const [data, setData] = useState({ claims: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTrending()
      .then(setData)
      .catch(() => setData({ claims: [] }))
      .finally(() => setLoading(false));
  }, []);

  const summary = useMemo(() => {
    const claims = data.claims || [];
    const today = new Date().toISOString().slice(0, 10);
    const todayCount = claims.filter((c) => (c.created_at || '').startsWith(today)).length;
    const verdictCount = claims.reduce((acc, item) => {
      acc[item.verdict] = (acc[item.verdict] || 0) + 1;
      return acc;
    }, {});
    const topVerdict = Object.entries(verdictCount).sort((a, b) => b[1] - a[1])[0];
    return { todayCount, topVerdict };
  }, [data]);

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem 4rem' }}>
      <h1 style={{ marginBottom: 14 }}>🔥 Trending Claims This Week</h1>
      {loading ? (
        <div style={{ display: 'grid', gap: 10 }}>{Array.from({ length: 8 }).map((_, i) => <div className="skeleton" key={i} style={{ height: 50 }} />)}</div>
      ) : (
        <section className="glass" style={{ padding: '1rem' }}>
          {(data.claims || []).map((item, index) => (
            <div key={`${item.claim}-${index}`} style={{ padding: '10px 6px', borderBottom: '1px solid var(--border-dark)', display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <div>#{index + 1} {item.claim}</div>
              <div style={{ whiteSpace: 'nowrap', opacity: 0.85 }}>{item.verdict} {Math.round(item.confidence || 0)}% — {item.verification_count}x</div>
            </div>
          ))}
          <div style={{ marginTop: 12, opacity: 0.8 }}>
            <p>Most verified today: {summary.todayCount} claims</p>
            <p>Top verdict: {summary.topVerdict ? `${summary.topVerdict[0]} (${summary.topVerdict[1]})` : '-'}</p>
          </div>
        </section>
      )}
    </main>
  );
}
