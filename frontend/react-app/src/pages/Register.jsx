import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import * as api from "../services/api";
import "./AuthSplit.css";

const panelTransition = {
  duration: 0.5,
  ease: "easeOut",
};

const fieldVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: (index) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.32, ease: "easeOut", delay: index * 0.08 },
  }),
};

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (index) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: "easeOut", delay: index * 0.2 },
  }),
};

function ShieldIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2L4 5.2V11.2C4 16.4 7.4 21.2 12 22.6C16.6 21.2 20 16.4 20 11.2V5.2L12 2Z"
        fill="#4f46e5"
      />
    </svg>
  );
}

function EyeIcon({ hidden }) {
  if (hidden) {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3 3L21 21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <path
          d="M10.6 10.7C10.2 11 10 11.5 10 12C10 13.1 10.9 14 12 14C12.5 14 13 13.8 13.3 13.4"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path
          d="M9.8 5.3C10.5 5.1 11.2 5 12 5C16.8 5 20.6 8 22 12C21.5 13.4 20.6 14.7 19.5 15.7"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path
          d="M14.1 18.7C13.4 18.9 12.7 19 12 19C7.2 19 3.4 16 2 12C2.6 10.3 3.8 8.8 5.3 7.6"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M2 12C3.4 8 7.2 5 12 5C16.8 5 20.6 8 22 12C20.6 16 16.8 19 12 19C7.2 19 3.4 16 2 12Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#EA4335" d="M12 10.2V14.3H17.7C17.4 15.6 16.6 16.7 15.4 17.4L18.8 20C20.8 18.2 22 15.5 22 12.2C22 11.5 21.9 10.8 21.8 10.2H12Z" />
      <path fill="#34A853" d="M12 22C14.7 22 16.9 21.1 18.8 20L15.4 17.4C14.4 18.1 13.3 18.5 12 18.5C9.4 18.5 7.2 16.8 6.4 14.5L2.9 17.2C4.8 20 8.1 22 12 22Z" />
      <path fill="#FBBC05" d="M6.4 14.5C6.2 13.8 6 13 6 12.2C6 11.4 6.2 10.6 6.4 9.9L2.9 7.2C2.2 8.6 1.8 10.3 1.8 12.2C1.8 14.1 2.2 15.8 2.9 17.2L6.4 14.5Z" />
      <path fill="#4285F4" d="M12 5.9C13.5 5.9 14.8 6.4 15.9 7.4L18.9 4.4C16.9 2.5 14.4 1.4 12 1.4C8.1 1.4 4.8 3.4 2.9 6.2L6.4 8.9C7.2 6.6 9.4 5.9 12 5.9Z" />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M16.7 12.7C16.7 10.7 18.3 9.8 18.4 9.7C17.5 8.3 16.1 8.1 15.6 8.1C14.2 8 13 8.9 12.3 8.9C11.6 8.9 10.5 8.2 9.3 8.2C7.8 8.2 6.4 9.1 5.7 10.4C4.2 13.1 5.3 17.1 6.8 19.2C7.5 20.2 8.3 21.4 9.4 21.3C10.5 21.3 10.9 20.6 12.2 20.6C13.5 20.6 13.9 21.3 15 21.3C16.1 21.3 16.9 20.2 17.6 19.2C18.4 18.1 18.7 17 18.8 16.9C18.8 16.9 16.7 16.1 16.7 12.7Z" />
      <path d="M14.8 6.8C15.4 6 15.8 4.9 15.7 3.8C14.8 3.8 13.7 4.4 13 5.2C12.5 5.8 12 6.9 12.1 7.9C13.1 8 14.1 7.5 14.8 6.8Z" />
    </svg>
  );
}

function getStrength(password) {
  if (!password) {
    return { score: 0, label: "Weak", color: "#ef4444" };
  }

  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score <= 1) return { score: 1, label: "Weak", color: "#ef4444" };
  if (score === 2) return { score: 2, label: "Fair", color: "#f97316" };
  if (score === 3) return { score: 3, label: "Good", color: "#eab308" };
  return { score: 4, label: "Strong", color: "#22c55e" };
}

