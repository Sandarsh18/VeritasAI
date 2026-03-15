import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Dialog from '@radix-ui/react-dialog';
import { Shield, History, Network, BarChart3, Flame, Search, LibraryBig } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { searchClaims } from '../services/api';

const NAV_LINKS = [
  { to: '/', label: 'Verify', icon: Shield },
  { to: '/history', label: 'History', icon: History },
  { to: '/graph', label: 'Graph', icon: Network },
  { to: '/stats', label: 'Stats', icon: BarChart3 },
  { to: '/trending', label: 'Trending', icon: Flame },
  { to: '/sources', label: 'Sources', icon: LibraryBig },
];

export default function Navbar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { theme } = useApp();
  const { user, isAuthenticated, logout } = useAuth();
  const isDark = theme === 'dark';
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [recent, setRecent] = useState(() => JSON.parse(localStorage.getItem('veritasai_recent_searches') || '[]'));

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await searchClaims(query, { limit: 8 });
        setResults(data.results || []);
      } catch {
        setResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const initials = (user?.full_name || user?.username || 'U').split(' ').map((x) => x[0]).join('').slice(0, 2).toUpperCase();

  const rememberRecent = (q) => {
    const next = [q, ...recent.filter((item) => item !== q)].slice(0, 5);
    setRecent(next);
    localStorage.setItem('veritasai_recent_searches', JSON.stringify(next));
  };

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
          <button onClick={() => setSearchOpen(true)} style={{ border: '1px solid transparent', background: 'transparent', color: isDark ? '#cbd5e1' : '#334155', cursor: 'pointer', display: 'grid', placeItems: 'center', borderRadius: 8, width: 34, height: 34 }}>
            <Search size={16} />
          </button>
          <div style={{ marginLeft: 2 }}>
            <ThemeToggle />
          </div>

          {!isAuthenticated ? (
            <>
              <Link to="/login" style={{ marginLeft: 8, padding: '8px 12px', borderRadius: 10, fontSize: '0.85rem', border: '1px solid var(--border-dark)' }}>Login</Link>
              <Link to="/register" style={{ marginLeft: 6, padding: '8px 12px', borderRadius: 10, fontSize: '0.85rem', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white' }}>Sign Up</Link>
            </>
          ) : (
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button style={{ marginLeft: 8, width: 34, height: 34, borderRadius: '50%', border: 'none', color: 'white', fontWeight: 700, background: user?.avatar_color || '#6366f1', cursor: 'pointer', position: 'relative' }}>
                  {initials}
                  <span style={{ position: 'absolute', right: -1, top: -1, width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} />
                </button>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content sideOffset={8} style={{ minWidth: 180, padding: 8, borderRadius: 10, border: '1px solid var(--border-dark)', background: isDark ? '#0f172a' : '#ffffff', color: isDark ? '#e2e8f0' : '#0f172a' }}>
                  <DropdownMenu.Item onClick={() => navigate('/profile')} style={{ padding: 8, cursor: 'pointer' }}>👤 View Profile</DropdownMenu.Item>
                  <DropdownMenu.Item onClick={() => navigate('/history')} style={{ padding: 8, cursor: 'pointer' }}>📊 My Claims</DropdownMenu.Item>
                  <DropdownMenu.Item onClick={() => navigate('/profile')} style={{ padding: 8, cursor: 'pointer' }}>⚙️ Settings</DropdownMenu.Item>
                  <DropdownMenu.Separator style={{ height: 1, background: 'var(--border-dark)', margin: '6px 0' }} />
                  <DropdownMenu.Item onClick={logout} style={{ padding: 8, cursor: 'pointer', color: '#f87171' }}>🚪 Logout</DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          )}
        </div>
      </div>

      <Dialog.Root open={searchOpen} onOpenChange={setSearchOpen}>
        <Dialog.Portal>
          <Dialog.Overlay style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)' }} />
          <Dialog.Content className="glass" style={{ position: 'fixed', inset: '10% 8%', padding: '1rem', overflow: 'auto' }}>
            <h3 style={{ marginBottom: 10 }}>🔍 Search claims, topics, sources...</h3>
            <input
              value={query}
              onChange={(e) => {
                const q = e.target.value;
                setQuery(q);
                if (q.trim()) rememberRecent(q.trim());
              }}
              placeholder="Type to search..."
              style={{ width: '100%', padding: 12, borderRadius: 10, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }}
            />

            {!query.trim() && recent.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <p style={{ opacity: 0.7, marginBottom: 6 }}>Recent searches:</p>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {recent.map((item) => (
                    <button key={item} onClick={() => setQuery(item)} style={{ borderRadius: 999, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit', padding: '4px 10px', cursor: 'pointer' }}>{item}</button>
                  ))}
                </div>
              </div>
            )}

            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {results.map((item) => (
                <div key={`${item.scope}-${item.id}`} className="glass" style={{ padding: 10 }}>
                  <div style={{ fontWeight: 600 }}>{item.text}</div>
                  <small style={{ opacity: 0.7 }}>{item.verdict} • {Math.round(item.confidence || 0)}%</small>
                </div>
              ))}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </motion.nav>
  );
}
