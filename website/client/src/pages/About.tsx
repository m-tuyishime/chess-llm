/**
 * About Page component.
 * Displays information about the project based on the research report.
 */
export function About() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header Section */}
      <section style={{ textAlign: 'center', marginBottom: '1rem' }}>
        <h1
          style={{
            fontSize: '2.5rem',
            marginBottom: '0.5rem',
            background: 'var(--accent-gradient)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Chess LLM Arena
        </h1>
        <h2 style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', fontWeight: '400' }}>
          Comparative Analysis of Language Model Performance in Chess
        </h2>
        <p style={{ marginTop: '0.5rem', fontStyle: 'italic', color: 'var(--text-tertiary)' }}>
          Original Title: Analyse comparative des performances des modèles de langage dans le jeu
          d'échecs
        </p>

        <div style={{ marginTop: '2rem' }}>
          <a
            href="/report.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: 'none' }}
          >
            📄 Read Full Report (French only)
          </a>
        </div>
      </section>

      {/* Abstract Section */}
      <div className="card">
        <h3>Abstract</h3>
        <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)' }}>
          This work presents an evaluation of various Large Language Models (LLMs) on chess puzzle
          solving tasks. We developed an automatic evaluation system that uses the Glicko-2 rating
          to compare the performance of five models. The evaluation consisted of testing these
          models on a diverse set of chess puzzles from the Lichess database, distributed across
          three themes: End Game, Strategic, and Tactic.
        </p>
        <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)', marginTop: '1rem' }}>
          Our results reveal that they all obtained a ranking lower than the average level of
          approximately 1500. The best performing model (nvidia/llama-3.1-nemotron-ultra-253b-v1)
          only reached about 705 ± 81 points. We observed that the size and architecture of the
          model did not systematically correlate with performance.
        </p>
        <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)', marginTop: '1rem' }}>
          This research highlights the current limitations of LLMs in chess reasoning tasks and
          suggests that neither model size nor Chain-of-Thought training are indicators of
          performance in complex strategic games.
        </p>
      </div>

      {/* Key Findings & Methodology Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '2rem',
        }}
      >
        {/* Methodology */}
        <div className="card">
          <div
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}
          >
            <span style={{ fontSize: '1.5rem' }}>🔬</span>
            <h3 style={{ margin: 0 }}>Methodology</h3>
          </div>
          <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Framework:</strong> Automated Python evaluation system using Glicko-2 ratings.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Dataset:</strong> 1,400 puzzles from Lichess (Endgame, Strategic, Tactics).
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Models:</strong> 5 LLMs tested via Nvidia NIM & OpenRouter APIs.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Baselines:</strong> Stockfish (~1500 Elo) and Random Agent.
            </li>
          </ul>
        </div>

        {/* Key Findings */}
        <div className="card">
          <div
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}
          >
            <span style={{ fontSize: '1.5rem' }}>📊</span>
            <h3 style={{ margin: 0 }}>Key Findings</h3>
          </div>
          <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Sub-Human Performance:</strong> Best model reached ~705 Elo (vs 1500 human
              avg).
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Size ≠ Skill:</strong> Larger models (405B) did not significantly outperform
              smaller ones.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Hallucinations:</strong> High rate of illegal moves, especially without
              Chain-of-Thought.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Reasoning Gap:</strong> LLMs struggle with strict logic and lookahead
              planning.
            </li>
          </ul>
        </div>
      </div>

      {/* Contributors Section */}
      <div className="card">
        <h3>Research Team</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '2rem',
            marginTop: '1rem',
          }}
        >
          <div>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem' }}>Authors</h4>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: 'var(--text-primary)' }}>
              <li style={{ padding: '0.25rem 0' }}>Muhoza Olivier Tuyishime</li>
              <li style={{ padding: '0.25rem 0' }}>William McAllister</li>
            </ul>
          </div>

          <div>
            <h4 style={{ color: 'var(--accent-secondary)', marginBottom: '0.5rem' }}>Supervisor</h4>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: 'var(--text-primary)' }}>
              <li style={{ padding: '0.25rem 0' }}>Alan Davoust</li>
            </ul>
          </div>

          <div>
            <h4 style={{ color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>Institution</h4>
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
              Université du Québec en Outaouais (UQO)
              <br />
              Département d'informatique et d'ingénierie
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
