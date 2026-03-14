import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Network, Loader } from 'lucide-react';
import { getHistory, getGraphData } from '../services/api';

export default function Graph() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [ForceGraph, setForceGraph] = useState(null);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  useEffect(() => {
    import('react-force-graph-2d').then(m => setForceGraph(() => m.default));
  }, []);

  useEffect(() => {
    getHistory()
      .then(d => d.claims || [])
      .then(async (cls) => {
        if (cls.length === 0) { setLoading(false); return; }
        const allNodes = [];
        const allEdges = [];
        const seenNodes = new Set();
        for (const claim of cls.slice(0, 10)) {
          if (!claim.id) continue;
          try {
            const g = await getGraphData(claim.id);
            for (const node of (g.nodes || [])) {
              if (!seenNodes.has(node.id)) { allNodes.push(node); seenNodes.add(node.id); }
            }
            allEdges.push(...(g.edges || []));
          } catch {}
        }
        setGraphData({ nodes: allNodes, edges: allEdges });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setDimensions({ width: containerRef.current.offsetWidth, height: Math.max(500, window.innerHeight - 220) });
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  const getNodeColor = (node) => {
    if (node.type === 'claim') {
      const vmap = { TRUE: '#10b981', FALSE: '#ef4444', MISLEADING: '#f59e0b', UNVERIFIED: '#94a3b8' };
      return vmap[node.verdict] || '#6366f1';
    }
    return '#8b5cf6';
  };

  const fgData = {
    nodes: graphData.nodes.map(n => ({ ...n })),
    links: graphData.edges.map(e => ({ source: e.source, target: e.target, type: e.type }))
  };

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem 4rem' }}>
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1.5rem' }}>
          <Network size={24} style={{ color: '#6366f1' }} />
          <h1 style={{ fontSize: '1.5rem' }}>Knowledge Graph</h1>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: '1rem' }}>
          {[
            { color: '#10b981', label: 'TRUE claim' },
            { color: '#ef4444', label: 'FALSE claim' },
            { color: '#f59e0b', label: 'MISLEADING' },
            { color: '#8b5cf6', label: 'Article' },
          ].map(({ color, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', opacity: 0.7 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
              {label}
            </div>
          ))}
        </div>

        <div
          ref={containerRef}
          className="glass"
          style={{ overflow: 'hidden', padding: 0, minHeight: 500 }}
        >
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 500, gap: 16, opacity: 0.5 }}>
              <Loader size={32} style={{ animation: 'spin 1s linear infinite' }} />
              <p>Loading graph data...</p>
            </div>
          ) : graphData.nodes.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 500, gap: 16, opacity: 0.5 }}>
              <Network size={48} style={{ opacity: 0.3 }} />
              <p style={{ fontSize: '1.1rem' }}>No graph data yet</p>
              <p style={{ fontSize: '0.85rem' }}>Verify some claims first to populate the knowledge graph</p>
            </div>
          ) : ForceGraph ? (
            <ForceGraph
              graphData={fgData}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor="transparent"
              nodeLabel={n => `${n.label}${n.type === 'claim' ? ` (${n.verdict})` : ''}`}
              nodeColor={getNodeColor}
              nodeRelSize={6}
              linkColor={() => 'rgba(255,255,255,0.15)'}
              linkWidth={1.5}
              onNodeClick={(node) => setSelected(node)}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const label = node.label?.slice(0, 20) + (node.label?.length > 20 ? '...' : '');
                const size = node.type === 'claim' ? 8 : 5;
                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
                ctx.fillStyle = getNodeColor(node);
                ctx.fill();
                ctx.strokeStyle = 'rgba(255,255,255,0.3)';
                ctx.lineWidth = 1;
                ctx.stroke();
                if (globalScale >= 1) {
                  ctx.font = `${10 / globalScale}px Inter, sans-serif`;
                  ctx.fillStyle = 'rgba(255,255,255,0.7)';
                  ctx.textAlign = 'center';
                  ctx.fillText(label, node.x, node.y + size + 10 / globalScale);
                }
              }}
            />
          ) : null}
        </div>

        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass"
            style={{ padding: '1rem 1.25rem', marginTop: '1rem' }}
          >
            <div style={{ fontWeight: 700, marginBottom: 6 }}>{selected.label}</div>
            <div style={{ fontSize: '0.85rem', opacity: 0.7 }}>
              Type: {selected.type} {selected.verdict && `| Verdict: ${selected.verdict}`}
            </div>
          </motion.div>
        )}
      </motion.div>
    </main>
  );
}
