import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sun, Moon, Languages } from 'lucide-react';

/**
 *
 */
/**
 * Navbar component.
 * Provides main navigation, theme toggle, and language toggle.
 */
export function Navbar() {
  const [theme, setTheme] = React.useState<'dark' | 'light'>(
    (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
  );
  const [lang, setLang] = React.useState(localStorage.getItem('lang') || 'en');
  const location = useLocation();

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  React.useEffect(() => {
    localStorage.setItem('lang', lang);
    // Ideally use a context or i18n lib here, but for now just persisting state
  }, [lang]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const toggleLang = () => {
    setLang((prev) => (prev === 'en' ? 'fr' : 'en'));
  };

  return (
    <nav className="navbar">
      <div className="logo">
        <Link to="/" style={{ textDecoration: 'none' }}>
          <span
            style={{
              fontWeight: 800,
              fontSize: '1.5rem',
              background: 'var(--accent-gradient)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Chess LLM Arena
          </span>
        </Link>
      </div>
      <div className="nav-links">
        <Link
          to="/leaderboard"
          className={`nav-link ${location.pathname === '/leaderboard' ? 'active' : ''}`}
        >
          Leaderboard
        </Link>
        <Link to="/about" className={`nav-link ${location.pathname === '/about' ? 'active' : ''}`}>
          About
        </Link>
        <div className="nav-actions">
          <button className="btn btn-secondary" onClick={toggleTheme} title="Toggle Theme">
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <button className="btn btn-secondary" onClick={toggleLang} title="Toggle Language">
            <Languages size={20} />
            <span style={{ fontSize: '0.8rem', marginLeft: '0.2rem' }}>{lang.toUpperCase()}</span>
          </button>
        </div>
      </div>
    </nav>
  );
}
