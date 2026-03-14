import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { History as HistoryIcon, Filter, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { bookmarkClaim, deleteMyClaim, getHistory, getUserClaims } from '../services/api';
import VerdictBadge from '../components/VerdictBadge';

export default function History() {
  const { isAuthenticated } = useAuth();
  const [tab, setTab] = useState('all');
  const [claims, setClaims] = useState([]);
  const [myClaims, setMyClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    Promise.all([
      getHistory().then((d) => setClaims(d.claims || [])).catch(() => setClaims([])),
      isAuthenticated
        ? getUserClaims({ limit: 100 }).then((d) => setMyClaims(d.claims || [])).catch(() => setMyClaims([]))
        : Promise.resolve(),
    ])
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  const verdicts = ['ALL', 'TRUE', 'FALSE', 'MISLEADING', 'UNVERIFIED'];
  const source = tab === 'my' ? myClaims : claims;
  const filtered = filter === 'ALL' ? source : source.filter(c => c.verdict === filter);

  const exportCSV = () => {
    const rows = [['Claim', 'Verdict', 'Confidence', 'Timestamp']];
    filtered.forEach(c => rows.push([`"${c.text}"`, c.verdict, c.confidence, c.timestamp]));
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = tab === 'my' ? 'my_claims_history.csv' : 'claims_history.csv'; a.click();
  };

  const refreshMyClaims = async () => {
    if (!isAuthenticated) return;
    const data = await getUserClaims({ limit: 100 });
    setMyClaims(data.claims || []);
  };

  const handleBookmark = async (id) => {
    await bookmarkClaim(id);
    toast.success('Bookmark updated');
    await refreshMyClaims();
  };

  const handleDelete = async (id) => {
    await deleteMyClaim(id);
    toast.success('Claim deleted');
    await refreshMyClaims();
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

        {isAuthenticated && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <button onClick={() => setTab('all')} style={{ borderRadius: 999, padding: '5px 12px', border: '1px solid var(--border-dark)', background: tab === 'all' ? 'rgba(99,102,241,0.2)' : 'transparent', color: 'inherit', cursor: 'pointer' }}>🌐 All Claims</button>
            <button onClick={() => setTab('my')} style={{ borderRadius: 999, padding: '5px 12px', border: '1px solid var(--border-dark)', background: tab === 'my' ? 'rgba(99,102,241,0.2)' : 'transparent', color: 'inherit', cursor: 'pointer' }}>👤 My Claims</button>
          </div>
        )}

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
            <p style={{ fontSize: '1.1rem' }}>📭 No claims match your filter.</p>
            <button onClick={() => setFilter('ALL')} style={{ marginTop: 8, border: '1px solid var(--border-dark)', borderRadius: 10, padding: '6px 10px', background: 'transparent', color: 'inherit', cursor: 'pointer' }}>Clear filters</button>
          </motion.div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map((claim, i) => (
              <motion.div
                key={`${tab}-${claim.id}`}
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
                      {claim.text || claim.claim_text}
                    </p>
                    <p style={{ fontSize: '0.72rem', opacity: 0.45 }}>
                      {(claim.timestamp || claim.date) ? new Date(claim.timestamp || claim.date).toLocaleString() : 'Unknown date'}
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <VerdictBadge verdict={claim.verdict || 'UNVERIFIED'} size="small" />
                    <span style={{
                      background: 'rgba(255,255,255,0.08)', borderRadius: 8,
                      padding: '3px 10px', fontSize: '0.75rem', fontWeight: 600,
                    }}>{claim.confidence || '?'}%</span>
                    {tab === 'my' && (
                      <>
                        <button onClick={(e) => { e.stopPropagation(); handleBookmark(claim.id); }} style={{ border: '1px solid var(--border-dark)', borderRadius: 8, padding: '4px 8px', background: claim.bookmarked ? 'rgba(99,102,241,0.2)' : 'transparent', color: 'inherit', cursor: 'pointer' }}>🔖</button>
                        <button onClick={(e) => { e.stopPropagation(); handleDelete(claim.id); }} style={{ border: '1px solid #ef4444', borderRadius: 8, padding: '4px 8px', background: 'transparent', color: '#f87171', cursor: 'pointer' }}>Delete</button>
                      </>
                    )}
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
