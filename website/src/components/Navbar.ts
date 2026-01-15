import { createIcons, icons } from 'lucide';

export function Navbar() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const currentLang = localStorage.getItem('lang') || 'en';

  return `
    <nav class="navbar">
      <div class="logo">
        <span style="font-weight: 800; font-size: 1.5rem; background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
          Chess LLM Arena
        </span>
      </div>
      <div class="nav-links">
        <a href="#" class="nav-link active" data-page="leaderboard">Leaderboard</a>
        <a href="#" class="nav-link" data-page="about">About</a>
        <div class="flex gap-2">
          <button class="btn btn-secondary" id="theme-toggle" title="Toggle Theme">
            ${currentTheme === 'dark' ? '<i data-lucide="sun"></i>' : '<i data-lucide="moon"></i>'}
          </button>
          <button class="btn btn-secondary" id="lang-toggle" title="Toggle Language">
            <i data-lucide="languages"></i>
            <span style="font-size: 0.8rem; margin-left: 0.2rem;">${currentLang.toUpperCase()}</span>
          </button>
        </div>
      </div>
    </nav>
  `;
}

export function setupNavbarListeners(updatePage: (page: string) => void) {
  // Theme Toggle
  const themeBtn = document.getElementById('theme-toggle');
  themeBtn?.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    // Update icon (simplified re-render would be better but this works for vanilla)
    themeBtn.innerHTML = next === 'dark' ? '<i data-lucide="sun"></i>' : '<i data-lucide="moon"></i>';
    createIcons({ icons });
  });

  // Language Toggle
  const langBtn = document.getElementById('lang-toggle');
  langBtn?.addEventListener('click', () => {
    const current = localStorage.getItem('lang') || 'en';
    const next = current === 'en' ? 'fr' : 'en';
    localStorage.setItem('lang', next);
    window.location.reload(); // Simple reload to apply language
  });

  // Navigation
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const page = (e.target as HTMLElement).getAttribute('data-page');
      if (page) {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        (e.target as HTMLElement).classList.add('active');
        updatePage(page);
      }
    });
  });
}
