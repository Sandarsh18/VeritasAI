import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, History, Network, BarChart3 } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useApp } from '../context/AppContext';

const NAV_LINKS = [
  { to: '/', label: 'Verify', icon: Shield },
  { to: '/history', label: 'History', icon: History },
  { to: '/graph', label: 'Graph', icon: Network },
  { to: '/stats', label: 'Stats', icon: BarChart3 },
];

export default function Navbar() {
  const { pathname } = useLocation();
  const { theme } = useApp();
  const isDark = theme === 'dark';

  return (
    <motion.nav
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        background: isDark ? 'rgba(10,10,15,0.8)' : 'rgba(248,250,252,0.85)',
        borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}`,
        padding: '0 1.5rem',
      }}
    >
      <div style={{
        maxWidth: 1200,
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 64,
      }}>
        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(99,102,241,0.4)',
          }}>
            <Shield size={18} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1rem', letterSpacing: '-0.02em' }}>
              <span style={{
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
              }}>
                VerifyAI
              </span>
            </div>
            <div style={{ fontSize: '0.6rem', opacity: 0.5, letterSpacing: '0.08em', fontWeight: 500 }}>
              MULTI-AGENT FACT CHECKER
            </div>
          </div>
        </Link>

        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {NAV_LINKS.map(({ to, label, icon: Icon }) => {
            const isActive = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '8px 14px', borderRadius: 10,
                  fontSize: '0.875rem', fontWeight: isActive ? 600 : 500,
                  color: isActive ? '#6366f1' : (isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)'),
                  background: isActive ? 'rgba(99,102,241,0.12)' : 'transparent',
                  border: `1px solid ${isActive ? 'rgba(99,102,241,0.3)' : 'transparent'}`,
                  transition: 'all 0.2s ease',
                  textDecoration: 'none',
                }}
              >
                <Icon size={15} />
                <span className="hide-mobile">{label}</span>
              </Link>
            );
          })}
          <div style={{ marginLeft: 8 }}>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </motion.nav>
  );
}
