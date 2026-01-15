import './style.css'
import { createIcons, icons } from 'lucide'
import { Navbar, setupNavbarListeners } from './components/Navbar'
import { Leaderboard } from './components/Leaderboard'
import { About } from './components/About'

// Initialize Theme
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

const app = document.querySelector<HTMLDivElement>('#app')!;

function render(page: string) {
  app.innerHTML = `
    ${Navbar()}
    <main style="margin-top: 2rem;">
      ${page === 'leaderboard' ? Leaderboard() : ''}
      ${page === 'about' ? About() : ''}
    </main>
    <footer style="margin-top: 4rem; text-align: center; color: var(--text-secondary); font-size: 0.8rem;">
      &copy; 2025 Chess LLM Arena. All rights reserved.
    </footer>
  `;

  // Initialize Icons
  createIcons({ icons });
  
  // Setup Listeners
  setupNavbarListeners(render);
}

// Initial Render
render('leaderboard');
