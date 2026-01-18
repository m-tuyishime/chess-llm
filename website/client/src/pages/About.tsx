// React import removed as handled by JSX transform

/**
 * About Page component.
 * Displays information about the project.
 */
export function About() {
  return (
    <div className="card">
      <h2>About Chess LLM Arena</h2>
      <p style={{ color: 'var(--text-secondary)' }}>
        Evaluating Large Language Models on their chess playing capabilities.
      </p>
    </div>
  );
}
