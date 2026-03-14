import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { History as HistoryIcon, Filter, Download } from 'lucide-react';
import { getHistory } from '../services/api';
import VerdictBadge from '../components/VerdictBadge';

export default function History() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getHistory()
      .then(d => setClaims(d.claims || []))
      .catch(() => setClaims([]))
      .finally(() => setLoading(false));
  }, []);

  const verdicts = ['ALL', 'TRUE', 'FALSE', 'MISLEADING', 'UNVERIFIED'];
  const filtered = filter === 'ALL' ? claims : claims.filter(c => c.verdict === filter);

  const exportCSV = () => {
    const rows = [['Claim', 'Verdict', 'Confidence', 'Timestamp']];
    filtered.forEach(c => rows.push([`"${c.text}"`, c.verdict, c.confidence, c.timestamp]));
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'claims_history.csv'; a.click();
  };

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1.5rem 4rem' }}>
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <HistoryIcon size={24} style={{ color: '#6366f1' }} />
            <h1 style={{ fontSize: '1.5rem' }}>Claims History</h1>
          </div>
          <button onClick={exportCSV} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)',
            borderRadius: 10, padding: '8px 14px', color: '#a5b4fc',
            cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, fontFamily: 'inherit',
          }}>
            <Download size={14} /> Export CSV
          </button>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 8, marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <Filter size={16} style={{ opacity: 0.5, alignSelf: 'center' }} />
          {verdicts.map(v => (
            <button key={v} onClick={() => setFilter(v)} style={{
              padding: '5px 14px', borderRadius: 20,
              background: filter === v ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${filter === v ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.08)'}`,
              color: filter === v ? '#a5b4fc' : 'inherit',
              cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600, fontFamily: 'inherit',
              transition: 'all 0.2s',
            }}>
              {v}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[...Array(5)].map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 72, borderRadius: 12 }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ textAlign: 'center', padding: '4rem', opacity: 0.5 }}>
            <HistoryIcon size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
            <p style={{ fontSize: '1.1rem' }}>No claims found</p>
            <p style={{ fontSize: '0.85rem', marginTop: 8 }}>Submit a claim on the home page to get started</p>
          </motion.div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map((claim, i) => (
              <motion.div
                key={claim.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="glass"
                style={{ padding: '1rem 1.25rem', cursor: 'pointer' }}
                onClick={() => setExpanded(expanded === claim.id ? null : claim.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontWeight: 500, fontSize: '0.9rem', marginBottom: 4, opacity: 0.9 }}>
                      {claim.text}
                    </p>
                    <p style={{ fontSize: '0.72rem', opacity: 0.45 }}>
                      {claim.timestamp ? new Date(claim.timestamp).toLocaleString() : 'Unknown date'}
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <VerdictBadge verdict={claim.verdict || 'UNVERIFIED'} size="small" />
                    <span style={{
                      background: 'rgba(255,255,255,0.08)', borderRadius: 8,
                      padding: '3px 10px', fontSize: '0.75rem', fontWeight: 600,
                    }}>{claim.confidence || '?'}%</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </main>
  );
}
