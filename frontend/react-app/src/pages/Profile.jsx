import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

const containerVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 30 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 25, staggerChildren: 0.1 } 
  },
  exit: { opacity: 0, scale: 0.95, y: -20, transition: { duration: 0.2 } }
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300 } }
};

function Profile({ user, onLogout }) {
  const navigate = useNavigate();
  const [notice, setNotice] = useState("");
  const [prefs, setPrefs] = useState(() => ({
    emailUpdates: localStorage.getItem("veritas-pref-email-updates") !== "off",
    saveLocalCache: localStorage.getItem("veritas-pref-save-cache") !== "off",
  }));

  const cacheCount = useMemo(() => {
    try {
      const cache = JSON.parse(localStorage.getItem("veritas-results-cache") || "{}");
      return Object.keys(cache || {}).length;
    } catch {
      return 0;
    }
  }, [notice]);

  const joinedAt = useMemo(() => {
    if (!user?.created_at) return "N/A";
    const dt = new Date(user.created_at);
    if (Number.isNaN(dt.getTime())) return "N/A";
    return dt.toLocaleString();
  }, [user?.created_at]);

  const tokenPresent = Boolean(localStorage.getItem("veritas-token"));

  const setPreference = (key, value) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));

    if (key === "emailUpdates") {
      localStorage.setItem("veritas-pref-email-updates", value ? "on" : "off");
    }
    if (key === "saveLocalCache") {
      localStorage.setItem("veritas-pref-save-cache", value ? "on" : "off");
    }
  };

  const clearLocalAnalysisCache = () => {
    localStorage.removeItem("veritas-results-cache");
    localStorage.removeItem("veritas-last-claim");
    setNotice("Local analysis cache cleared.");
  };

  if (!user) return null;

  return (
    <motion.div 
      className="page"
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={containerVariants}
    >
      <motion.div 
        className="card profile-card profile-enhanced-card"
        whileHover={{ boxShadow: "0 10px 40px rgba(0,0,0,0.15)" }}
      >
        <motion.div variants={itemVariants} className="profile-top-row">
          <div>
            <h2>User Profile</h2>
            <p className="profile-subtitle">Manage your essential account settings and security.</p>
          </div>
          <span className={`profile-status-pill ${user.is_active ? "active" : "inactive"}`}>
            {user.is_active ? "Active" : "Inactive"}
          </span>
        </motion.div>

        {notice && <p className="profile-notice">{notice}</p>}

        <div className="profile-sections-grid">
          <motion.section className="card profile-section-card" variants={itemVariants} whileHover={{ scale: 1.01 }}>
            <h3>Account Overview</h3>
            <div className="profile-kv-grid">
              <div>
                <label>Username</label>
                <p>{user.username}</p>
              </div>
              <div>
                <label>Email</label>
                <p>{user.email}</p>
              </div>
              <div>
                <label>Joined</label>
                <p>{joinedAt}</p>
              </div>
            </div>
            <div className="profile-actions-row">
              <button className="secondary-btn" onClick={() => navigate("/")}>Go To Home</button>
            </div>
          </motion.section>

          <motion.section className="card profile-section-card" variants={itemVariants} whileHover={{ scale: 1.01 }}>
            <h3>Essential Preferences</h3>
            <label className="profile-toggle-row">
              <span>Email updates</span>
              <input
                type="checkbox"
                checked={prefs.emailUpdates}
                onChange={(e) => setPreference("emailUpdates", e.target.checked)}
              />
            </label>
            <label className="profile-toggle-row">
              <span>Save local analysis cache</span>
              <input
                type="checkbox"
                checked={prefs.saveLocalCache}
                onChange={(e) => setPreference("saveLocalCache", e.target.checked)}
              />
            </label>
            <div className="profile-kv-grid single-col">
              <div>
                <label>Local Saved Claims</label>
                <p>{cacheCount}</p>
              </div>
            </div>
            <div className="profile-actions-row">
              <button className="secondary-btn" onClick={clearLocalAnalysisCache}>Clear Local Cache</button>
            </div>
          </motion.section>

          <motion.section className="card profile-section-card profile-wide-section" variants={itemVariants} whileHover={{ scale: 1.01 }}>
            <h3>Security And Session</h3>
            <div className="profile-kv-grid single-col">
              <div>
                <label>Session Token</label>
                <p>{tokenPresent ? "Present" : "Missing"}</p>
              </div>
              <div>
                <label>Account Verification</label>
                <p>Verified</p>
              </div>
            </div>
            <div className="profile-actions-row">
              <button className="primary-btn profile-danger-btn" onClick={onLogout}>Logout</button>
            </div>
          </motion.section>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default Profile;
