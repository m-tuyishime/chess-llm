import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Leaderboard } from './pages/Leaderboard';
import { AgentDetail } from './pages/AgentDetail';
import { ReplayPage } from './pages/ReplayPage';
import { About } from './pages/About';

/**
 * Layout wrapper to handle conditional rendering of Navbar and Footer.
 */
function AppLayout() {
  const location = useLocation();
  const isReplayPage = location.pathname.startsWith('/replay');

  return (
    <div id="app" className={isReplayPage ? 'full-screen-layout' : ''}>
      {!isReplayPage && <Navbar />}
      <main style={{ marginTop: isReplayPage ? '0' : '2rem' }}>
        <Routes>
          <Route path="/" element={<Navigate to="/leaderboard" replace />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/agent/*" element={<AgentDetail />} />
          <Route path="/replay/:gameId" element={<ReplayPage />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
      {!isReplayPage && (
        <footer
          style={{
            marginTop: '4rem',
            textAlign: 'center',
            color: 'var(--text-secondary)',
            fontSize: '0.8rem',
            paddingBottom: '2rem',
          }}
        >
          &copy; 2025 Chess LLM Arena. All rights reserved.
        </footer>
      )}
    </div>
  );
}

/**
 * Main App component.
 * Handles client-side routing and global layout.
 */
function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;
