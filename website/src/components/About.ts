export function About() {
  return `
    <div class="card animate-fade-in">
      <h2>About the Project</h2>
      <p style="color: var(--text-secondary); margin-bottom: 2rem;">
        This project evaluates the chess capabilities of modern Large Language Models (LLMs) using a rigorous benchmark of chess puzzles.
      </p>

      <h3>Methodology</h3>
      <p style="color: var(--text-secondary); margin-bottom: 2rem;">
        We use a modified Glicko-2 rating system. Agents are presented with tactical puzzles from the Lichess database. 
        They must analyze the position and output the best move. We use Chain-of-Thought prompting to encourage reasoning.
      </p>

      <h3>Authors</h3>
      <ul style="color: var(--text-secondary); margin-bottom: 2rem;">
        <li>Tuyishime</li>
        <li>McAllister</li>
      </ul>

      <div style="margin-top: 3rem; padding-top: 2rem; border-top: 1px solid var(--glass-border);">
        <h3>Support the Project</h3>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1rem;">
          Running these benchmarks requires significant compute resources. If you find this useful, consider donating!
        </p>
        <button class="btn btn-primary">
          <i data-lucide="coffee"></i> Buy us a coffee
        </button>
      </div>
    </div>
  `;
}