function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  const strength = useMemo(() => getStrength(formData.password), [formData.password]);

  useEffect(() => {
    if (!toast) return undefined;
    const timeoutId = setTimeout(() => setToast(""), 2200);
    return () => clearTimeout(timeoutId);
  }, [toast]);

  const showOAuthToast = (provider) => {
    setToast(`${provider} login coming soon`);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const payload = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
      };

      const data = await api.register(payload);
      let token = data.access_token || data.token || data.jwt;

      if (!token) {
        const loginData = await api.login({ email: formData.email, password: formData.password });
        token = loginData.access_token || loginData.token || loginData.jwt;
      }

      if (!token) {
        throw new Error("Missing token");
      }

      localStorage.setItem("veritas-token", token);
      api.setAuthToken(token);
      navigate("/");
    } catch {
      setError("Registration failed. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="va-auth-page">
      <div className="va-auth-card">
        <motion.section
          className="va-auth-left"
          initial={{ x: -30, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={panelTransition}
        >
          <div className="va-auth-logo">
            <ShieldIcon />
            <span>VeritasAI</span>
          </div>

          <h1 className="va-auth-heading">Create Your Account</h1>
          <p className="va-auth-subtext">Join VeritasAI and start verifying claims.</p>

          <form className="va-auth-form" onSubmit={handleSubmit}>
            <motion.div className="va-field" variants={fieldVariants} initial="hidden" animate="visible" custom={0}>
              <label className="va-label" htmlFor="register-name">Full Name</label>
              <input
                id="register-name"
                type="text"
                className="va-input"
                placeholder="John Doe"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </motion.div>

            <motion.div className="va-field" variants={fieldVariants} initial="hidden" animate="visible" custom={1}>
              <label className="va-label" htmlFor="register-email">Email</label>
              <input
                id="register-email"
                type="email"
                className="va-input"
                placeholder="you@example.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </motion.div>

            <motion.div className="va-field with-icon" variants={fieldVariants} initial="hidden" animate="visible" custom={2}>
              <label className="va-label" htmlFor="register-password">Password</label>
              <div className="va-input-wrap">
                <input
                  id="register-password"
                  type={showPassword ? "text" : "password"}
                  className="va-input"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                />
                <button type="button" className="va-eye-btn" onClick={() => setShowPassword((v) => !v)} aria-label="Toggle password visibility">
                  <EyeIcon hidden={showPassword} />
                </button>
              </div>
            </motion.div>

            <motion.div className="va-strength" variants={fieldVariants} initial="hidden" animate="visible" custom={3}>
              <div className="va-strength-bars">
                {[0, 1, 2, 3].map((segment) => (
                  <span
                    key={segment}
                    className="va-strength-segment"
                    style={{ background: segment < strength.score ? strength.color : "#e5e7eb" }}
                  />
                ))}
              </div>
              <div className="va-strength-label">{strength.label}</div>
            </motion.div>

            <motion.div className="va-field with-icon" variants={fieldVariants} initial="hidden" animate="visible" custom={4}>
              <label className="va-label" htmlFor="register-confirm-password">Confirm Password</label>
              <div className="va-input-wrap">
                <input
                  id="register-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  className="va-input"
                  placeholder="••••••••"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  required
                />
                <button type="button" className="va-eye-btn" onClick={() => setShowConfirmPassword((v) => !v)} aria-label="Toggle confirm password visibility">
                  <EyeIcon hidden={showConfirmPassword} />
                </button>
              </div>
            </motion.div>

            <motion.div variants={fieldVariants} initial="hidden" animate="visible" custom={5}>
              <motion.button
                type="submit"
                className="va-primary-btn"
                disabled={loading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {loading ? "Creating account..." : "Create Account"}
              </motion.button>
            </motion.div>

            {error && <p className="va-error">{error}</p>}

            <motion.div className="va-divider" variants={fieldVariants} initial="hidden" animate="visible" custom={6}>
              <span>Or Register With</span>
            </motion.div>

            <motion.div className="va-oauth-row" variants={fieldVariants} initial="hidden" animate="visible" custom={7}>
              <button type="button" className="va-oauth-btn" onClick={() => showOAuthToast("Google")}>
                <GoogleIcon />
                <span>Google</span>
              </button>
              <button type="button" className="va-oauth-btn" onClick={() => showOAuthToast("Apple")}>
                <AppleIcon />
                <span>Apple</span>
              </button>
            </motion.div>
          </form>

          <p className="va-bottom-link">
            Already Have An Account? <Link to="/login">Log In.</Link>
          </p>

          <div className="va-footer">
            <span>Copyright © 2025 VeritasAI</span>
            <a href="#">Privacy Policy</a>
          </div>
        </motion.section>

        <motion.section
          className="va-auth-right"
          initial={{ x: 30, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={panelTransition}
        >
          <h2 className="va-right-heading">Verify claims with AI-powered adversarial debate.</h2>
          <p className="va-right-subtext">Log in to start fact-checking claims with multi-agent reasoning.</p>

          <div className="va-dashboard">
            <motion.div className="va-dash-card va-card-small va-card-one" variants={cardVariants} initial="hidden" animate="visible" custom={0}>
              <div className="va-dash-label">Claims Verified</div>
              <div className="va-dash-value">1,284</div>
              <div className="va-dash-trend">
                <span>▲</span>
                <span>12% this week</span>
              </div>
            </motion.div>

            <motion.div className="va-dash-card va-card-small va-card-two" variants={cardVariants} initial="hidden" animate="visible" custom={1}>
              <div className="va-dash-label">Avg Confidence</div>
              <div className="va-dash-value">87.4%</div>
              <div className="va-dash-arc" />
            </motion.div>

            <motion.div className="va-dash-card va-card-wide" variants={cardVariants} initial="hidden" animate="visible" custom={2}>
              <div className="va-dash-label">Recent Verdicts</div>
              <div className="va-table">
                <div className="va-table-row">
                  <span className="va-claim-text">WW3 is happening</span>
                  <span className="va-badge false">FALSE</span>
                </div>
                <div className="va-table-row">
                  <span className="va-claim-text">Gold dropped ₹4000</span>
                  <span className="va-badge true">TRUE</span>
                </div>
                <div className="va-table-row">
                  <span className="va-claim-text">5G causes COVID</span>
                  <span className="va-badge false">FALSE</span>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.section>
      </div>

      {toast && (
        <motion.div className="va-toast" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}>
          {toast}
        </motion.div>
      )}
    </div>
  );
}

export default Register;
