// React import removed as handled by JSX transform
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Leaderboard } from './pages/Leaderboard';
import { About } from './pages/About';

/**
 *
 */
/**
 * Main App component.
 * Handles client-side routing and global layout.
 */
function App() {
  return (
    <Router>
      <div id="app">
        <Navbar />
        <main style={{ marginTop: '2rem' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/leaderboard" replace />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
            <Route path="/about" element={<About />} />
            {/* Add more routes here */}
          </Routes>
        </main>
        <footer
          style={{
            marginTop: '4rem',
            textAlign: 'center',
            color: 'var(--text-secondary)',
            fontSize: '0.8rem',
          }}
        >
          &copy; 2025 Chess LLM Arena. All rights reserved.
        </footer>
      </div>
    </Router>
  );
}

export default App;
