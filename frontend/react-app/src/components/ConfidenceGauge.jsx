import React from "react";

const ConfidenceGauge = ({ confidence = 0 }) => {
  const pct = Math.min(Math.max(confidence, 0), 1);
  const color = pct > 0.7 ? "#22c55e" : pct > 0.4 ? "#f59e0b" : "#ef4444";
  const radius = 40;
  const circumference = Math.PI * radius;
  const dash = pct * circumference;

  return (
    <div style={{ textAlign: "center", padding: "8px" }}>
      <svg width="100" height="60" viewBox="0 0 100 60">
        <path
          d="M 10 55 A 40 40 0 0 1 90 55"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d="M 10 55 A 40 40 0 0 1 90 55"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
        <text x="50" y="52" textAnchor="middle" fontSize="13" fontWeight="bold" fill={color}>
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <div style={{ fontSize: "11px", color: "#6b7280", marginTop: "-4px" }}>Confidence</div>
    </div>
  );
};

export default ConfidenceGauge;
