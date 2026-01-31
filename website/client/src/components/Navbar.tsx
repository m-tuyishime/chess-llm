import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sun, Moon, Languages } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useLocalStorage } from '../hooks/useLocalStorage';

/**
 * Navbar component.
 * Provides main navigation, theme toggle, and language toggle.
 */
export function Navbar() {
  const { t, i18n } = useTranslation();
  const [theme, setTheme] = useLocalStorage<'dark' | 'light'>('theme', 'dark');
  const [lang, setLang] = useLocalStorage<string>('lang', i18n.language);
  const location = useLocation();

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Sync i18n with localStorage
  React.useEffect(() => {
    if (i18n.language !== lang) {
      i18n.changeLanguage(lang);
    }
  }, [lang, i18n]);

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
            {t('nav.title')}
          </span>
        </Link>
      </div>
      <div className="nav-links">
        <Link
          to="/leaderboard"
          className={`nav-link ${location.pathname === '/leaderboard' ? 'active' : ''}`}
        >
          {t('nav.leaderboard')}
        </Link>
        <Link
          to="/analytics"
          className={`nav-link ${location.pathname === '/analytics' ? 'active' : ''}`}
        >
          {t('nav.analytics')}
        </Link>
        <Link to="/about" className={`nav-link ${location.pathname === '/about' ? 'active' : ''}`}>
          {t('nav.about')}
        </Link>
        <div className="nav-actions">
          <button className="btn btn-secondary" onClick={toggleTheme} title={t('nav.toggleTheme')}>
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <button
            className="btn btn-secondary"
            onClick={toggleLang}
            title={t('nav.toggleLanguage')}
          >
            <Languages size={20} />
            <span style={{ fontSize: '0.8rem', marginLeft: '0.2rem' }}>{lang.toUpperCase()}</span>
          </button>
        </div>
      </div>
    </nav>
  );
}
