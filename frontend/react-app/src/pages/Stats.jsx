import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Target, Database, Cpu } from 'lucide-react';

const AGENT_MODELS_INFO = [
  {
    role: 'Prosecutor',
    model: 'Mistral 7B',
    tag: 'mistral',
    params: '7 billion',
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.08)',
    border: 'rgba(239,68,68,0.25)',
    emoji: '🔴',
    desc: 'Searches for evidence that contradicts the news claim.',
  },
  {
    role: 'Defender',
    model: 'Phi-3 Mini',
    tag: 'phi3',
    params: '3.8 billion',
    color: '#10b981',
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.25)',
    emoji: '🟢',
    desc: 'Finds supporting evidence and arguments for the claim.',
  },
  {
    role: 'Judge',
    model: 'LLaMA 3',
    tag: 'llama3',
    params: '8 billion',
    color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.08)',
    border: 'rgba(139,92,246,0.25)',
    emoji: '⚖️',
    desc: 'Weighs both sides and delivers the final verdict.',
  },
  {
    role: 'Claim Analyzer',
    model: 'Mistral 7B',
    tag: 'mistral',
    params: '7 billion',
    color: '#f59e0b',
    bg: 'rgba(245,158,11,0.08)',
    border: 'rgba(245,158,11,0.25)',
    emoji: '🔍',
    desc: 'Extracts entities, keywords, and claim type for context.',
  },
];
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { getStats } from '../services/api';

const VERDICT_COLORS = { TRUE: '#10b981', FALSE: '#ef4444', MISLEADING: '#f59e0b', UNVERIFIED: '#94a3b8' };

export default function Stats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats({ total_claims: 0, verdict_distribution: {}, top_sources: [] }))
      .finally(() => setLoading(false));
  }, []);

  const pieData = stats
    ? Object.entries(stats.verdict_distribution || {}).map(([name, value]) => ({ name, value }))
    : [];

  const barData = stats?.top_sources?.map(s => ({ name: s.source, count: s.count })) || [];

  const statCards = [
    { label: 'Total Claims', value: stats?.total_claims || 0, icon: Database, color: '#6366f1' },
    { label: 'Unique Sources', value: stats?.top_sources?.length || 0, icon: Target, color: '#10b981' },
    { label: 'Verdict Types', value: Object.keys(stats?.verdict_distribution || {}).length, icon: TrendingUp, color: '#f59e0b' },
    { label: 'Graph Nodes', value: (stats?.total_claims || 0) * 3, icon: BarChart3, color: '#8b5cf6' },
  ];

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1.5rem 4rem' }}>
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '2rem' }}>
          <BarChart3 size={24} style={{ color: '#6366f1' }} />
          <h1 style={{ fontSize: '1.5rem' }}>System Statistics</h1>
        </div>

        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 16 }} />)}
          </div>
        ) : (
          <>
            {/* Stat cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              {statCards.map((card, i) => {
                const Icon = card.icon;
                return (
                  <motion.div
                    key={card.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="glass"
                    style={{ padding: '1.25rem', textAlign: 'center' }}
                  >
                    <Icon size={28} style={{ color: card.color, marginBottom: 8 }} />
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: card.color }}>{card.value}</div>
                    <div style={{ fontSize: '0.8rem', opacity: 0.6, fontWeight: 500 }}>{card.label}</div>
                  </motion.div>
                );
              })}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
              {/* Pie chart */}
              <motion.div
                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}
                className="glass" style={{ padding: '1.5rem' }}
              >
                <h3 style={{ marginBottom: '1rem', fontSize: '1rem', opacity: 0.8 }}>Verdict Distribution</h3>
                {pieData.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '2rem', opacity: 0.4 }}>No data yet</div>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" paddingAngle={3}>
                        {pieData.map((entry) => (
                          <Cell key={entry.name} fill={VERDICT_COLORS[entry.name] || '#6366f1'} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: '#1e1e2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: '0.8rem' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginTop: 8 }}>
                  {pieData.map(d => (
                    <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.75rem' }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: VERDICT_COLORS[d.name] || '#6366f1' }} />
                      {d.name}: {d.value}
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Bar chart */}
              <motion.div
                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}
                className="glass" style={{ padding: '1.5rem' }}
              >
                <h3 style={{ marginBottom: '1rem', fontSize: '1rem', opacity: 0.8 }}>Top Sources</h3>
                {barData.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '2rem', opacity: 0.4 }}>No data yet</div>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={barData} layout="vertical" margin={{ left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} width={80} />
                      <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: '0.8rem' }} />
                      <Bar dataKey="count" fill="#6366f1" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </motion.div>
            </div>

            {/* Agent Models Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              style={{ marginTop: '2rem' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '1rem' }}>
                <Cpu size={18} style={{ color: '#8b5cf6' }} />
                <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Agent Models</h3>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                {AGENT_MODELS_INFO.map((agent, i) => (
                  <motion.div
                    key={agent.role}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.55 + i * 0.08 }}
                    style={{
                      background: agent.bg,
                      border: `1px solid ${agent.border}`,
                      borderRadius: 16,
                      padding: '1.1rem 1.25rem',
                      backdropFilter: 'blur(20px)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{ fontSize: '1.2rem' }}>{agent.emoji}</span>
                      <div>
                        <div style={{ fontWeight: 700, color: agent.color, fontSize: '0.9rem' }}>{agent.role}</div>
                        <div style={{
                          display: 'inline-block',
                          marginTop: 3,
                          padding: '2px 8px',
                          borderRadius: 20,
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          letterSpacing: '0.04em',
                          background: `${agent.color}22`,
                          border: `1px solid ${agent.color}55`,
                          color: agent.color,
                        }}>
                          {agent.model}
                        </div>
                      </div>
                    </div>
                    <div style={{ fontSize: '0.75rem', opacity: 0.5, marginBottom: 6 }}>
                      Parameters: <span style={{ color: agent.color, fontWeight: 600 }}>{agent.params}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', opacity: 0.7, lineHeight: 1.5 }}>{agent.desc}</div>
                    <div style={{ marginTop: 8, fontSize: '0.65rem', opacity: 0.4, fontFamily: 'monospace' }}>
                      tag: {agent.tag}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </motion.div>
    </main>
  );
}
