import { Routes, Route, Navigate, Link, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Gavel, LogOut } from "lucide-react";
import Auth from "./pages/Auth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Practice from "./pages/Practice.jsx";
import Results from "./pages/Results.jsx";

const Guard = ({ children }) => (localStorage.getItem("token") ? children : <Navigate to="/login" replace />);

function Shell({ children }) {
  const nav = useNavigate();
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-line px-5 py-4">
        <Link to="/" className="flex items-center gap-2 font-display text-xl"><Gavel size={20} className="text-accent" />Debatrix</Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link to="/practice" className="hover:text-accent">Practice</Link>
          <button aria-label="Log out" onClick={() => { localStorage.clear(); nav("/login"); }}><LogOut size={18} /></button>
        </nav>
      </header>
      <main className="mx-auto max-w-4xl px-5 py-8">{children}</main>
    </div>
  );
}

export default function App() {
  const loc = useLocation();
  const page = (el) => <Guard><Shell><motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{el}</motion.div></Shell></Guard>;
  return (
    <AnimatePresence mode="wait">
      <Routes location={loc} key={loc.pathname}>
        <Route path="/login" element={<Auth />} />
        <Route path="/register" element={<Auth register />} />
        <Route path="/" element={page(<Dashboard />)} />
        <Route path="/practice" element={page(<Practice />)} />
        <Route path="/results/:id" element={page(<Results />)} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AnimatePresence>
  );
}
