import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import toast from 'react-hot-toast';
import { AppProvider, useApp } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import History from './pages/History';
import Graph from './pages/Graph';
import Stats from './pages/Stats';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';
import Trending from './pages/Trending';
import SharedClaim from './pages/SharedClaim';

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -16 }}
        transition={{ duration: 0.3 }}
      >
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/history" element={<History />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/trending" element={<Trending />} />
          <Route path="/shared/:token" element={<SharedClaim />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

function AppInner() {
  const { theme } = useApp();
  const { isAuthenticated, user } = useAuth();

  React.useEffect(() => {
    if (!isAuthenticated || !user) return;
    const seen = localStorage.getItem('veritasai_onboarded');
    if (!seen) {
      toast.success(`🎉 Welcome to VeritasAI, ${user.full_name || user.username}! Start by verifying your first claim below.`);
      localStorage.setItem('veritasai_onboarded', '1');
    }
  }, [isAuthenticated, user]);

  return (
    <BrowserRouter>
      <div className="animated-bg" />
      <Navbar />
      <AnimatedRoutes />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: theme === 'dark' ? '#1e1e2e' : '#ffffff',
            color: theme === 'dark' ? '#f1f5f9' : '#0f172a',
            border: '1px solid rgba(99,102,241,0.3)',
            borderRadius: 12,
            fontSize: '0.875rem',
          },
        }}
      />
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <AppInner />
      </AppProvider>
    </AuthProvider>
  );
}
