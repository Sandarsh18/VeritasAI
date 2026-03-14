import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import { AppProvider, useApp } from './context/AppContext';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import History from './pages/History';
import Graph from './pages/Graph';
import Stats from './pages/Stats';

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
          <Route path="/history" element={<History />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/stats" element={<Stats />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

function AppInner() {
  const { theme } = useApp();
  return (
    <BrowserRouter>
      <div className={`animated-bg`} />
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
    <AppProvider>
      <AppInner />
    </AppProvider>
  );
}
