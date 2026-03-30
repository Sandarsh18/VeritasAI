import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState, useRef } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { usePopper } from "react-popper";
import AOS from "aos";
import "aos/dist/aos.css";

import Home from "./pages/Home";
import History from "./pages/History";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import Stats from "./pages/Stats";
import { getMe, setAuthToken } from "./services/api";
import "./App.css";

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthRoute = location.pathname === "/login" || location.pathname === "/register";
  const [theme, setTheme] = useState(localStorage.getItem("veritas-theme") || "dark");
  const [currentUser, setCurrentUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [profileOpen, setProfileOpen] = useState(false);

  const [referenceElement, setReferenceElement] = useState(null);
  const [popperElement, setPopperElement] = useState(null);
  const { styles, attributes } = usePopper(referenceElement, popperElement, {
    placement: "bottom-end",
    modifiers: [
      {
        name: "offset",
        options: {
          offset: [0, 10],
        },
      },
    ],
  });

  useEffect(() => {
    AOS.init({ duration: 800, once: true });
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("veritas-theme", theme);
  }, [theme]);

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem("veritas-token");
      if (!token) {
        setCurrentUser(null);
        setAuthToken(null);
        setLoadingUser(false);
        return;
      }

      try {
        setAuthToken(token);
        const me = await getMe();
        setCurrentUser(me);
      } catch {
        localStorage.removeItem("veritas-token");
        setAuthToken(null);
        setCurrentUser(null);
      } finally {
        setLoadingUser(false);
      }
    };

    loadUser();
    setProfileOpen(false);
  }, [location.pathname]);

  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  const initials = useMemo(() => {
    if (!currentUser?.username) return "U";
    return currentUser.username.slice(0, 2).toUpperCase();
  }, [currentUser]);

  const logout = () => {
    localStorage.removeItem("veritas-token");
    setAuthToken(null);
    setCurrentUser(null);
    setProfileOpen(false);
    navigate("/login");
  };

  return (
    <div className={`app-shell ${isAuthRoute ? "auth-layout" : ""}`}>
      {!isAuthRoute && (
        <motion.header 
          className="top-nav"
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
        >
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            VeritasAI
          </motion.h1>
          <nav>
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}>
              <Link to="/" className={`nav-link-btn nav-home ${location.pathname === "/" ? "active" : ""}`}>Home</Link>
            </motion.div>
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}>
              <Link to="/history" className={`nav-link-btn nav-history ${location.pathname === "/history" ? "active" : ""}`}>History</Link>
            </motion.div>
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}>
              <Link to="/stats" className={`nav-link-btn nav-stats ${location.pathname === "/stats" ? "active" : ""}`}>Stats</Link>
            </motion.div>

            {!loadingUser && !currentUser && (
              <>
                <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}>
                  <Link to="/login" className={`nav-link-btn ${location.pathname === "/login" ? "active" : ""}`}>Login</Link>
                </motion.div>
                <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}>
                  <Link to="/register" className={`nav-link-btn ${location.pathname === "/register" ? "active" : ""}`}>Sign Up</Link>
                </motion.div>
              </>
            )}

            {!loadingUser && currentUser && (
              <div className="profile-menu-wrap">
                <motion.button 
                  ref={setReferenceElement}
                  className="profile-chip" 
                  onClick={() => setProfileOpen((v) => !v)}
                  whileHover={{ scale: 1.02, boxShadow: "0 0 10px rgba(108, 99, 255, 0.5)" }}
                  whileTap={{ scale: 0.98 }}
                >
                  <span className="profile-avatar">{initials}</span>
                  <span className="profile-name">{currentUser.username}</span>
                </motion.button>
                
                <AnimatePresence>
                  {profileOpen && (
                    <motion.div 
                      ref={setPopperElement}
                      style={styles.popper}
                      {...attributes.popper}
                      className="profile-menu"
                      initial={{ opacity: 0, y: -10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -10, scale: 0.95 }}
                      transition={{ type: "spring", stiffness: 300, damping: 25 }}
                    >
                      <p className="profile-email">{currentUser.email}</p>
                      <Link to="/profile" className="menu-link">
                        View Profile
                      </Link>
                      <button className="menu-link logout-btn" onClick={logout}>
                        Logout
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            <motion.button 
              className="theme-btn" 
              onClick={toggleTheme}
              whileHover={{ scale: 1.05, rotate: theme === "dark" ? 30 : -30 }}
              whileTap={{ scale: 0.9 }}
            >
              {theme === "dark" ? "☀ Light" : "🌙 Dark"}
            </motion.button>
          </nav>
        </motion.header>
      )}

      <div className="page-transition-wrapper">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Home />} />
            <Route path="/history" element={<History />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/login" element={currentUser ? <Navigate to="/" replace /> : <Login />} />
            <Route path="/register" element={currentUser ? <Navigate to="/" replace /> : <Register />} />
            <Route path="/profile" element={currentUser ? <Profile user={currentUser} onLogout={logout} /> : <Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
