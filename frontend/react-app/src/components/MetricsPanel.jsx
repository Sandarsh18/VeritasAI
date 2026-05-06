function toSeconds(value) {
  if (value == null || value === "") return null;

  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;

  if (numeric > 1000) return numeric / 1000;
  return numeric;
}

function formatSeconds(value) {
  const seconds = toSeconds(value);
  if (seconds == null) return "—";
  return `${seconds.toFixed(2)}s`;
}

function Metric({ label, value }) {
  return (
    <div style={{ minWidth: 120 }}>
      <strong>{label}:</strong>
      <div>{value}</div>
    </div>
  );
}

export default function MetricsPanel({ pipeline_metrics = {} }) {
  const total = pipeline_metrics.total_time ?? null;
  const retrieval = pipeline_metrics.retrieval_time ?? null;
  const agent = pipeline_metrics.agent_time ?? null;
  const cacheHit = Boolean(pipeline_metrics.cache_hit);
  const cacheSource = pipeline_metrics.cache_source || "";

  return (
    <div style={{ marginTop: 12, fontSize: 13 }}>
      <strong>Pipeline Metrics</strong>
      <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
        <Metric label="Total" value={formatSeconds(total)} />
        <Metric label="Retrieval" value={formatSeconds(retrieval)} />
        <Metric label="Agents" value={formatSeconds(agent)} />
        <Metric label="Cache" value={cacheHit ? "HIT" : "MISS"} />
        {cacheSource ? <Metric label="Source" value={cacheSource} /> : null}
      </div>
    </div>
  );
}
