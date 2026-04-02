import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Bar, Doughnut, Line } from "react-chartjs-2";
import {
  ArcElement,
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

import { getHistory, getStats } from "../services/api";

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend
);

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  },
  exit: { opacity: 0, x: -20, transition: { duration: 0.2 } }
};

const cardVariants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 260, damping: 20 } }
};

function Stats() {
  const [stats, setStats] = useState({ total_claims: 0, avg_confidence: 0, verdicts_breakdown: {} });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats({ total_claims: 0, avg_confidence: 0, verdicts_breakdown: {} }));
    getHistory().then(setHistory).catch(() => setHistory([]));
  }, []);

  const chartData = useMemo(() => {
    const labels = Object.keys(stats.verdicts_breakdown || {});
    const dataValues = Object.values(stats.verdicts_breakdown || {});

    const colorByVerdict = (label) => {
      const key = String(label || "").toUpperCase();
      if (key === "FALSE") return { bg: "#dc2626", hover: "#ef4444" };
      if (key === "TRUE") return { bg: "#166534", hover: "#15803d" };
      if (key === "MISLEADING") return { bg: "#f59e0b", hover: "#fbbf24" };
      return { bg: "#6b7280", hover: "#9ca3af" };
    };

    const backgroundColor = labels.map((label) => colorByVerdict(label).bg);
    const hoverBackgroundColor = labels.map((label) => colorByVerdict(label).hover);

    return {
      labels,
      datasets: [
        {
          label: 'Verdict Distribution',
          data: dataValues,
          backgroundColor,
          borderRadius: 6,
          hoverBackgroundColor,
        }
      ]
    };
  }, [stats.verdicts_breakdown]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: '#1f1f2e',
        titleColor: '#fff',
        bodyColor: '#fff',
        padding: 12,
        cornerRadius: 8,
        displayColors: false,
      }
    },
    scales: {
      x: {
        grid: {
          display: false,
          drawBorder: false,
        },
        ticks: {
          color: '#9ca3af',
        }
      },
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
          drawBorder: false,
        },
        ticks: {
          color: '#9ca3af',
        }
      }
    },
    animation: {
      duration: 1500,
      easing: 'easeOutQuart'
    }
  };

  const domainDistribution = useMemo(() => {
    const counts = {};
    for (const row of history) {
      const domain = row.domain || "general";
      counts[domain] = (counts[domain] || 0) + 1;
    }
    return counts;
  }, [history]);

  const doughnutData = useMemo(() => {
    const labels = Object.keys(domainDistribution);
    const values = Object.values(domainDistribution);
    return {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: ["#6c63ff", "#22c55e", "#f97316", "#ef4444", "#06b6d4", "#eab308"],
          borderWidth: 0,
          hoverOffset: 8,
        },
      ],
    };
  }, [domainDistribution]);

  const confidenceTrendData = useMemo(() => {
    const sorted = [...history].reverse().slice(-10);
    return {
      labels: sorted.map((_, idx) => `#${idx + 1}`),
      datasets: [
        {
          label: "Confidence Trend",
          data: sorted.map((row) => Math.round(row.confidence || 0)),
          borderColor: "#6c63ff",
          backgroundColor: "rgba(108, 99, 255, 0.2)",
          fill: true,
          tension: 0.35,
          pointRadius: 3,
        },
      ],
    };
  }, [history]);

  const latestVerdict = history[0]?.verdict || "N/A";
  const highConfidenceCount = history.filter((row) => Number(row.confidence) >= 80).length;

  return (
    <motion.div 
      className="page"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
    >
      <div className="stats-grid">
        <motion.div 
          className="card stat-mini-card" 
          variants={cardVariants}
          whileHover={{ scale: 1.04, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)" }}
        >
          <h3>Total Claims</h3>
          <motion.p 
            initial={{ scale: 0 }} 
            animate={{ scale: 1 }} 
            transition={{ type: "spring", delay: 0.3 }}
          >
            {stats.total_claims}
          </motion.p>
        </motion.div>
        
        <motion.div 
          className="card stat-mini-card" 
          variants={cardVariants}
          whileHover={{ scale: 1.04, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)" }}
        >
          <h3>Average Confidence</h3>
          <motion.p 
            initial={{ scale: 0 }} 
            animate={{ scale: 1 }} 
            transition={{ type: "spring", delay: 0.4 }}
          >
            {Math.round(stats.avg_confidence)}%
          </motion.p>
        </motion.div>

        <motion.div
          className="card stat-mini-card"
          variants={cardVariants}
          whileHover={{ scale: 1.04, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)" }}
        >
          <h3>Latest Verdict</h3>
          <p>{latestVerdict}</p>
        </motion.div>

        <motion.div
          className="card stat-mini-card"
          variants={cardVariants}
          whileHover={{ scale: 1.04, boxShadow: "0 14px 32px rgba(0,0,0,0.16), -14px 0 20px rgba(0,0,0,0.08), 14px 0 20px rgba(0,0,0,0.08)" }}
        >
          <h3>High Confidence (≥80%)</h3>
          <p>{highConfidenceCount}</p>
        </motion.div>
      </div>

      <motion.div 
        className="card chart-card"
        variants={cardVariants}
        whileHover={{ boxShadow: "0 10px 40px rgba(0,0,0,0.15)" }}
      >
        <h2>Verdict Distribution</h2>
        <div style={{ width: '100%', height: '320px', position: 'relative' }}>
          <Bar data={chartData} options={chartOptions} />
        </div>
      </motion.div>

      <div className="stats-grid stats-grid-two">
        <motion.div className="card chart-card" variants={cardVariants} whileHover={{ boxShadow: "0 10px 40px rgba(0,0,0,0.15)" }}>
          <h2>Domain Distribution</h2>
          <div style={{ width: '100%', height: '300px', position: 'relative' }}>
            <Doughnut
              data={doughnutData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
              }}
            />
          </div>
        </motion.div>

        <motion.div className="card chart-card" variants={cardVariants} whileHover={{ boxShadow: "0 10px 40px rgba(0,0,0,0.15)" }}>
          <h2>Recent Confidence Trend</h2>
          <div style={{ width: '100%', height: '300px', position: 'relative' }}>
            <Line
              data={confidenceTrendData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                  y: { min: 0, max: 100, ticks: { stepSize: 20 } },
                },
              }}
            />
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

export default Stats;
